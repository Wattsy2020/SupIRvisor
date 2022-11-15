"""Combines the entire source code to analyse a conference based on authorship information"""
from pathlib import Path
import attr
import pprint
import pandas as pd
from typing import Sequence

from analyse_conf import sigir_extract
from analyse_conf import author_info

conference_to_webscraper = {
    "SIGIR2022": sigir_extract
}


def make_output_dir(conf: str) -> Path:
    """Create the output_dir for a conference, and return the path to it"""
    output_dir = Path("outputs") / conf
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def write_class_list(objects: Sequence[object], file_name: Path) -> None:
    """Write a list of attrs objects to a csv file, overwriting old results"""
    file_name.unlink(missing_ok=True)
    rows = [attr.asdict(obj) for obj in objects]
    df = pd.DataFrame(rows)
    df.to_csv(file_name, index=False)


def analyse_conf(conf: str) -> None:
    """
    Webscrape the conference site to get author data
    Use SemanticScholar API to get citation and institution data
    TODO: Perform analysis of this data
        TODO: Create visualisations and tables of the results
    """
    output_dir = make_output_dir(conf)

    # Webscrape conference data
    papers = conference_to_webscraper[conf].extract_data()
    print("Papers:")
    pprint.pprint(papers[:10])

    # Get author data from SemanticScholar
    authors = author_info.get_author_data(papers)
    print("\n\nAuthors:")
    pprint.pprint(authors[:10])

    # Extract authorships after the author_id information has been added to papers list
    authorships = [ats for paper in papers for ats in paper.authorships]
    print("\n\nAuthorships:")
    pprint.pprint(authorships[:10])

    # Write data to file
    write_class_list(authors, output_dir / "authors.csv")
    write_class_list(papers, output_dir / "papers.csv")
    write_class_list(authorships, output_dir / "authorships.csv")

if __name__ == "__main__":
    analyse_conf("SIGIR2022")
