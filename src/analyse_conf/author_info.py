"""Provides functions that extract further data of each author from google scholar"""
from typing import Optional, Any
import requests

from analyse_conf.data import Authorship, Author

# Cache the results for each query, using a key value pair of Author name to Author data (actual value needs to be a list of authors with the same name)
    # Then look in the cache first before making a ScraperAPI request (to save money)
    # Persist the cache to disk at end of program 
    # (maybe it should be a global object created by this file, that has a destructor which persists the cache to disk, and a constructor that reads from it)
class SemanticScholarQuerier:
    """Make queries to the google scholar API, while keeping a persisted cache of previous queries, to avoid duplicate queries across sessions"""
    def __init__(self, api_path="https://api.semanticscholar.org/graph/v1"):
        """Read query cache in constructor"""
        self.api_path = api_path

    # Write cache in destructor

    def __get_json(self, resource_url: str) -> dict[str, Any]:
        """Return the json for a get request on the given resource url for the SemanticScholar graph API"""
        response = requests.get(f"{self.api_path}/{resource_url}")
        response.raise_for_status()
        return response.json()

    # TODO: check if query is in cache
    def get_paper(self, title: str) -> Optional[dict[str, Any]]:
        """Return the paper json, if it exists"""
        paper_json = self.__get_json(f"paper/search?query={title}&fields=authors")
        return paper_json["data"][0] if paper_json["total"] != 0 else None

    def get_author(self, id: str) -> dict[str, Any]:
        """Return the author json for the given id"""
        return self.__get_json(f"author/{id}?fields=affiliations,paperCount,citationCount,hIndex")



def extract_author_data(authorships: list[Authorship]) -> list[Author]:
    """Create authors and extract their data from google scholar"""
    authors: set[Author] = set()
    query_engine = SemanticScholarQuerier()

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


def get_author_data(authorships: list[Authorship]) -> list[Author]:
    """Extract all author data, create Author objects to represent them"""
    authors = extract_author_data(authorships) # store authors in a class, then add in extra info from google scholar
    return authors
