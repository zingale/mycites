#!/usr/bin/env python3

from datetime import date

import ads
import numpy as np

class CoAuthor:
    """a class to manage coauthors with their affiliations"""

    def __init__(self, author, affil, start_year=10000, recent_year=-10000):
        """start_year is the earliest we've worked with the coauthor,
        recent_year is the most recent year we've worked with them"""

        self.author = author
        self.affil = affil
        self.start_year = start_year
        self.recent_year = recent_year

    def __eq__(self, other):
        return self.author == other.author

    def __lt__(self, other):
        return self.author < other.author

class MyPapers:

        """a class to manage searching for my publications from ADS"""

    def __init__(self, name="Zingale, M"):

        p = list(ads.SearchQuery(author=name,
                                 max_pages=10,
                                 fl=["id", "bibcode",
                                     "author", "pub", "volume",
                                     "issue", "page", "year", "aff",
                                     "title", "property", "authors"]))

        self.papers = p
        self.num = len(self.papers)

def doit():
    """the main driver -- check out cites"""

    start_year = 2017

    myp = MyPapers()

    coauthors = []

    for p in myp.papers:
        if int(p.year) >= start_year:
            for au, af in zip(p.author, p.aff):
                co = CoAuthor(au, af, start_year=p.year, recent_year=p.year)
                try:
                    idx = coauthors.index(co)
                    coauthors[idx].start_year = min(coauthors[idx].start_year, co.start_year)
                    coauthors[idx].recent_year = max(coauthors[idx].recent_year, co.recent_year)
                except ValueError:
                    coauthors.append(co)

    for co in sorted(coauthors):
        print(f"\"{co.author}\", \"{co.affil}\", \"{co.year}\"")

if __name__ == "__main__":
    doit()
