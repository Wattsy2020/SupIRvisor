import requests
import bs4
import pandas as pd
from attr import define, field

from typing import List, Dict, Set, Union, Optional, Any


@define
class Paper():
    """Simple class to store information about a paper"""
    title: str = field()
    type: str = field()
    authors: List[str] = field()
    

def get_paper_tags(url: str) -> List[bs4.element.Tag]:
    """Retrieve all the paragraph tags on the SIGIR page"""
    response = requests.get(url)
    response.raise_for_status()
    html = response.content
    soup = bs4.BeautifulSoup(html, "html.parser")
    body_text = soup.find("div", class_="post-body") # the main body of text
    paragraphs = body_text.find_all("p") # All paragraph tags are papers, or contain a href and indicate the type of paper
    return paragraphs


def split_authors(author_str: str) -> List[str]:
    """Split the typical academic list of authors into a list of strings"""
    authors = author_str.strip().split(" and ")
    authors[0] = authors[0].split(", ")
    if len(authors) > 1: # there are a few lone authors, avoid throwing an error for them
        authors = authors[0] + [authors[1]]
    return authors


def extract_paper_data(paper_tags: List[bs4.element.Tag]) -> List[Paper]:
    """Extract authorship, title and type information from the paper tags"""
    papers = []
    current_paper_type: str
    for tag in paper_tags:
        if tag.find("a") is not None: # this tag contains a link and indicates the paper section
            current_paper_type = tag.a["name"]
        else: # extract the paper
            title = tag.b.text.strip() # titles are bolded
            author_str = tag.find(text=True, recursive=False)
            authors = split_authors(author_str)
            papers.append(Paper(title, current_paper_type, authors))
    return papers


def main() -> None:
    paper_tags = get_paper_tags("https://sigir.org/sigir2022/program/accepted/")
    paper_data = extract_paper_data(paper_tags) # Extract and Store papers as a Paper object, with title, authors and type
    # Then store authors in a class, with a dict mapping to accumulate paper data
    # Add in extra info from google scholar
    # Convert to pandas dataframe and write to csv
    print(paper_data[:10])


if __name__ == "__main__":
    main()
