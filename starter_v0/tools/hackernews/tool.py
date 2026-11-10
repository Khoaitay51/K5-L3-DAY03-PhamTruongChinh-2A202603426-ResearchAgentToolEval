from __future__ import annotations

import time
from typing import Any

import requests

from tools._shared import TIMEOUT, clamp_int, domain, err, pick


HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search"
HN_SEARCH_BY_DATE_URL = "https://hn.algolia.com/api/v1/search_by_date"
TIMEFRAME_SECONDS = {"day": 86_400, "week": 7 * 86_400, "month": 30 * 86_400, "year": 365 * 86_400}


def search_hackernews(query: str = "", sort_by: str = "relevance", timeframe: str = "all", limit: int = 5) -> dict[str, Any]:
    try:
        query = (query or "").strip() if isinstance(query, str) else ""
        if not query:
            raise ValueError("query must be a non-empty string")
        sort_by = pick(sort_by, ("relevance", "date"), "relevance")
        timeframe = pick(timeframe, ("day", "week", "month", "year", "all"), "all")
        limit = clamp_int(limit, default=5, low=1, high=20)

        params: dict[str, Any] = {"query": query, "tags": "story", "hitsPerPage": limit}
        if timeframe != "all":
            params["numericFilters"] = f"created_at_i>{int(time.time()) - TIMEFRAME_SECONDS[timeframe]}"
        url = HN_SEARCH_BY_DATE_URL if sort_by == "date" else HN_SEARCH_URL

        response = requests.get(url, params=params, timeout=TIMEOUT)
        response.raise_for_status()
        hits = response.json().get("hits", []) or []

        items = []
        for hit in hits:
            object_id = hit.get("objectID")
            if not object_id or not hit.get("title"):
                continue
            hn_url = f"https://news.ycombinator.com/item?id={object_id}"
            story_url = hit.get("url") or hn_url
            items.append({
                "title": hit.get("title"),
                "url": story_url,
                "source": domain(story_url) if hit.get("url") else "news.ycombinator.com",
                "summary": f"{hit.get('points') or 0} points, {hit.get('num_comments') or 0} comments on Hacker News",
                "hn_url": hn_url,
                "points": hit.get("points") or 0,
                "num_comments": hit.get("num_comments") or 0,
                "date": hit.get("created_at"),
            })
        return {
            "tool": "search_hackernews",
            "query": query,
            "sort_by": sort_by,
            "timeframe": timeframe,
            "items": items[:limit],
        }
    except Exception as exc:
        return err("search_hackernews", exc)
