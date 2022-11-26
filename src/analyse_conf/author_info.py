"""Provides functions that extract further data of each author from google scholar"""
import os
import re
import time
import pickle
import requests
import Levenshtein
from typing import Optional, Any

import logging
logger = logging.getLogger(__name__)

from analyse_conf.data import Paper, Authorship, Author


def equal_titles(title1: str, title2: str) -> bool:
    """Compare the first three words of each title to check for equality"""
    return title1.lower().split(" ")[:3] == title2.lower().split(" ")[:3]


def shares_author(paper_json: dict[str, Any], paper: Paper) -> bool:
    """Check if the paper_json shares any authors with a paper"""
    target_authors = {authorship.author_name for authorship in paper.authorships}
    for author in paper_json["authors"]:
        if author["name"].lower() in target_authors:
            return True
    return False


def is_same_paper(paper_json: dict[str, Any], paper: Paper) -> bool:
    """
    Check if a paper returned by search API matches the query
    A paper matches if it has the same title, or is written by the same author (the name likely changed)
    """
    if equal_titles(paper_json["title"], paper.title):
        return True
    return shares_author(paper_json, paper)


def is_initialed(name: str) -> bool:
    """
    Determine whether a name is initialised, e.g. as L. Watts or L Watts
    match strings that have a single isolated char (space on either side or start/end of line), with an optional dot
    """
    return bool(re.match(r".*(?:^| ).[\.]?(?:$| ).*", name))


def initialise_name(name: str) -> tuple[str, list[str]]:
    """Convert a full written name into an intialised one, e.g. Liam Watts -> L. Watts"""
    name_sections = name.split(" ")
    initials = [f"{name_sec[0]}." for name_sec in name_sections[:-1]]
    return " ".join(initials + [name_sections[-1]]), initials


def name_distance(name1: str, name2: str) -> int:
    """
    Calculate the levenshtein distance between two names
    Also account for academic naming fashion of using initials, e.g. writing L. Watts for Liam Watts
    """
    name1 = name1.lower()
    name2 = name2.lower()
    if is_initialed(name1) or is_initialed(name2):
        new_name1, initials1 = initialise_name(name1)
        new_name2, initials2 = initialise_name(name2)
        if initials1 == initials2: # only if the initials match up can we compare using the initials
            name1 = new_name1
            name2 = new_name2
    return Levenshtein.distance(name1, name2)


