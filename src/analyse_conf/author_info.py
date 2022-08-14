"""Provides functions that extract further data of each author from google scholar"""
import os
import pickle
import requests
from typing import Optional, Any

from analyse_conf.data import Authorship, Author


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

    def get_paper(self, title: str) -> Optional[dict[str, Any]]:
        """Return the paper json, if it exists"""
        paper_json = self.__get_json(f"paper/search?query={title}&fields=authors")
        return paper_json["data"][0] if paper_json["total"] != 0 else None

    def get_author(self, id: str) -> dict[str, Any]:
        """Return the author json for the given id"""
        return self.__get_json(f"author/{id}?fields=affiliations,paperCount,citationCount,hIndex")


def get_author_data(authorships: list[Authorship]) -> list[Author]:
    """Create authors and extract their data from google scholar"""
    authors: set[Author] = set()
    with SemanticScholarQuerier() as query_engine:
        # Retrieve data from semantic scholar for each author
        for authorship in authorships:
            # only add new authors
            if Author(authorship.author_name) in authors:
                continue
            
            # Retrieve paper, if it exists
            paper = query_engine.get_paper(authorship.title)
            if paper is None:
                continue

            # Retrieve and add author details for the entire paper
            for author_id_json in paper["authors"]:
                author = Author(author_id_json["name"])
                if author in authors:
                    continue

                # query API and fill in the author object
                author_json = query_engine.get_author(author_id_json["authorId"])
                author.citations = author_json["citationCount"]
                author.paper_count = author_json["paperCount"]
                author.h_index = author_json["hIndex"]
                if author_json["affiliations"]:
                    author.institution = author_json["affiliations"][0]
                
                authors.add(author)
                print(author)
    return list(authors)
