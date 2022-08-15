"""Combines the entire source code to analyse a conference based on authorship information"""
import os
import attr
import pandas as pd
from typing import Sequence

from analyse_conf import sigir_extract
from analyse_conf import author_info

conference_to_webscraper = {
    "SIGIR2022": sigir_extract
}


def make_output_dir(conf: str) -> str:
    """Create the output_dir for a conference, and return the path to it"""
    output_dir = f"outputs/{conf}"
    if not os.path.exists("outputs"):
        os.mkdir("outputs")
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    return output_dir


def write_class_list(objects: Sequence[object], file_name: str) -> None:
    """Write a list of attrs objects to a csv file, overwriting old results"""
    # Delete the file if it exists
    if os.path.exists(file_name):
        os.remove(file_name)

    # Write data to file
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

    # Webscrape conference data and write to file
    papers = conference_to_webscraper[conf].extract_data()
    print("Papers:", papers[:10])
    write_class_list(papers, f"{output_dir}/papers.csv")

    authors = author_info.get_author_data(papers)
    print("Authors:", authors[:10])
    write_class_list(authors, f"{output_dir}/authors.csv")

    #print("Authorships:", authorships[:10])
    #write_class_list(authorships, f"{output_dir}/authorships.csv")

if __name__ == "__main__":
    analyse_conf("SIGIR2022")