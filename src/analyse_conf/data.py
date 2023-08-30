"""Defines the Dataclasses used to represent Papers, Authors, and Authorship"""
from __future__ import annotations

from typing import Any

from attrs import define, field


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
    author_name: str = field(hash=True)
    author_id: str | None = field(default=None) # the SemanticScholar authorId, to be populated later


@define(slots=True, hash=True)
class Author:
    """Represents an author"""
    author_name: str = field(hash=True, eq=True, order=True) # name can be used for comparison, but is unreliable as there are duplicates
    author_id: str = field(hash=True, eq=True, order=True) # use the SemanticScholar authorId to uniquely identify authors

    # These attributes will be populated after initialisation
    citations: int | None = field(default=None, hash=False, eq=False, order=False)
    paper_count: int | None = field(default=None, hash=False, eq=False, order=False)
    h_index: int | None = field(default=None, hash=False, eq=False, order=False)
    institution: str | None = field(default=None, hash=False, eq=False, order=False) # not always available in the API

    @classmethod
    def from_api_json(cls, author_json: dict[str, Any]) -> Author:
        """Create author class from JSON returned by the SemanticScholar API"""
        return cls(
            author_name=author_json["name"], 
            author_id=author_json["authorId"],
            citations=author_json["citationCount"],
            paper_count=author_json["paperCount"],
            h_index=author_json["hIndex"],
            institution=author_json["affiliations"][0] if author_json["affiliations"] else None
        )