class SemanticScholarQuerier:
    """
    Make queries to the google scholar API, while keeping a persisted cache of previous queries, to avoid duplicate queries across sessions.
    Should ALWAYS be used with the WITH keyword (to load and write the cache).
    """
    def __init__(self, api_path: str = "https://api.semanticscholar.org/graph/v1", cache_path: str = ".api_cache") -> None:
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
        Return the json for a get request on the given resource url for the SemanticScholar graph API.
        Cache new requests, and return the cached result for any previously seen API requests.
        """
        if resource_url in self.__cache:
            return self.__cache[resource_url]
        
        logging.info(f"Request for {resource_url}")
        response = requests.get(f"{self.__api_path}/{resource_url}")
        if response.status_code == 429: # too many requests, retry later
            logging.info(f"Recursing for {resource_url=}, {response=}, {response.headers=}")
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

    def __search_paper(self, query: str) -> dict[str, Any]:
        """Convert paper search query to a url, and search for it"""
        query = self.__clean_query(query)
        query_url = f"paper/search?query={query}&fields=authors,title"
        return self.__get_json(query_url)

    def get_paper(self, paper: Paper) -> Optional[dict[str, Any]]:
        """Given a title, and one author: search for a paper and return its json object"""
        paper_json = self.__search_paper(paper.title)

        # If the search has no results, the paper might have been renamed, search again with the author appended to the query
        if paper_json["total"] == 0:
            paper_json = self.__search_paper(f"{paper.title} {paper.authorships[0].author_name}")

        # If the search still no results: remove words from the end of the title (sometimes missing spaces confuses SemanticScholar)
        title = paper.title
        while paper_json["total"] == 0:
            title_words = title.split(" ")
            if len(title_words) < 3: # too few search terms will give a poor result, so treat the paper as unfindable
                return None
            title = " ".join(title_words[:-1])
            paper_json = self.__search_paper(title)

        # If the top paper doesn't have a matching author, look at the next results (note: it may have been renamed, but by the same author)
        paper_idx = 0
        total_papers = len(paper_json["data"])
        while not is_same_paper(paper_json["data"][paper_idx], paper):
            paper_idx += 1
            if paper_idx == total_papers: # no matches found in all the results
                return None
        
        return paper_json["data"][paper_idx]

    def get_author(self, id: str) -> dict[str, Any]:
        """Return the author json for the given id"""
        return self.__get_json(f"author/{id}?fields=name,affiliations,paperCount,citationCount,hIndex")

    def search_author(self, author_name: str, paper_json: dict[str, Any]) -> Optional[str]:
        """
        Given an author name return the correct authorId, by finding the authorId that wrote papers with the given co_authors
        
        If there are no search results from the API this returns none
        """
        co_author_ids = {author_json["authorId"] for author_json in paper_json["authors"]}
        author_name = self.__clean_query(author_name)
        retrieved_authors = self.__get_json(f"author/search?query={author_name}&fields=papers.authors&limit=20")

        # Find the most likely author by counting the number of shared co authors
        author_score: dict[str, int] = {} # stores number of matching co-authors for each authorId
        for author in retrieved_authors["data"]:
            potential_match_id = author["authorId"]
            # count the number of matching co_authors
            for paper in author["papers"]:    
                for co_author in paper["authors"]:
                    if co_author["authorId"] in co_author_ids:
                        author_score[potential_match_id] = author_score.get(potential_match_id, 0) + 1
        
        return max(author_score, key=lambda x: author_score[x]) if author_score else None


def extract_author(author_id_json: dict[str, str], paper_json: dict[str, Any], query_engine: SemanticScholarQuerier) -> Optional[Author]:
    """Search the API for author_id_json, then create and return an Author object"""
    # search for the Author if no id is given
    if author_id_json["authorId"] is None: 
        author_id = query_engine.search_author(author_id_json["name"], paper_json)
    else:
        author_id = author_id_json["authorId"]

    # query API and create author object
    if author_id:
        author_json = query_engine.get_author(author_id)
        return Author.from_API_json(author_json)
    return None


def get_author_data(papers: list[Paper]) -> list[Author]:
    """
    Create authors and extract their data from SemanticScholar
    Also mutates the paper list, adding author_ids to the authorships of each paper
    """
    authors: list[Author] = []
    seen_author_ids: set[str] = set()
    corrected_ids: dict[str, str] = {} # Create a map for correcting author ids (sometimes author ids are updated by the API)

    # Loop through all papers, searching for them on semantic scholar, then searching for their authors
    with SemanticScholarQuerier() as query_engine:
        for i, paper in enumerate(papers):
            paper_json = query_engine.get_paper(paper)
            if paper_json is None:
                continue

            # Retrieve and add all new author details
            for author_id_json in paper_json["authors"]:
                author_id = author_id_json["authorId"]
                if author_id is None or author_id not in seen_author_ids:
                    author = extract_author(author_id_json, paper_json, query_engine)
                    if not author: # failed to find author
                        continue
                    authors.append(author)

                    # Add the previous id (or found id if none), to the list of extracted ids
                    new_seen = author_id or author.author_id
                    seen_author_ids.add(new_seen)

                    if author_id != author.author_id: # store corrected ids
                        corrected_ids[author_id] = author.author_id

                # Correct id if it has been updated
                if author_id in corrected_ids:
                    author_id = corrected_ids[author_id]

                # Add author_id to the paper authorship info, to distinguish between different authors with similar names
                # If number of authors is consistent: Set author with the lowest Levenshtein distance to the current author_id, 
                    # otherwise require less than 5 levenshtein distance
                    # (note some authors leave out middle names, so exact string matching is not possible)
                distances = {authorship: name_distance(author_id, authorship.author_name) for authorship in paper.authorships}
                min_dist_authorship = min(distances, key=lambda x: distances[x])
                if len(paper_json["authors"]) == len(paper.authorships) or distances[min_dist_authorship] < 5:
                    min_dist_authorship.author_id = author_id
            
            logging.info(f"{i}/{len(papers)} papers processed")
    return authors
