# SupIRvisor
A simple project that scrapes the [SIGIR2022 paper list](https://sigir.org/sigir2022/program/accepted/) to find professors to talk to at the conference.

It uses [BeautifulSoup4](https://beautiful-soup-4.readthedocs.io/en/latest/) to scrape the documents, 
then joins the author data with their Google Scholar profile using the [Scholarly API](https://scholarly.readthedocs.io/en/stable/)
