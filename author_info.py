"""Provides functions that extract further data of each author from google scholar"""
import requests

from data import Authorship, Author

# Cache the results for each query, using a key value pair of Author name to Author data (actual value needs to be a list of authors with the same name)
    # Then look in the cache first before making a ScraperAPI request (to save money)
    # Persist the cache to disk at end of program 
    # (maybe it should be a global object created by this file, that has a destructor which persists the cache to disk, and a constructor that reads from it)
class SemanticScholarQuerier:
    """Make queries to the google scholar API, while keeping a persisted cache of previous queries, to avoid duplicate queries across sessions"""
    # Read cache in constructor
    
    # Write cache in destructor

    # Have a method for querying, that checks if a query is in the cache first
        # returns a generator, that returns further results for the same query if they are needed



def extract_author_data(authorships: list[Authorship]) -> list[Author]:
    """Create authors and extract their data from google scholar"""
    authors: set[Author] = set()

    # Retrieve data from semantic scholar for each author
    for authorship in authorships:
        # only add new authors
        if Author(authorship.author_name) in authors:
            continue
        
        # Search for paper
        response = requests.get(f"https://api.semanticscholar.org/graph/v1/paper/search?query={authorship.title}&fields=authors")
        response.raise_for_status()
        paper_json = response.json()
        if paper_json["total"] == 0: # check for results
            continue
        top_result = paper_json["data"][0]

        # Retrieve and add author details for the entire paper
        for author_id_json in top_result["authors"]:
            author = Author(author_id_json["name"])
            if author in authors:
                continue

            # query API and add as much data as we can
            response = requests.get(f"https://api.semanticscholar.org/graph/v1/author/{author_id_json['authorId']}?fields=affiliations,paperCount,citationCount,hIndex")
            response.raise_for_status()
            author_json = response.json()
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
