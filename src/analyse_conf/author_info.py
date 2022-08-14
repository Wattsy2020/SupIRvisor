"""Provides functions that extract further data of each author from google scholar"""
import os
import re
import pickle
import requests
from typing import Optional, Any

from analyse_conf.data import Authorship, Author


def equal_titles(title1: str, title2: str) -> bool:
    """Compare the first three words of each title to check for equality"""
    return title1.lower().split(" ")[:3] == title2.lower().split(" ")[:3]


def has_author(paper_json: dict[str, Any], author_name: str) -> bool:
    """Check if `author_name` is an author of the paper"""
    for author in paper_json["authors"]:
        if author["name"].lower() == author_name:
            return True
    return False


def is_same_paper(paper_json: dict[str, Any], title: str, author: str) -> bool:
    """
    Check if a paper returned by search API matches the query
    A paper matches if it has the same title, or is written by the same author (the name likely changed)
    """
    if equal_titles(paper_json["title"], title):
        return True
    return has_author(paper_json, author)


class SemanticScholarQuerier:
    """
    Make queries to the google scholar API, while keeping a persisted cache of previous queries, to avoid duplicate queries across sessions
    Should ALWAYS be used with the WITH keyword (to load and write the cache)
    """
    def __init__(self, api_path="https://api.semanticscholar.org/graph/v1", cache_path=".api_cache"):
        self.__api_path = api_path
        self.__cache_path = cache_path
        self.__cache: dict[str, dict[str, Any]] = {} # maps API urls to Json responses

    def __enter__(self) -> 'SemanticScholarQuerier':
        """Load the cache from file"""
        if os.path.exists(self.__cache_path):
            with open(self.__cache_path, "rb") as file:
                self.__cache = pickle.load(file)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Write the cache to file"""
        with open(self.__cache_path, "wb") as file:
            pickle.dump(self.__cache, file)

    def __get_json(self, resource_url: str) -> dict[str, Any]:
        """
        Return the json for a get request on the given resource url for the SemanticScholar graph API
        Cache new requests, and return the cached result for any previously seen API requests
        """
        if resource_url in self.__cache:
            return self.__cache[resource_url]
        
        response = requests.get(f"{self.__api_path}/{resource_url}")
        response.raise_for_status()
        json = response.json()
        self.__cache[resource_url] = json
        return json

    def __search_paper(self, query: str) -> dict[str, Any]:
        """Convert paper search query to a url, and search for it"""
        query = re.sub(r"[^\w]", "+", query) # replace spaces and all punctuation with + to fit the search API
        query_url = f"paper/search?query={query}&fields=authors,title"
        return self.__get_json(query_url)

    def get_paper(self, title: str, author: str) -> Optional[dict[str, Any]]:
        """Given a title, and one author: search for a paper and return its json object"""
        paper_json = self.__search_paper(title)

        # If the search has no results, the paper might have been renamed, search again with the author appended to the query
        if paper_json["total"] == 0:
            paper_json = self.__search_paper(f"{title} {author}")

        # If the search still no results: remove words from the end of the title (sometimes missing spaces confuses SemanticScholar)
        while paper_json["total"] == 0:
            title_words = title.split(" ")
            if len(title_words) < 3: # too few search terms will give a poor result, so treat the paper as unfindable
                return None
            title = " ".join(title_words[:-1])
            paper_json = self.__search_paper(title)

        # If the top paper doesn't have a matching author, look at the next results (note: it may have been renamed, but by the same author)
        paper_idx = 0
        total_papers = len(paper_json["data"])
        while not is_same_paper(paper_json["data"][paper_idx], title, author):
            paper_idx += 1
            if paper_idx == total_papers: # no matches found in all the results
                return None
        
        return paper_json["data"][paper_idx]

    def get_author(self, id: str) -> dict[str, Any]:
        """Return the author json for the given id"""
        return self.__get_json(f"author/{id}?fields=affiliations,paperCount,citationCount,hIndex")


def get_author_data(authorships: list[Authorship]) -> list[Author]:
    """Create authors and extract their data from SemanticScholar"""
    authors: list[Author] = []
    seen_author_ids: set[str] = set()

    with SemanticScholarQuerier() as query_engine:
        last_paper_title = ""
        for authorship in authorships:
            # Retrieve paper, if it's a new one
            if authorship.title == last_paper_title:
                continue
            last_paper_title = authorship.title
            paper = query_engine.get_paper(authorship.title, authorship.author_name)
            if paper is None:
                continue

            # Retrieve and add all new author details
            for author_id_json in paper["authors"]:
                author_id = author_id_json["authorId"]
                if author_id in seen_author_ids:
                    continue
                seen_author_ids.add(author_id)

                # query API and fill in the author object
                author_json = query_engine.get_author(author_id_json["authorId"])
                author = Author(author_id_json["name"], author_id)
                author.citations = author_json["citationCount"]
                author.paper_count = author_json["paperCount"]
                author.h_index = author_json["hIndex"]
                if author_json["affiliations"]:
                    author.institution = author_json["affiliations"][0]
                
                authors.append(author)
                print(author)
    return authors
