"""Tests author_info.py"""
from analyse_conf.author_info import Name
from analyse_conf.data import Author


def test_is_initialed() -> None:
    assert Name("L. watts").is_initialed
    assert not Name("Liam Watts").is_initialed
    assert Name("Terence C. S. Tao").is_initialed  # test initialed middle names are also recognized
    assert not Name("Terence Chi-Shen Tao").is_initialed
    assert Name("Liam W.").is_initialed  # even last names can be initialed
    assert Name("Liam W").is_initialed
    assert not Name(" Liam ").is_initialed  # sanity check


def test_initialise_name() -> None:
    assert Name("liam watts").initialised() == ("l. watts", ["l."])
    assert Name("francis william watts").initialised() == ("f. w. watts", ["f.", "w."])
    assert Name("saul").initialised() == ("saul", [])
    assert Name("l. watts").initialised() == ("l. watts", ["l."])


def test_name_distance() -> None:
    assert Name("liam watts").distance(Name("liam watts")) == 0
    assert Name("liam watts").distance(Name("liAm WATts")) == 0, "name distance should not be case sensitive"
    assert Name("liam watts").distance(Name("lifm wftts")) == 2
    assert Name("liam watts").distance(Name("l. watts")) == 0
    assert Name("liam watts").distance(Name("L. watts")) == 0
    assert Name("Liam watts").distance(Name("l. watts")) == 0
    assert Name("liam watts").distance(Name("l watts")) == 0
    assert Name("liam watts").distance(Name("d. watts")) == 4, "incorrect initialisms don't have a high distance"


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
