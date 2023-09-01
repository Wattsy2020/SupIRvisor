import warnings
from collections import Counter

from analyse_conf.author_info import Name
from analyse_conf.data import Author, Paper
from analyse_conf.semantic_scholar import SemanticScholarSearcher


def test_get_author_paper_consistency(papers: list[Paper], authors: list[Author]) -> None:
    """Check, for every paper, that the ids in authorships are unique (and that the authors with that id in API have a similar name)"""
    author_id_map: dict[str, Author] = {a.author_id: a for a in authors}
    num_papers_with_missing_authors = 0
    different_name_matches: list[tuple[str, str]] = []  # store borderline name matches and display at the end
    authors_with_papers: set[str] = set()

    with SemanticScholarSearcher() as search_engine:
        for paper in papers:
            author_id_count = Counter([authorship.author_id for authorship in paper.authorships])
            authors_with_papers = authors_with_papers.union({id for id in author_id_count.keys() if id is not None})

            # If paper has no author_ids, assert that it's not available on Semantic Scholar
            if author_id_count[None] == len(paper.authorships):
                if search_engine.search_paper(paper) is not None:
                    warnings.warn(
                        f"Paper is available on Semantic Scholar, but author information wasn't extracted, {paper.authorships=}"
                    )
                continue
            elif None in author_id_count:  # sometimes authors are missing on Semantic Scholar
                num_papers_with_missing_authors += 1

            # Check paper has no duplicate author ids
            for id, count in author_id_count.items():
                if id is not None:
                    assert count == 1, f"author_id: {id} occurs {id} times, {paper.authorships=}"

            # Check each Authorship object and Author object share a similar name
            for authorship in paper.authorships:
                if authorship.author_id is not None:  # can't check unmatched papers
                    assert (
                        authorship.author_id in author_id_map
                    ), f"Authorship.author_id is not found in any Author object {authorship=}"

                    name1 = authorship.author_name
                    name2 = author_id_map[authorship.author_id].author_name
                    if Name(name1).distance(Name(name2)) > 5:
                        different_name_matches.append((name1, name2))

    assert authors_with_papers == set(author_id_map.keys()), "Some authors have not been assigned to a paper"
    warnings.warn(f"For {num_papers_with_missing_authors} papers, not all authors are found by the SemanticScholar API")
    warnings.warn(f"Check the list of borderline name matches\n{different_name_matches}")
