import pytest
from analyse_conf.author_info import get_author_data
from analyse_conf.data import Author, Paper
from analyse_conf.sigir_extract import extract_data


@pytest.fixture(scope="function")
def papers() -> list[Paper]:
    """Extract papers for testing"""
    return extract_data()


@pytest.fixture(scope="function")
def authors(papers: list[Paper]) -> list[Author]:
    """Extract authors for testing"""
    return list(get_author_data(papers))
