from __future__ import annotations

import pickle
import re
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import requests

from analyse_conf.data import JsonDict, Paper


def equal_titles(title1: str, title2: str) -> bool:
    """Compare the first three words of each title to check for equality"""
    return title1.lower().split(" ")[:3] == title2.lower().split(" ")[:3]


def shares_author(paper_json: JsonDict, paper: Paper) -> bool:
    """Check if the paper_json shares any authors with a paper"""
    target_authors = {authorship.author_name for authorship in paper.authorships}
    return any(author["name"].lower() in target_authors for author in paper_json["authors"])


def is_same_paper(paper_json: JsonDict, paper: Paper) -> bool:
    """
    Check if a paper returned by search API matches the query, i.e. it has the same title,
    or is written by the same author (the paper name likely changed)
    """
    return equal_titles(paper_json["title"], paper.title) or shares_author(paper_json, paper)


class SemanticScholarQuerier:
    """
    Make queries to the google scholar API
    Keeps a persisted cache of previous queries, to avoid duplicate queries across sessions.
    Should ALWAYS be used with the WITH keyword (to load and write the cache).
    """

    def __init__(
        self,
        api_path: str = "https://api.semanticscholar.org/graph/v1",
        cache_path: str = ".api_cache",
    ) -> None:
        self.__api_path = api_path
        self.__cache_path = Path(cache_path)
        self.__cache: dict[str, JsonDict] = {}  # maps API urls to Json responses

    def __enter__(self) -> SemanticScholarQuerier:
        """Load the cache from file"""
        if self.__cache_path.exists():
            self.__cache = pickle.load(self.__cache_path.open("rb"))
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Write the cache to file"""
        with open(self.__cache_path, "wb") as file:
            pickle.dump(self.__cache, file)

    def __get_json(self, resource_url: str) -> JsonDict:
        """
        Return the json for a get request on `resource_url` to the SemanticScholar graph API
        Cache new requests, and return the cached result for any previously seen API requests
        """
        if resource_url in self.__cache:
            return self.__cache[resource_url]

        response = requests.get(f"{self.__api_path}/{resource_url}")
        if response.status_code == 429:  # too many requests, retry later
            time.sleep(60)
            return self.__get_json(resource_url)
        response.raise_for_status()
        json = response.json()
        self.__cache[resource_url] = json
        return json

    @staticmethod
    def __clean_query(query: str) -> str:
        """Remove punctuation and spaces from a query, to make it api friendly"""
        return re.sub(r"[^\w]", "+", query)

    def __search_paper(self, query: str) -> JsonDict:
        """Convert paper search query to a url, and search for it"""
        query = self.__clean_query(query)
        query_url = f"paper/search?query={query}&fields=authors,title"
        return self.__get_json(query_url)

    def get_paper(self, paper: Paper) -> JsonDict | None:
        """Given a title, and one author: search for a paper and return its json object"""
        paper_json = self.__search_paper(paper.title)

        # If the search has no results, the paper might have been renamed, try adding the author
        if paper_json["total"] == 0:
            title_with_author = f"{paper.title} {paper.authorships[0].author_name}"
            paper_json = self.__search_paper(title_with_author)

        # If the search still no results: remove words from the end of the title
        # (sometimes missing spaces confuses SemanticScholar)
        title = paper.title
        while paper_json["total"] == 0:
            title_words = title.split(" ")
            # too few search terms will give a poor result, so treat the paper as unfindable
            if len(title_words) < 3:
                return None
            title = " ".join(title_words[:-1])
            paper_json = self.__search_paper(title)

        # If the top paper doesn't have a matching author, look at the next results
        # note: the paper may have been renamed, but by the same author
        paper_idx = 0
        total_papers = len(paper_json["data"])
        while not is_same_paper(paper_json["data"][paper_idx], paper):
            paper_idx += 1
            if paper_idx == total_papers:  # no matches found in all the results
                return None

        return paper_json["data"][paper_idx]

    def get_author(self, author_id: str) -> JsonDict:
        """Return the author json for the given id"""
        return self.__get_json(
            f"author/{author_id}?fields=name,affiliations,paperCount,citationCount,hIndex"
        )

    def search_author(self, author_name: str, paper_json: JsonDict) -> str | None:
        """
        Given an author name return the correct authorId,
        by finding the authorId that wrote papers with the given co_authors

        If there are no search results from the API this returns none
        """
        co_author_ids = {author_json["authorId"] for author_json in paper_json["authors"]}
        author_name = self.__clean_query(author_name)
        retrieved_authors = self.__get_json(
            f"author/search?query={author_name}&fields=papers.authors&limit=20"
        )

        # Find the most likely author by counting the number of shared co authors
        author_score: dict[str, int] = defaultdict(int)
        for author in retrieved_authors["data"]:
            potential_match_id = author["authorId"]
            # count the number of matching co_authors
            for paper in author["papers"]:
                for co_author in paper["authors"]:
                    if co_author["authorId"] in co_author_ids:
                        author_score[potential_match_id] += 1

        return max(author_score, key=lambda x: author_score[x]) if author_score else None
