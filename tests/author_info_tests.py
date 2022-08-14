"""Tests author_info.py"""
from analyse_conf import sigir_extract
from analyse_conf.author_info import SemanticScholarQuerier, get_author_data


def test_get_paper() -> None:
    """Test that a subset of papers from SIGIR can be found using SemanticScholarQuerier.get_paper"""
    papers, _ = sigir_extract.extract_data()
    query_engine = SemanticScholarQuerier()
    for paper in papers[:10]:
        paper_json = query_engine.get_paper(paper.title)
        assert paper_json is not None, f"No paper found for {paper.title=}"
        assert "authors" in paper_json, f"Authors field isn't returned for {paper.title=}"
        assert len(paper_json["authors"]) >= 1, f"There are no authors for a paper for {paper.title=}"


def test_get_author() -> None:
    """Test that SemanticScholarQuerier.get_author returns all the required fields"""
    query_engine = SemanticScholarQuerier()
    author_json = query_engine.get_author("1741101")
    assert "authorId" in author_json
    assert "citationCount" in author_json
    assert "paperCount" in author_json
    assert "hIndex" in author_json
    assert "affiliations" in author_json
    assert isinstance(author_json["affiliations"], list)


def test_get_author_data() -> None:
    """Check that every author passed into author_info.get_author_data has complete data extracted"""
    # Check that id, citations, papercount, and h index are present in every author

    # Check that every author in the authorships list, has an author object
