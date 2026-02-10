"""
Web retrieval: fetch evidence from search/news APIs (Serper, Tavily).
Returns list of {title, url, snippet} (optionally date). Used alongside ChromaDB in the pipeline.
"""
import os
from typing import Any

# Default max results per query; total merged evidence is capped in pipeline
DEFAULT_MAX_RESULTS = 15


def _search_serper(query: str, max_results: int) -> list[dict]:
    """Call Serper Google Search API. Returns list of {title, url, snippet} (optional date)."""
    api_key = os.environ.get("SERPER_API_KEY", "").strip()
    if not api_key:
        return []

    try:
        import requests
        resp = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            json={"q": query, "num": min(max_results, 30)},
            timeout=15,
        )
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
    except Exception:
        return []

    organic = data.get("organic") or []
    out: list[dict] = []
    for item in organic[:max_results]:
        title = (item.get("title") or "").strip()
        url = (item.get("link") or "").strip()
        snippet = (item.get("snippet") or "").strip()[:500]
        if not url:
            continue
        entry: dict = {"title": title or "No title", "url": url, "snippet": snippet or ""}
        if item.get("date"):
            entry["date"] = item.get("date")
        out.append(entry)
    return out


def _search_tavily(query: str, max_results: int) -> list[dict]:
    """Call Tavily Search API. Returns list of {title, url, snippet} (optional date)."""
    api_key = os.environ.get("TAVILY_API_KEY", "").strip()
    if not api_key:
        return []

    try:
        import requests
        resp = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": query,
                "search_depth": "basic",
                "max_results": min(max_results, 20),
                "include_answer": False,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
    except Exception:
        return []

    results = data.get("results") or []
    out: list[dict] = []
    for item in results[:max_results]:
        title = (item.get("title") or "").strip()
        url = (item.get("url") or "").strip()
        content = (item.get("content") or "").strip()[:500]
        if not url:
            continue
        entry: dict = {"title": title or "No title", "url": url, "snippet": content or ""}
        if item.get("published_date"):
            entry["date"] = item.get("published_date")
        out.append(entry)
    return out


def search_web(query: str, max_results: int = DEFAULT_MAX_RESULTS) -> list[dict]:
    """
    Fetch evidence from the web for a given query. Uses Serper if SERPER_API_KEY is set,
    otherwise Tavily if TAVILY_API_KEY is set. Returns list of {title, url, snippet}
    (and optionally date). Returns [] if no API key is configured or on failure.
    """
    query = (query or "").strip()
    if not query:
        return []

    max_results = max(1, min(max_results, 20))

    # Prefer Serper, then Tavily
    if os.environ.get("SERPER_API_KEY", "").strip():
        results = _search_serper(query, max_results)
        if results:
            return results
    if os.environ.get("TAVILY_API_KEY", "").strip():
        results = _search_tavily(query, max_results)
        if results:
            return results

    return []


def is_web_search_configured() -> bool:
    """True if at least one web search API key is set."""
    return bool(
        os.environ.get("SERPER_API_KEY", "").strip()
        or os.environ.get("TAVILY_API_KEY", "").strip()
    )
