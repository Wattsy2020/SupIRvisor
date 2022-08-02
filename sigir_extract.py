"""
Web scraping to extract information about Accepted papers and Authors
from the SIGIR2022 Accepted paper list, located here: https://sigir.org/sigir2022/program/accepted/
"""
import requests
import bs4

from data import Paper, Authorship


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
                author = author.lower().strip()
                authorships.append(Authorship(title, author))
    return papers, authorships


def extract_data() -> tuple[list[Paper], list[Authorship]]:
    """Return the paper and authorship data for SIGIR2022"""
    paper_tags = get_paper_tags("https://sigir.org/sigir2022/program/accepted/") # Get all html elements that represent a paper
    papers, authorships = extract_paper_data(paper_tags) # Extract and Store papers as a Paper object, with title, authors and type
    return papers, authorships
