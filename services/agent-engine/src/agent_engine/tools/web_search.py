"""Web search tool stub returning mock results.

Ready to integrate with a real search API (Brave, SerpAPI, etc.) later.
"""

from __future__ import annotations


async def web_search(query: str) -> list[dict]:
    """Return mock search results for *query*.

    Each result has keys: title, url, snippet.
    """
    return [
        {
            "title": f"Result 1 for: {query}",
            "url": f"https://example.com/search?q={query.replace(' ', '+')}&r=1",
            "snippet": f"This is a relevant excerpt about {query} from a trusted source.",
        },
        {
            "title": f"Result 2 for: {query}",
            "url": f"https://example.com/search?q={query.replace(' ', '+')}&r=2",
            "snippet": f"Another informative passage related to {query}.",
        },
        {
            "title": f"Result 3 for: {query}",
            "url": f"https://example.com/search?q={query.replace(' ', '+')}&r=3",
            "snippet": f"Additional context and details about {query}.",
        },
    ]
