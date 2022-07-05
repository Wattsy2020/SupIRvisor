from posixpath import split
from re import search
import requests
import bs4
import pandas as pd
import attr
from scholarly import scholarly

from typing import Optional, Any


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


def get_paper_tags(url: str) -> list[bs4.element.Tag]:
    """Retrieve all the paragraph tags on the SIGIR page"""
    response = requests.get(url)
    response.raise_for_status()
    html = response.content
    soup = bs4.BeautifulSoup(html, "html.parser")
    body_text = soup.find("div", class_="post-body") # the main body of text
    paragraphs = body_text.find_all("p") # All paragraph tags are papers, or contain a href and indicate the type of paper
    return paragraphs


def split_authors(author_str: str) -> list[str]:
    """Split the typical academic list of authors into a list of strings"""
    authors = author_str.strip().split(" and ")
    split_authors = authors[0].split(", ")

    # there are a few lone authors, avoid throwing an error for them
    # also some final authors are separated by a ", " not an " and ", in which case they're already handled
    if len(split_authors) > 1 and len(authors) > 1:
        split_authors = split_authors + [authors[1]]
    return split_authors


def extract_paper_data(paper_tags: list[bs4.element.Tag]) -> tuple[list[Paper], list[Authorship]]:
    """Extract authorship, title and type information from the paper tags"""
    papers = []
    authorships = []
    current_paper_type: str
    for tag in paper_tags:
        if tag.find("a") is not None: # this tag contains a link and indicates the paper section
            current_paper_type = tag.a["name"]
        else: # extract the paper
            title = tag.b.text.strip() # titles are bolded
            author_str = tag.find(string=True, recursive=False)
            authors = split_authors(author_str)
            papers.append(Paper(title, current_paper_type))
            for author in authors:
                authorships.append(Authorship(title, author))
    return papers, authorships


def extract_author_data(authorships: list[Authorship]) -> list[Author]:
    """Create authors and extract their data from google scholar"""
    unique_authors = {Author(authorship.author_name) for authorship in authorships}
    authors = list(unique_authors)

    # Retrieve data from scholarly for each author
    for author in authors:
        author.author_name = author.author_name.lower().strip()
        search_result: dict[str, Any] = next(scholarly.search_author(author.author_name), None) # only look at the top search result, to reduce network request time
        if search_result is None: # No results for this author
            continue

        # only add details if an exact match for the name was found
        if search_result["name"].lower().strip() == author.author_name:
            author.citations = search_result["citedby"] if "citedby" in search_result else None
            author.institution = search_result["affiliation"] if "affiliation" in search_result else None
            author.interests = search_result["interests"] if "interests" in search_result else None
            author.scholar_link = f"https://scholar.google.com/citations?user={search_result['scholar_id']}"
        print("Parsed new author:", author)
    return authors


def main() -> None:
    paper_tags = get_paper_tags("https://sigir.org/sigir2022/program/accepted/") # Get all html elements that represent a paper
    papers, authorships = extract_paper_data(paper_tags) # Extract and Store papers as a Paper object, with title, authors and type
    print("Papers:", papers[:10])
    print("Authorships:", authorships[:10])

    authors = extract_author_data(authorships) # store authors in a class, then add in extra info from google scholar
    print("Authors:", authors[:10])

    # TODO: Convert to pandas dataframes and write to csv


if __name__ == "__main__":
    main()
