"""Academic literature search tool for literature_web_search agent."""

from omnigent_client import tool
from lab.tools import search_academic_papers


@tool
def search_papers(query: str, limit: int = 5) -> list:
    """Search academic publications strictly from Springer, Nature, IEEE, and arXiv.

    Zero hallucination policy: results are queried live from OpenAlex or retrieved from
    verified academic indexes. Articles from unapproved sources are rejected.

    Args:
        query: Academic topic or keywords to search for.
        limit: Maximum number of papers to return (default 5).

    Returns:
        List of papers with title, authors, year, venue, DOI, URL, and abstract excerpt.
    """
    return search_academic_papers(query=query, limit=limit)
