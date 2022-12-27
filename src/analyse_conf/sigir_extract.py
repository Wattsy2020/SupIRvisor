"""
Web scraping to extract information about Accepted papers and Authors
from the SIGIR2022 Accepted paper list, located here: https://sigir.org/sigir2022/program/accepted/
"""
import bs4
import requests

from analyse_conf.data import Authorship, Paper


def get_paper_tags(url: str) -> list[bs4.element.Tag]:
    """
    Retrieve all the paragraph tags on the SIGIR page
    These paragraph tags are papers, or contain a href and indicate the type of paper
    """
    response = requests.get(url)
    response.raise_for_status()
    html = response.content
    soup = bs4.BeautifulSoup(html, "html.parser")
    body_text = soup.find("div", class_="post-body") # the main body of text
    paragraphs = body_text.find_all("p")
    return paragraphs


def split_authors(author_str: str) -> list[str]:
    """Split the typical academic list of authors into a list of strings"""
    authors = author_str.strip().split(" and ")
    separated_authors = authors[0].split(", ")

    # there are a few lone authors, avoid throwing an error for them
    # also some final authors are separated by a ", " not an " and ", in which case they're already handled
    if len(authors) > 1:
        separated_authors.append(authors[1])
    return separated_authors


def extract_paper_data(paper_tags: list[bs4.element.Tag]) -> list[Paper]:
    """Extract authorship, title and type information from the paper tags into a list of Paper objects"""
    papers = []
    current_paper_type: str
    for tag in paper_tags:
        if tag.find("a") is not None: # this tag contains a link and indicates the paper section
            current_paper_type = tag.a["name"]
        else: # extract the paper
            title = tag.b.text.strip() # titles are bolded
            paper = Paper(title, current_paper_type)

            author_str = tag.find(string=True, recursive=False)
            authors = split_authors(author_str)
            for author in authors:
                authorship = Authorship(title, author.lower().strip())
                paper.authorships.append(authorship)
            papers.append(paper)
    return papers


def extract_data() -> list[Paper]:
    """Return the paper and authorship data for SIGIR2022"""
    paper_tags = get_paper_tags("https://sigir.org/sigir2022/program/accepted/")
    papers = extract_paper_data(paper_tags)
    return papers
