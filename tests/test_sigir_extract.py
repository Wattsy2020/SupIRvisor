"""Test sigir_extract.py"""
import bs4

from analyse_conf import sigir_extract


def test_split_authors() -> None:
    assert sigir_extract.split_authors("test1 test2, author1 author2 and author3 author4") == [
        "test1 test2",
        "author1 author2",
        "author3 author4",
    ], "Fails to recognise `and`"
    assert sigir_extract.split_authors("Test1 test2") == ["Test1 test2"], "Fails to recognise single authors"
    assert sigir_extract.split_authors("af1 al1, af2 al2") == [
        "af1 al1",
        "af2 al2",
    ], "Fails to recognise authors separated only by commas"
    assert sigir_extract.split_authors("Author1 author1l and Author2 author2l") == [
        "Author1 author1l",
        "Author2 author2l",
    ], "Fails to extract two authors separated by and"


def test_get_paper_tags() -> None:
    # Check that they are tags, there's not much else we can test
    results = sigir_extract.get_paper_tags("https://sigir.org/sigir2022/program/accepted/")
    for result in results:
        assert isinstance(result, bs4.element.Tag)


def test_extract_paper_data() -> None:
    tags = sigir_extract.get_paper_tags("https://sigir.org/sigir2022/program/accepted/")
    papers = sigir_extract.extract_paper_data(tags)

    # Check that the papers are unique and have one of the four correct types
    paper_titles: set[str] = set()
    for paper in papers:
        assert paper.title not in paper_titles, "Paper title is not unique"
        assert paper.type in [
            "Long",
            "Perspectives",
            "Reproducibility",
            "Short",
            "Resource",
            "Demos",
            "SIRIP",
        ], "Paper type is not valid"
        paper_titles.add(paper.title)

    # Check that the authorships contain valid papers,
    authorship_titles: set[str] = set()
    for paper in papers:
        for authorship in paper.authorships:
            assert authorship.title in paper_titles, "The paper does not exist"
            authorship_titles.add(authorship.title)

    # Check that each paper has at least one author
    for title in paper_titles:
        assert title in authorship_titles, "The paper has no author"
