#!/usr/bin/env python3

import json
import re
import textwrap

import ads
import numpy as np

class MyPapers:
    """a class to manage searching for my publications from ADS"""

    def __init__(self):
        p = list(ads.SearchQuery(author="Zingale, M",
                                 max_pages=10,
                                 fl=["id", "bibcode", "citation_count",
                                     "author", "pub", "volume",
                                     "issue", "page", "year",
                                     "title", "property", "authors"]))

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
        # sort account to number of citations

        for p in mypapers:
            try:
                int(p.citation_count)
            except:
                print("Error with: ", p.bibcode, p.citation_count)

        self.mypapers = sorted(mypapers, key=lambda q: q.citation_count, reverse=True)


    def cite_report(self):
        """generate a table, ordered by cites, of the papers with number of
        cites"""

        num_cites = np.sum(np.array([q.citation_count for q in self.mypapers]))
        print("number of citations = ", num_cites)

        for n, p in enumerate(self.mypapers):
            clean_tags = re.compile("<.*?>")
            title = re.sub(clean_tags, "", p.title[0])
            tt = textwrap.wrap(title, 60)
            print(f"{n+1:3} | {p.citation_count:4}   {tt[0]}")
            if len(tt) > 1:
                for line in tt[1:]:
                    print("{:3} | {:4}   {}".format("", "", line))
            print("{:3} | {:4}   {}".format("", "", ""))

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
        except OSError:
            old_cites = {}

        num_cites = np.sum(np.array([q.citation_count for q in self.mypapers]))
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
        with open("cites.json", "w") as f:
            f.write(cite_json)

        # now look for differences in cites
        for key, value in cites.items():
            if key not in old_cites:
                print(f"new paper: {value[0]}")
            else:
                if value[1] != old_cites[key][1]:
                    print(f"change of {value[1] - old_cites[key][1]:+d} for paper: {value[0]}")

def doit():
    """the main driver -- check out cites"""
    myp = MyPapers()
    cites = Cites(myp.mypapers)
    #cites.cite_report()
    cites.compare_and_update()

if __name__ == "__main__":
    doit()
