"""Tests author_info.py"""
import os
import pickle
import pytest
import warnings
from collections import Counter

from analyse_conf.data import Paper, Author, Authorship
from analyse_conf import sigir_extract
from analyse_conf.author_info import SemanticScholarQuerier, get_author_data, is_same_paper, initialise_name, name_distance


@pytest.fixture
def papers() -> list[Paper]:
    """Extract papers for testing"""
    return sigir_extract.extract_data()


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
    

def test_get_paper(papers: list[Paper]) -> None:
    """Test that a subset of papers from SIGIR can be found using SemanticScholarQuerier.get_paper"""
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


def test_get_paper_author_consistency(papers: list[Paper]) -> None:
    """Calculate the number of papers for which not all authors are represented by the SemanticScholar API"""
    num_inconsistent_authors = 0
    with SemanticScholarQuerier() as query_engine:
        for paper in papers:
            paper_json = query_engine.get_paper(paper)
            if paper_json is None:
                continue
            if len(paper_json["authors"]) != len(paper.authorships):
                num_inconsistent_authors += 1
    warnings.warn(f"For {num_inconsistent_authors} papers, not all authors are found by the SemanticScholar API")


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


def test_search_author() -> None:
    """Test that searching for authors correctly matches based on co_author info"""
    test_author_id = '2067085425'
    test_author_name = 'Nicholas Lim'
    test_paper_json = {
        'paperId': '684877258525dced03ebb049c7bf3c3c69999f9f', 
        'title': 'Hierarchical Multi-Task Graph Recurrent Network for Next POI Recommendation', 
        'authors': [
                {'authorId': None, 'name': 'Nicholas Lim'}, {'authorId': '2019961', 'name': 'Bryan Hooi'}, 
                {'authorId': '1794527', 'name': 'See-Kiong Ng'}, {'authorId': '1995261298', 'name': 'Yong Liang Goh'}, 
                {'authorId': '49361860', 'name': 'Renrong Weng'}, {'authorId': '2052819973', 'name': 'Rui Tan'}
            ]
        }
    with SemanticScholarQuerier() as query_engine:
        calc_author_id = query_engine.search_author(test_author_name, test_paper_json)
    assert test_author_id == calc_author_id, "Wrong author ids retrieved"
    # TODO: Check that all authors we've extracted (from get_author_data) are retrieved by this method


def test_get_author_data(papers: list[Paper]) -> None:
    """Check that every author passed into author_info.get_author_data has complete data extracted"""
    authors = get_author_data(papers)
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

    # Check, for every paper, that the ids in authorships are unique (and that the authors with that id in API have a similar name
    num_papers_with_missing_authors = 0
    different_name_matches: list[tuple[str, str]] = [] # store borderline name matches and display at the end
    authors_with_papers: set[str] = set()
    with SemanticScholarQuerier() as query_engine:
        for paper in papers:
            author_id_count = Counter([authorship.author_id for authorship in paper.authorships])
            authors_with_papers = authors_with_papers.union(set(author_id_count.keys()))

            # If paper has no author_ids, assert that it's not available on Semantic Scholar
            if author_id_count[None] == len(paper.authorships):
                assert query_engine.get_paper(paper) is None, "Paper is available on Semantic Scholar, but author information wasn't extracted"
                continue
            elif None in author_id_count: # sometimes authors are missing on Semantic Scholar
                num_papers_with_missing_authors += 1
            
            # Check paper has no duplicate author ids
            for id, count in author_id_count.items():
                if id is not None:
                    assert count == 1, f"author_id: {id} occurs {id} times, {paper.authorships=}"
                
            # Check each Authorship object and Author object share a similar name
            for authorship in paper.authorships:
                if authorship.author_id is not None: # can't check unmatched papers
                    assert authorship.author_id in author_id_map, f"Authorship.author_id is not found in any Author object {authorship=}"

                    name1 = authorship.author_name
                    name2 = author_id_map[authorship.author_id].author_name
                    if name_distance(name1, name2) > 5:
                        different_name_matches.append((name1, name2))
    
    assert authors_with_papers == set(author_id_map.keys()), "Some authors have not been assigned to a paper" # type: ignore
    warnings.warn(f"For {num_papers_with_missing_authors} papers, not all authors are found by the SemanticScholar API")
    warnings.warn(f"Check the list of borderline name matches\n{different_name_matches}")


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
