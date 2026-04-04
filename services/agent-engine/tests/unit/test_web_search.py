"""Tests for the web search stub tool."""

from __future__ import annotations

import pytest

from agent_engine.tools.web_search import web_search


@pytest.mark.asyncio
async def test_web_search_returns_three_results() -> None:
    results = await web_search("python async")
    assert len(results) == 3


@pytest.mark.asyncio
async def test_web_search_result_keys() -> None:
    results = await web_search("test query")
    for r in results:
        assert "title" in r
        assert "url" in r
        assert "snippet" in r


@pytest.mark.asyncio
async def test_web_search_includes_query_in_results() -> None:
    query = "machine learning"
    results = await web_search(query)
    assert query in results[0]["title"]
    assert query in results[0]["snippet"]
    assert query.replace(" ", "+") in results[0]["url"]


@pytest.mark.asyncio
async def test_web_search_results_are_distinct() -> None:
    results = await web_search("anything")
    urls = [r["url"] for r in results]
    assert len(set(urls)) == 3
