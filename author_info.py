"""Provides functions that extract further data of each author from google scholar"""
from scholarly import scholarly
from typing import Any

from data import Authorship, Author

def extract_author_data(authorships: list[Authorship]) -> list[Author]:
    """Create authors and extract their data from google scholar"""
    unique_authors = {Author(authorship.author_name) for authorship in authorships}
    authors = list(unique_authors)
    # Convert authorships to a dataframe so we can find all co-authors for a given author (using a self merge)

    # Retrieve data from scholarly for each author
    for author in authors:
        search_result_gen = scholarly.search_author(author.author_name)
        try:
            search_result: dict[str, Any] = next(search_result_gen) # only look at the top search result, to reduce network request time
        except StopIteration: # No results for this author
            continue

        # only add details if an exact match for the name was found
        if search_result["name"].lower().strip() == author.author_name:
            # TODO: check if there is significant overlap with the coauthors, if not keep searching
            author.citations = search_result["citedby"] if "citedby" in search_result else None
            author.institution = search_result["affiliation"] if "affiliation" in search_result else None
            author.interests = search_result["interests"] if "interests" in search_result else None
            author.scholar_link = f"https://scholar.google.com/citations?user={search_result['scholar_id']}"
        print("Parsed new author:", author)
    return authors


def get_author_data(authorships: list[Authorship]) -> list[Author]:
    """Extract all author data, create Author objects to represent them"""
    authors = extract_author_data(authorships) # store authors in a class, then add in extra info from google scholar
    return authors
