"""Tests author_info.py"""
import os
import pickle
import pytest
import warnings

from analyse_conf import sigir_extract
from analyse_conf.author_info import SemanticScholarQuerier, get_author_data, is_same_paper


def test_get_paper() -> None:
    """Test that a subset of papers from SIGIR can be found using SemanticScholarQuerier.get_paper"""
    papers = sigir_extract.extract_data()
    with SemanticScholarQuerier() as query_engine:
        for paper in papers:
            first_author_name = paper.authorships[0].author_name
            paper_json = query_engine.get_paper(paper)

            if paper_json is None:
                warnings.warn(f"No paper found for {paper.title=}")
                continue
            assert "authors" in paper_json, f"Authors field isn't returned for {paper.title=}"
            assert len(paper_json["authors"]) >= 1, f"There are no authors for a paper for {paper.title=}"
            assert is_same_paper(paper_json, paper), \
                f"Retrieved a paper with a different title, or author {paper.title=} {first_author_name=} {paper_json['title']=}"


def test_get_author() -> None:
    """Test that SemanticScholarQuerier.get_author returns all the required fields"""
    with SemanticScholarQuerier() as query_engine:
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


def test_query_cache() -> None:
    """Check that API queries are stored in the cache and persisted to disk"""
    cache_path = ".api_cache_test"
    test_url = "author/1741101?fields=affiliations,paperCount,citationCount,hIndex"

    # Check queries are written to the in memory cache
    with SemanticScholarQuerier(cache_path=cache_path) as query_engine:
        query_engine._SemanticScholarQuerier__get_json(test_url) # type: ignore # mypy doesn't understand private variable accessing
        assert test_url in query_engine._SemanticScholarQuerier__cache, "URL is not cached to dict" # type: ignore

    # Open the persisted cache and check its contents
    assert os.path.exists(cache_path), "Cache file not created"
    with open(cache_path, "rb") as file:
        cache = pickle.load(file)
    assert test_url in cache, "Queried URL is not stored in cache"

    os.remove(cache_path)
