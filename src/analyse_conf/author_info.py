"""Provides functions that extract further data of each author from google scholar"""
from __future__ import annotations

import re
from typing import Iterator

import Levenshtein
from tqdm import tqdm

from analyse_conf.data import Author, JsonDict, Paper
from analyse_conf.semantic_scholar import SemanticScholarQuerier


def is_initialed(name: str) -> bool:
    """
    Determine whether a name is initialised, e.g. as L. Watts or L Watts
    match strings that have a single isolated char with an optional dot
    """
    return bool(re.match(r".*(?:^| ).[\.]?(?:$| ).*", name))


def initialise_name(name: str) -> tuple[str, list[str]]:
    """Convert a full written name into an intialised one, e.g. Liam Watts -> L. Watts"""
    name_sections = name.split(" ")
    initials = [f"{name_sec[0]}." for name_sec in name_sections[:-1]]
    return " ".join(initials + [name_sections[-1]]), initials


def levenshtein_distance(left: str, right: str) -> int:
    distance = Levenshtein.distance(left, right) # type: ignore
    assert isinstance(distance, int)
    return distance


def name_distance(name1: str, name2: str) -> int:
    """
    Calculate the levenshtein distance between two names
    Also account for academic naming fashion of using initials, e.g. writing L. Watts for Liam Watts
    """
    name1 = name1.lower()
    name2 = name2.lower()
    if is_initialed(name1) or is_initialed(name2):
        initialed_name1, initials1 = initialise_name(name1)
        initialed_name2, initials2 = initialise_name(name2)
        if initials1 == initials2:
            return levenshtein_distance(initialed_name1, initialed_name2)
    return levenshtein_distance(name1, name2)


def extract_author(
    author_id_json: dict[str, str],
    paper_json: JsonDict,
    query_engine: SemanticScholarQuerier,
) -> Author | None:
    """Search the API for author_id_json, then create and return an Author object"""
    # search for the Author if no id is given
    if author_id_json["authorId"] is None:
        author_id = query_engine.search_author(author_id_json["name"], paper_json)
    else:
        author_id = author_id_json["authorId"]

    # query API and create author object
    if author_id:
        author_json = query_engine.get_author(author_id)
        return Author.from_api_json(author_json)
    return None


_author_id_map: dict[str, Author] = {}
def get_authors(
    paper_json: JsonDict, query_engine: SemanticScholarQuerier
) -> list[Author]:
    """Extract all authors for a given `paper_json`. Uses a cache"""
    paper_authors: list[Author] = []
    for author_id_json in paper_json["authors"]:
        author_id: str | None = author_id_json["authorId"]

        # Search API for authors we haven't extracted yet
        if author_id is None or author_id not in _author_id_map:
            author = extract_author(author_id_json, paper_json, query_engine)
            if not author:  # failed to find author
                continue

            # Map author_ids to this extracted author
            # (including outdated ones that differ between Paper and Author API)
            # Do not map author_id of None, as there are multiple such author_ids
            if author_id is None:  # update so we can later retrieve the author
                author_id = author.author_id
            elif author_id != author.author_id:
                _author_id_map[author_id] = author
            _author_id_map[author.author_id] = author

        paper_authors.append(_author_id_map[author_id])
    return paper_authors


def match_authors_to_authorships(authors: list[Author], paper: Paper) -> set[Author]:
    """
    Given a list of candidate `authors`, match their names to the authors of the given `paper`,
    filling in the author_ids in paper.authorships
    This helps in later data analysis, to distinguish between different authors with similar names

    Returns:
        authors: The set of authors who were matched with a paper's authorships.
            This leaves out candidate authors whose name wasn't similar to any authors of the paper
    """
    matched_authors: set[Author] = set()
    for author in authors:
        # Greedily match the current Author against all authorships that haven't been matched with
        distances = {
            authorship: name_distance(author.author_name, authorship.author_name)
            for authorship in paper.authorships
            if authorship.author_id is None
        }

        # Stop once all authors have been matched
        # This happens when there are additional authors listed on SemanticScholar, that aren't listed in the conference data
        if not distances:
            break
        min_dist_authorship = min(distances.items(), key=lambda key_value: key_value[1])[0]

        # If number of authors is consistent: Set author with the lowest Levenshtein distance to the current author_id
        # otherwise require less than 5 levenshtein distance
        # (note some authors leave out middle names, so exact string matching is not possible)
        if len(authors) == len(paper.authorships) or distances[min_dist_authorship] < 5:
            min_dist_authorship.author_id = author.author_id
            matched_authors.add(author)
    return matched_authors


def get_author_data(papers: list[Paper]) -> Iterator[Author]:
    """
    Create authors and extract their data from SemanticScholar
    Also mutates the paper list, adding author_ids to the authorships of each paper
    """
    filtered_authors: set[Author] = set()
    with SemanticScholarQuerier() as query_engine:
        for paper in tqdm(papers):
            paper_json = query_engine.get_paper(paper)
            if paper_json is None:
                continue

            paper_authors = get_authors(paper_json, query_engine)
            matched_authors = match_authors_to_authorships(paper_authors, paper)

            # yield any matched authors not previously yielded
            new_authors = matched_authors.difference(filtered_authors)
            yield from new_authors
            filtered_authors = filtered_authors.union(new_authors)
