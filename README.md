# SupIRvisor
A simple project that scrapes the [SIGIR2022 paper list](https://sigir.org/sigir2022/program/accepted/) and performs analysis and data visualisation. I'm particularly interested in which institutions and researchers are the most prolific, and whether prolific people/institutions collaborate more.

It uses [BeautifulSoup4](https://beautiful-soup-4.readthedocs.io/en/latest/) to scrape the documents, 
then joins the author data with their Semantic Scholar profile using the [Academic Graph API](https://api.semanticscholar.org/api-docs/graph)

To analyse a conference run `python main.p <conference>`, where `<conference>` is any suported conference (without the brackets). This creates three output files in the `outputs/<conference>/` directory that you can further analyse: `authors.csv`, `authorships.csv`, and `papers.csv`.

Supported conferences are:
- SIGIR2022

## Developer Environment Notes
To make changes to this project, you need to clone the repo and install the package in editable mode with `pip install -e .`
Run `./test.sh` to perform type checking and testing
Note that the tests require making a large number of queries to the Academic Graph API, so will take hours to run the first time. Ensure you preserve the ".api_cache" file, so these requests don't need to be repeated in future
