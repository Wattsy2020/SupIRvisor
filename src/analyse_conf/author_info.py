"""Provides functions that extract further data of each author from google scholar"""
from __future__ import annotations

import re
from typing import Iterator

import Levenshtein
from attrs import define, field
from tqdm import tqdm

from analyse_conf.data import Author, JsonDict, Paper
from analyse_conf.semantic_scholar import SemanticScholarSearcher


def lowercase(string: str) -> str:
    return string.lower()


def levenshtein_distance(left: str, right: str) -> int:
        distance = Levenshtein.distance(left, right)  # type: ignore
        assert isinstance(distance, int)
        return distance


@define(frozen=True, slots=True)
class Name:
    name: str = field(converter=lowercase)

    # match strings that have a single isolated char with an optional dot
    INITIALED_NAME_PATTERN = re.compile(r".*(?:^| )\w[\.]?(?:$| ).*")

    @property
    def is_initialed(self) -> bool:
        """Whether a name is initialised, e.g. as L. Watts or L Watts"""
        return bool(re.match(Name.INITIALED_NAME_PATTERN, self.name))

    def initialised(self) -> tuple[str, list[str]]:
        """Convert a full written name into an intialised one, e.g. Liam Watts -> L. Watts"""
        *name_parts, last_name = self.name.split(" ")
        initials = [f"{part[0]}." for part in name_parts]
        return " ".join(initials + [last_name]), initials

    def distance(self, other: Name) -> int:
        """
        Calculate the levenshtein distance between two names
        Also account for academic naming fashion of using initials, e.g. writing L. Watts for Liam Watts
        """
        if self.is_initialed or other.is_initialed:
            initialed_name, initials = self.initialised()
            other_initialed_name, other_initials = other.initialised()
            if initials == other_initials:
                return levenshtein_distance(initialed_name, other_initialed_name)
        return levenshtein_distance(self.name, other.name)


def extract_author(
    author_id_json: dict[str, str | None],
    paper_json: JsonDict,
    search_engine: SemanticScholarSearcher,
) -> Author | None:
    """Search the API for author_id_json, then create and return an Author object"""
    # search for the Author if no id is given
    if author_id_json["authorId"] is None:
        assert author_id_json["name"] is not None
        author_id = search_engine.search_author_by_name(author_id_json["name"], paper_json)
    else:
        author_id = author_id_json["authorId"]

    # query API and create author object
    if author_id:
        author_json = search_engine.search_author_by_id(author_id)
        return Author.from_api_json(author_json)
    return None


_author_id_map: dict[str, Author] = {}


def get_authors(paper_json: JsonDict, search_engine: SemanticScholarSearcher) -> list[Author]:
    """Extract all authors for a given `paper_json`. Uses a cache"""
    paper_authors: list[Author] = []
    for author_id_json in paper_json["authors"]:
        author_id: str | None = author_id_json["authorId"]

        # Search API for authors we haven't extracted yet
        if author_id is None or author_id not in _author_id_map:
            author = extract_author(author_id_json, paper_json, search_engine)
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
            authorship: Name(author.author_name).distance(Name(authorship.author_name))
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
            matched_authors = match_authors_to_authorships(paper_authors, paper)

            # yield any matched authors not previously yielded
            new_authors = matched_authors.difference(filtered_authors)
            yield from new_authors
            filtered_authors = filtered_authors.union(new_authors)
