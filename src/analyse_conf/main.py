"""Combines the entire source code to analyse a conference based on authorship information"""
from __future__ import annotations

import logging
import pprint
from pathlib import Path
from typing import TYPE_CHECKING, Sequence

import attr
import pandas as pd

from analyse_conf import author_info, sigir_extract

if TYPE_CHECKING:
    from analyse_conf.data import Author, Authorship, Paper

OUTPUT_DIR = Path("outputs")
CONFERENCE_TO_WEBSCRAPER = {
    "SIGIR2022": sigir_extract
}


def webscrape_conference_data(conference: str) -> list[Paper]:
    papers = CONFERENCE_TO_WEBSCRAPER[conference].extract_data()
    print("Papers:")
    pprint.pprint(papers[:10])
    return papers


def query_author_data(papers: list[Paper]) -> list[Author]:
    print("\nExtracting Authors:")
    authors = list(author_info.get_author_data(papers))
    print("\n\nAuthors:")
    pprint.pprint(authors[:10])
    return authors


def get_authorships(papers: list[Paper]) -> list[Authorship]:
    authorships = [ats for paper in papers for ats in paper.authorships]
    print("\n\nAuthorships:")
    pprint.pprint(authorships[:10])
    return authorships


def make_output_dir(conf: str) -> Path:
    """Create the output_dir for a conference, and return the path to it"""
    (output_dir := OUTPUT_DIR / conf).mkdir(parents=True, exist_ok=True)
    return output_dir


def write_class_list(objects: Sequence[attr.AttrsInstance], file_name: Path) -> None:
    """Write a list of attrs objects to a csv file, overwriting old results"""
    file_name.unlink(missing_ok=True)
    rows = [attr.asdict(obj) for obj in objects]
    df = pd.DataFrame(rows)
    df.to_csv(file_name, index=False)


def write_data(conference: str, papers: list[Paper], authors: list[Author], authorships: list[Authorship]) -> None:
    output_dir = make_output_dir(conference)
    write_class_list(authors, output_dir / "authors.csv") # type: ignore[arg-type]
    write_class_list(papers, output_dir / "papers.csv")
    write_class_list(authorships, output_dir / "authorships.csv")


def analyse_conf(conference: str) -> None:
    """
    Webscrape the conference site to get author data
    Use SemanticScholar API to get citation and institution data
    TODO: Perform analysis of this data
        TODO: Create visualisations and tables of the results
    """
    logging.basicConfig(filename='download.log', format='%(asctime)s %(message)s', filemode="w", encoding='utf-8', level=logging.DEBUG)
    papers = webscrape_conference_data(conference)
    authors = query_author_data(papers)
    authorships = get_authorships(papers)
    write_data(conference, papers, authors, authorships)
