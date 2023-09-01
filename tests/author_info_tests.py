"""Tests author_info.py"""
from analyse_conf.data import Author


def test_get_author_data(authors: list[Author]) -> None:
    """Check that every author passed into author_info.get_author_data has complete data extracted"""
    author_id_map: dict[str, Author] = {a.author_id: a for a in authors}

    # Check that id, citations, papercount, and h index are present in every author
    for author in authors:
        assert isinstance(author.author_id, str)
        assert isinstance(author.citations, int)
        assert isinstance(author.paper_count, int)
        assert isinstance(author.h_index, int)
        if author.institution is not None:
            assert isinstance(author.institution, str)
    assert len(author_id_map) == len(authors), "There are duplicate authors in the extracted list"
