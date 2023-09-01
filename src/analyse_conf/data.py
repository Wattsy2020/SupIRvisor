"""Defines the Dataclasses used to represent Papers, Authors, and Authorship"""
from __future__ import annotations

import re
from typing import Any

import Levenshtein
from attrs import define, field

JsonDict = dict[str, Any]


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

    def __str__(self) -> str:
        return self.name


@define(slots=True, frozen=True)
class Paper:
    """Simple class to store information about a paper"""

    title: str
    type: str
    authorships: list[Authorship]

    @classmethod
    def from_author_names(cls, title: str, paper_type: str, author_names: list[str]):
        return Paper(title, paper_type, [Authorship(title, name) for name in author_names])


@define(slots=True, hash=True)
class Authorship:
    """Intermediate class to represent the many-to-many relationship between papers and authors"""

    title: str = field(hash=True)
    author_name: Name = field(converter=Name, hash=True)
    author_id: str | None = field(default=None)  # the SemanticScholar authorId, to be populated later


@define(slots=True, hash=True)
class Author:
    """Represents an author"""

    # name can be used for comparison, but is unreliable as there are duplicates
    author_name: Name = field(converter=Name, hash=True, eq=True, order=True)
    # use the SemanticScholar authorId to uniquely identify authors
    author_id: str = field(hash=True, eq=True, order=True)

    # These attributes will be populated after initialisation
    citations: int | None = field(default=None, hash=False, eq=False, order=False)
    paper_count: int | None = field(default=None, hash=False, eq=False, order=False)
    h_index: int | None = field(default=None, hash=False, eq=False, order=False)
    institution: str | None = field(default=None, hash=False, eq=False, order=False)  # not always available in the API

    @classmethod
    def from_api_json(cls, author_json: dict[str, Any]) -> Author:
        """Create author class from JSON returned by the SemanticScholar API"""
        return cls(
            author_name=author_json["name"],
            author_id=author_json["authorId"],
            citations=author_json["citationCount"],
            paper_count=author_json["paperCount"],
            h_index=author_json["hIndex"],
            institution=author_json["affiliations"][0] if author_json["affiliations"] else None,
        )
