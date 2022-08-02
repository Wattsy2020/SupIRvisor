"""Combines the entire source code to analyse a conference based on authorship information"""
import sigir_extract
import author_info

conference_to_webscraper = {
    "SIGIR2022": sigir_extract
}

def main(conf: str) -> None:
    """
    Webscrape the conference site to get author data
        TODO: Write this raw data to file
    Use google scholar API to get institution data
        TODO: Write the data to file
    TODO: Perform analysis of this data
        TODO: Create visualisations and tables of the results
    """
    papers, authorships = conference_to_webscraper[conf].extract_data()
    print("Papers:", papers[:10])
    print("Authorships:", authorships[:10])

    authors = author_info.get_author_data(authorships)
    print("Authors:", authors[:10])


if __name__ == "__main__":
    main("SIGIR2022")
