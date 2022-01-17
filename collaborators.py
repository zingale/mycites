#!/usr/bin/env python3

from datetime import date

import ads
import numpy as np

class CoAuthor:
    """a class to manage coauthors with their affiliations"""

    def __init__(self, author, affil, year=10000):
        self.author = author
        self.affil = affil
        self.year = year

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
        if int(p.year) > start_year:
            for au, af in zip(p.author, p.aff):
                co = CoAuthor(au, af, year=p.year)
                try:
                    idx = coauthors.index(co)
                    coauthors[idx].year = min(coauthors[idx].year, co.year)
                except ValueError:
                    coauthors.append(co)

    for co in sorted(coauthors):
        print(f"\"{co.author}\", \"{co.affil}\", \"{co.year}\"")

if __name__ == "__main__":
    doit()
