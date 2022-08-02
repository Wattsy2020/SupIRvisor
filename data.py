"""Defines the Dataclasses used to represent Papers, Authors, and Authorship"""
import attr
from typing import Optional


@attr.define
class Paper(object):
    """Simple class to store information about a paper"""
    title: str = attr.field()
    type: str = attr.field()

@attr.define()
class Authorship(object):
    """Intermediate class to represent the many-to-many relationship between papers and authors"""
    title: str = attr.field()
    author_name: str = attr.field()

@attr.define(hash=True)
class Author(object):
    """Represents an author"""
    author_name: str = attr.field(hash=True, eq=True, order=True) # use the name to hash authors

    # These attributes will be populated after initialisation
    scholar_link: Optional[str] = attr.field(default=None, hash=False, eq=False, order=False)
    institution: Optional[str] = attr.field(default=None, hash=False, eq=False, order=False)
    citations: Optional[int] = attr.field(default=None, hash=False, eq=False, order=False)
    interests: Optional[list[str]] = attr.field(default=None, hash=False, eq=False, order=False)
