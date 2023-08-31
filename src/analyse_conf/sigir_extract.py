"""
Web scraping to extract information about Accepted papers and Authors
from the SIGIR2022 Accepted paper list, located here: https://sigir.org/sigir2022/program/accepted/
"""
from __future__ import annotations

import bs4
import requests

from analyse_conf.data import Paper


def get_paper_tags(url: str) -> list[bs4.element.Tag]:
    """
    Retrieve all the paragraph tags on the SIGIR page
    These paragraph tags are papers, or contain a href and indicate the type of paper
    """
    response = requests.get(url)
    response.raise_for_status()
    html = response.content
    soup = bs4.BeautifulSoup(html, "html.parser")
    body_text = soup.find("div", class_="post-body")  # the main body of text
    assert isinstance(body_text, bs4.element.Tag)
    paragraphs = body_text.find_all("p")
    return paragraphs


def extract_title(tag: bs4.element.Tag) -> str:
    """Get the paper title from a paragraph tag"""
    bolded_title = tag.b  # titles are bolded
    assert bolded_title is not None
    return bolded_title.text.strip()


def split_authors(author_str: str) -> list[str]:
    """Split the typical academic list of authors into a list of strings"""
    authors = author_str.strip().split(" and ")
    separated_authors = authors[0].split(", ")

    # there are a few lone authors, avoid throwing an error for them
    # also some final authors are separated by a ", " not an " and ", in which case they're already handled
    if len(authors) > 1:
        separated_authors.append(authors[1])
    return separated_authors


def extract_authors(tag: bs4.element.Tag) -> list[str]:
    author_str = tag.find(string=True, recursive=False)
    assert isinstance(author_str, str)
    author_names = split_authors(author_str)
    return [name.lower().strip() for name in author_names]


def extract_paper(tag: bs4.element.Tag, paper_type: str) -> Paper:
    title = extract_title(tag)
    author_names = extract_authors(tag)
    return Paper.from_author_names(title, paper_type, author_names)


def is_paper_type(tag: bs4.element.Tag) -> bool:
    """Tags that are links indicate a paper section"""
    return tag.find("a") is not None


def extract_paper_type(tag: bs4.element.Tag) -> str:
    link = tag.find("a")
    assert isinstance(link, bs4.element.Tag)
    paper_type = link["name"]
    assert isinstance(paper_type, str)
    return paper_type


def extract_paper_data(paper_tags: list[bs4.element.Tag]) -> list[Paper]:
    """Extract authorship, title and type information from the paper tags into a list of Paper objects"""
    papers: list[Paper] = []
    current_paper_type: str | None = None
    for tag in paper_tags:
        if is_paper_type(tag):
            current_paper_type = extract_paper_type(tag)
        else:
            assert current_paper_type is not None
            papers.append(extract_paper(tag, current_paper_type))
    return papers


def extract_data() -> list[Paper]:
    """Return the paper and authorship data for SIGIR2022"""
    paper_tags = get_paper_tags("https://sigir.org/sigir2022/program/accepted/")
    papers = extract_paper_data(paper_tags)
    return papers
