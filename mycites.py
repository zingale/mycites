#!/usr/bin/env python

import json
import os
import sys
import tempfile
import time

import ads


from requests.exceptions import ConnectionError


# SciXplorer uses the same API as ADS. Override the legacy client's search
# endpoint, including searches it creates internally to fetch missing fields.
ads.SearchQuery.HTTP_ENDPOINT = "https://api.scixplorer.org/v1/search/query"


class InconsistentSciXResults(RuntimeError):
    """SciXplorer returned duplicate records or an unexpected paper count."""


class MyPapers:
    """a class to manage searching for my publications from SciXplorer"""

    def __init__(self):

        for attempt in range(3):
            query = ads.SearchQuery(author="Zingale, M",
                                    # The default relevance scores can differ between
                                    # server replicas, causing cursor pagination to
                                    # skip or repeat papers. Sorting by unique record
                                    # ID gives a stable order across page requests.
                                    sort="id asc",
                                    max_pages=10,
                                    fl=["id", "bibcode", "citation_count",
                                        "author", "pub", "volume",
                                        "issue", "page", "year",
                                        "title", "property", "authors"])
            try:
                p = list(query)
                unique_count = len({paper.bibcode for paper in p})
                if len(p) != query.response.numFound or unique_count != len(p):
                    raise InconsistentSciXResults(
                        f"received {len(p)} of {query.response.numFound} papers "
                        f"({unique_count} unique bibcodes)"
                    )
            except (ConnectionError, IndexError, InconsistentSciXResults) as exc:
                # The ADS iterator raises IndexError if a next page is empty
                # while numFound still indicates more results. Restart from
                # scratch so records from different attempts are never mixed.
                if attempt == 2:
                    raise RuntimeError(
                        f"SciXplorer query failed after 3 attempts ({exc}); "
                        "cites.json was not updated"
                    ) from exc
                delay = 5 * (attempt + 1)
                print(f"SciXplorer query failed ({type(exc).__name__}: {exc}); "
                      f"retrying in {delay} seconds", file=sys.stderr)
                time.sleep(delay)
            else:
                break

        self.mypapers = p

        # hack around a bug whereby some papers might have "None" as the number of cites
        for paper in self.mypapers:
            if paper.citation_count is None:
                paper.citation_count = 0
            if paper.property is None:
                paper.property = []

        # do some sorting and splitting
        self.refereed = [q for q in self.mypapers if "REFEREED" in q.property]
        self.num = len(self.mypapers)

    def cv_list(self):
        """print out a bibliography of papers, most recent first"""

        mystr = ""
        for p in self.mypapers:
            mystr += f"{p.title[0]}\n"
            if len(p.author) > 12:
                a = f"{p.author[0]} et al. "
            elif len(p.author) > 2:
                a = ", ".join(p.author[:-1]) + f" & {p.author[-1]} "
            elif len(p.author) == 2:
                a = f"{p.author[0]} & {p.author[1]} "
            else:
                a = f"{p.author[0]} "

            mystr += f"{a}"
            mystr += f"{p.year}, {p.pub}"
            if p.volume is not None:
                mystr += f", {p.volume}"
            if p.issue is not None:
                mystr += f", {p.issue}"
            if p.page is not None:
                mystr += f", {p.page[0]}"
            mystr += "\n\n"
        return mystr


class Cites:
    """a class to manage the number of citations of papers"""
    def __init__(self, mypapers):
        mypapers = list(mypapers)

        for p in mypapers:
            count = p.citation_count
            try:
                normalized = 0 if count is None else int(count)
                if (normalized < 0 or isinstance(count, bool) or
                        (count is not None and not isinstance(count, str)
                         and count != normalized)):
                    raise ValueError("expected a nonnegative integer")
            except (TypeError, ValueError, OverflowError) as exc:
                raise ValueError(
                    f"Invalid citation count for {p.bibcode}: {count!r}"
                ) from exc
            p.citation_count = normalized

        self.mypapers = sorted(mypapers, key=lambda q: q.citation_count, reverse=True)

    def compare_and_update(self):
        """this will read the old cite numbers from the stored JSON file and
        then compare to the new cites, and print out any papers that
        changed.  Then it will updated the stored JSON file
        """

        # first read in the old cites
        try:
            with open("cites.json") as f:
                cites_json = f.read()
            old_cites = json.loads(cites_json)
        except FileNotFoundError:
            old_cites = {}
        except json.JSONDecodeError as exc:
            raise ValueError(
                "cites.json contains invalid JSON; leaving it unchanged"
            ) from exc

        num_cites = sum(q.citation_count for q in self.mypapers)
        print("number of citations = ", num_cites)

        h_index = 0
        for n, p in enumerate(self.mypapers):
            if p.citation_count >= n+1:
                h_index = n + 1
        print("h-index = ", h_index)

        # now create a dict of the cites and update the stored JSON
        cites = {}
        for p in self.mypapers:
            cites[p.bibcode] = (p.title[0], p.citation_count)

        cite_json = json.dumps(cites, indent=4)
        temp_path = None
        try:
            # Keep the temporary file on the same filesystem for atomic replacement.
            with tempfile.NamedTemporaryFile(mode="w", dir=".",
                                             prefix=".cites-", suffix=".tmp",
                                             delete=False) as f:
                temp_path = f.name
                f.write(cite_json)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, "cites.json")
        finally:
            if temp_path is not None and os.path.exists(temp_path):
                os.unlink(temp_path)

        # now look for differences in cites
        for key, value in cites.items():
            if key not in old_cites:
                print(f"new paper: {value[0]}")
            elif value[1] != old_cites[key][1]:
                print(f"change of {value[1] - old_cites[key][1]:+d} for paper: {value[0]}")


def doit():
    """the main driver -- check out cites"""
    myp = MyPapers()
    cites = Cites(myp.mypapers)
    cites.compare_and_update()


if __name__ == "__main__":
    doit()
