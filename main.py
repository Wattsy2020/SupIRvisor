"""Combines the entire source code to analyse a conference based on authorship information"""
import os
import attr
import pandas as pd

import sigir_extract
import author_info

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


def write_class_list(objects: list[object], file_name: str) -> None:
    """Write a list of attrs objects to a csv file"""
    rows = [attr.asdict(obj) for obj in objects]
    df = pd.DataFrame(rows)
    df.to_csv(file_name, index=False)


def main(conf: str) -> None:
    """
    Webscrape the conference site to get author data
    Use google scholar API to get institution data
    TODO: Perform analysis of this data
        TODO: Create visualisations and tables of the results
    """
    output_dir = make_output_dir(conf)

    # Webscrape conference data and write to file
    papers, authorships = conference_to_webscraper[conf].extract_data()
    print("Papers:", papers[:10])
    print("Authorships:", authorships[:10])
    write_class_list(papers, f"{output_dir}/papers.csv")
    write_class_list(authorships, f"{output_dir}/authorships.csv")

    authors = author_info.get_author_data(authorships)
    print("Authors:", authors[:10])
    write_class_list(authors, f"{output_dir}/authors.csv")


if __name__ == "__main__":
    main("SIGIR2022")
