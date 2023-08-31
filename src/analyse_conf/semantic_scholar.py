from __future__ import annotations

import pickle
import re
import time
from pathlib import Path
from typing import Any

import requests
from attrs import define, field

from analyse_conf.data import JsonDict, Paper


@define(slots=True, frozen=True)
class SemanticScholarQuerier:
    """
    A context manager that makes queries to the semantic scholar API
    Keeps a persisted cache of previous queries, to avoid duplicate queries across sessions.
    """

    api_path: str = field(default="https://api.semanticscholar.org/graph/v1")
    cache_path: Path = field(converter=Path, default=Path(".api_cache"))
    _cache: dict[str, JsonDict] = field(factory=dict)

    def __enter__(self) -> SemanticScholarQuerier:
        """Load the cache from file"""
        if self.cache_path.exists():
            self._cache.update(pickle.load(self.cache_path.open("rb")))
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Write the cache to file"""
        with open(self.cache_path, "wb") as file:
            pickle.dump(self._cache, file)

    def __get_json(self, resource_url: str) -> JsonDict:
        """
        Return the json for a get request on `resource_url` to the SemanticScholar graph API
        Cache new requests, and return the cached result for any previously seen API requests
        """
        if resource_url in self._cache:
            return self._cache[resource_url]

        response = requests.get(f"{self.api_path}/{resource_url}")
        if response.status_code == 429:  # too many requests, retry later
            time.sleep(60)
            return self.__get_json(resource_url)
        response.raise_for_status()
        json = response.json()
        self._cache[resource_url] = json
        return json

    @staticmethod
    def __clean_query(query: str) -> str:
        """Remove punctuation and spaces from a query, to make it api friendly"""
        return re.sub(r"[^\w]", "+", query)

    def search_paper(self, query: str) -> JsonDict:
        """Convert paper search query to a url, and search for it"""
        query = self.__clean_query(query)
        query_url = f"paper/search?query={query}&fields=authors,title"
        return self.__get_json(query_url)

    def search_author_by_id(self, author_id: str) -> JsonDict:
        """Return the author json for the given id"""
        return self.__get_json(f"author/{author_id}?fields=name,affiliations,paperCount,citationCount,hIndex")

    def search_author_by_name(self, author_name: str) -> JsonDict:
        cleaned_name = self.__clean_query(author_name)
        return self.__get_json(f"author/search?query={cleaned_name}&fields=papers.authors&limit=20")


class SemanticScholarSearcher:
    """
    Given paper information, searches for that paper and its authors on semantic scholar
    Has custom author matching logic specialised for Semantic Scholar
    """

    def __enter__(self) -> SemanticScholarSearcher:
        self.query_engine = SemanticScholarQuerier().__enter__()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.query_engine.__exit__(exc_type, exc_val, exc_tb)

    @staticmethod
    def _equal_titles(title1: str, title2: str) -> bool:
        """Compare the first three words of each title to check for equality"""
        return title1.lower().split(" ")[:3] == title2.lower().split(" ")[:3]

    @staticmethod
    def _shares_author(paper_json: JsonDict, paper: Paper) -> bool:
        """Check if the paper_json shares any authors with a paper"""
        target_authors = {authorship.author_name for authorship in paper.authorships}
        return any(author["name"].lower() in target_authors for author in paper_json["authors"])

    @staticmethod
    def _is_same_paper(paper_json: JsonDict, paper: Paper) -> bool:
        """
        Check if a paper returned by search API matches the query, i.e. it has the same title,
        or is written by the same author (the paper name likely changed)
        """
        return SemanticScholarSearcher._equal_titles(
            paper_json["title"], paper.title
        ) or SemanticScholarSearcher._shares_author(paper_json, paper)

    def _get_paper_candidates(self, paper: Paper) -> JsonDict | None:
        paper_json = self.query_engine.search_paper(paper.title)

        # If the search has no results, the paper might have been renamed, try adding the author
        if paper_json["total"] == 0:
            title_with_author = f"{paper.title} {paper.authorships[0].author_name}"
            paper_json = self.query_engine.search_paper(title_with_author)

        # If the search still no results: remove words from the end of the title
        # (sometimes missing spaces confuses SemanticScholar)
        title = paper.title
        while paper_json["total"] == 0:
            title_words = title.split(" ")
            # too few search terms will give a poor result, so treat the paper as unfindable
            if len(title_words) < 3:
                return None
            title = " ".join(title_words[:-1])
            paper_json = self.query_engine.search_paper(title)
        return paper_json
    
    def _match_paper_to_candidates(self, paper: Paper, paper_candidates: JsonDict) -> JsonDict | None:
        """
        Return the first paper with a matching author
        note: the paper may have been renamed, but by the same author
        """
        paper_idx = 0
        total_papers = len(paper_candidates["data"])
        while not self._is_same_paper(paper_candidates["data"][paper_idx], paper):
            paper_idx += 1
            if paper_idx == total_papers:  # no matches found in all the results
                return None

        return paper_candidates["data"][paper_idx]

    def search_paper(self, paper: Paper) -> JsonDict | None:
        """Search for the paper on Semantic Scholar"""
        paper_candidates = self._get_paper_candidates(paper)
        return self._match_paper_to_candidates(paper, paper_candidates) if paper_candidates else None

    @staticmethod
    def _find_matching_author(retrieved_authors: JsonDict, paper_json: JsonDict) -> str | None:
        """Find the most likely author by counting the number of shared co authors"""
        paper_coauthors = {author_json["authorId"] for author_json in paper_json["authors"]}
        author_score: dict[str, int] = {}
        for author in retrieved_authors["data"]:
            all_coauthor_ids = (co_author["authorId"] for paper in author["papers"] for co_author in paper["authors"])
            author_score[author["authorId"]] = sum(co_author_id in paper_coauthors for co_author_id in all_coauthor_ids)
        return max(author_score, key=lambda x: author_score[x]) if author_score else None

    def search_author_by_name(self, author_name: str, paper_json: JsonDict) -> str | None:
        """
        Given an author name return the correct authorId,
        by finding the authorId that wrote papers with the given co_authors

        If there are no search results from the API this returns none
        """
        retrieved_authors = self.query_engine.search_author_by_name(author_name)
        return self._find_matching_author(retrieved_authors, paper_json)

    def search_author_by_id(self, author_id: str) -> JsonDict:
        return self.query_engine.search_author_by_id(author_id)
