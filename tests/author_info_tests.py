"""Tests author_info.py"""
from analyse_conf.author_info import initialise_name, is_initialed, name_distance
from analyse_conf.data import Author


def test_is_initialed() -> None:
    assert is_initialed("L. watts")
    assert not is_initialed("Liam Watts")
    assert is_initialed("Terence C. S. Tao")  # test initialed middle names are also recognized
    assert not is_initialed("Terence Chi-Shen Tao")
    assert is_initialed("Liam W.")  # even last names can be initialed
    assert is_initialed("Liam W")
    assert not is_initialed(" Liam ")  # sanity check


def test_initialise_name() -> None:
    assert initialise_name("liam watts") == ("l. watts", ["l."])
    assert initialise_name("francis william watts") == ("f. w. watts", ["f.", "w."])
    assert initialise_name("saul") == ("saul", [])
    assert initialise_name("l. watts") == ("l. watts", ["l."])


def test_name_distance() -> None:
    assert name_distance("liam watts", "liam watts") == 0
    assert name_distance("liam watts", "liAm WATts") == 0, "name distance should not be case sensitive"
    assert name_distance("liam watts", "lifm wftts") == 2
    assert name_distance("liam watts", "l. watts") == 0
    assert name_distance("liam watts", "L. watts") == 0
    assert name_distance("Liam watts", "l. watts") == 0
    assert name_distance("liam watts", "l watts") == 0
    assert name_distance("liam watts", "d. watts") == 4, "incorrect initialisms don't have a high distance"


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
