"""Defines the Dataclasses used to represent Papers, Authors, and Authorship"""
import attr
from typing import Optional, Any


@attr.define
class Paper(object):
    """Simple class to store information about a paper"""
    title: str = attr.field()
    type: str = attr.field()
    authorships: list['Authorship'] = attr.field(factory=list)

@attr.define()
class Authorship(object):
    """Intermediate class to represent the many-to-many relationship between papers and authors"""
    title: str = attr.field()
    author_name: str = attr.field()
    author_id: Optional[str] = attr.field(default=None) # the SemanticScholar authorId, to be populated later

@attr.define(hash=True)
class Author(object):
    """Represents an author"""
    author_name: str = attr.field(hash=True, eq=True, order=True) # name can be used for comparison, but is unreliable as there are duplicates
    author_id: str = attr.field(hash=True, eq=True, order=True) # use the SemanticScholar authorId to uniquely identify authors

    # These attributes will be populated after initialisation
    citations: Optional[int] = attr.field(default=None, hash=False, eq=False, order=False)
    paper_count: Optional[int] = attr.field(default=None, hash=False, eq=False, order=False)
    h_index: Optional[int] = attr.field(default=None, hash=False, eq=False, order=False)
    institution: Optional[str] = attr.field(default=None, hash=False, eq=False, order=False) # not always available in the API

    @staticmethod
    def from_API_json(author_json: dict[str, Any]) -> 'Author':
        """Create author class from JSON returned by the SemanticScholar API"""
        return Author(
            author_name=author_json["name"], 
            author_id=author_json["authorId"],
            citations=author_json["citationCount"],
            paper_count=author_json["paperCount"],
            h_index=author_json["hIndex"],
            institution=author_json["affiliations"][0] if author_json["affiliations"] else None,
        )
