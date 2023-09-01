"""Provides functions that extract further data of each author from google scholar"""
from __future__ import annotations

from typing import Iterator

from tqdm import tqdm

from analyse_conf.data import Author, JsonDict, Paper
from analyse_conf.semantic_scholar import SemanticScholarSearcher


def extract_author_id(
    author_id_json: dict[str, str | None],
    paper_json: JsonDict,
    search_engine: SemanticScholarSearcher,
) -> str | None:
    if author_id_json["authorId"]:
        return author_id_json["authorId"]
    assert author_id_json["name"] is not None
    return search_engine.search_author_by_name(author_id_json["name"], paper_json)


def extract_author(
    author_id_json: dict[str, str | None],
    paper_json: JsonDict,
    search_engine: SemanticScholarSearcher,
) -> Author | None:
    """Search the API for the author's id, then create and return an Author object"""
    author_id = extract_author_id(author_id_json, paper_json, search_engine)
    if not author_id:
        return None
    author_json = search_engine.search_author_by_id(author_id)
    return Author.from_api_json(author_json)


_author_id_map: dict[str, Author] = {}


def get_authors(paper_json: JsonDict, search_engine: SemanticScholarSearcher) -> Iterator[Author]:
    """Extract all authors for a given `paper_json`. Uses a cache"""
    for author_id_json in paper_json["authors"]:
        author_id: str | None = author_id_json["authorId"]
        if author_id and (author := _author_id_map.get(author_id)):
            yield author
            continue

        author = extract_author(author_id_json, paper_json, search_engine)
        if not author:
            continue
        yield author

        # Map author_ids to this extracted author, 
        # including outdated ones that differ between Paper and Author API
        if author_id and author_id != author.author_id:
            _author_id_map[author_id] = author
        _author_id_map[author.author_id] = author


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
            authorship: author.author_name.distance(authorship.author_name)
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


def get_papers_from_api(
    papers: list[Paper], search_engine: SemanticScholarSearcher
) -> Iterator[tuple[Paper, JsonDict]]:
    for paper in tqdm(papers):
        if paper_json := search_engine.search_paper(paper):
            yield paper, paper_json


def get_author_data(papers: list[Paper]) -> Iterator[Author]:
    """
    Create authors and extract their data from SemanticScholar
    Also mutates the paper list, adding author_ids to the authorships of each paper
    """
    filtered_authors: set[Author] = set()
    with SemanticScholarSearcher() as search_engine:
        for paper, paper_json in get_papers_from_api(papers, search_engine):
            paper_authors = get_authors(paper_json, search_engine)
            matched_authors = match_authors_to_authorships(list(paper_authors), paper)

            # yield any matched authors not previously yielded
            new_authors = matched_authors.difference(filtered_authors)
            yield from new_authors
            filtered_authors = filtered_authors.union(new_authors)
