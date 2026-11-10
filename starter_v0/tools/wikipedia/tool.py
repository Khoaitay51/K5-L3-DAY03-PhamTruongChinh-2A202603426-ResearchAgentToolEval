from __future__ import annotations

from typing import Any

import requests

from tools._shared import TIMEOUT, clamp_int, err, pick


USER_AGENT = "AI20k-Day03-Research-Agent/1.0 (educational lab)"


def wikipedia_summary(query: str = "", lang: str = "en", max_chars: int = 1500) -> dict[str, Any]:
    try:
        query = (query or "").strip() if isinstance(query, str) else ""
        if not query:
            raise ValueError("query must be a non-empty string")
        lang = pick(lang, ("en", "vi"), "en")
        max_chars = clamp_int(max_chars, default=1500, low=200, high=5000)

        # One request: search for the best-matching page and return its intro as plain text.
        response = requests.get(
            f"https://{lang}.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "format": "json",
                "formatversion": 2,
                "generator": "search",
                "gsrsearch": query,
                "gsrlimit": 1,
                "prop": "extracts|info",
                "exintro": 1,
                "explaintext": 1,
                "inprop": "url",
                "redirects": 1,
            },
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        pages = (response.json().get("query") or {}).get("pages") or []
        if isinstance(pages, dict):  # formatversion=1 shape
            pages = list(pages.values())
        pages = [page for page in pages if not page.get("missing")]
        if not pages:
            return {"tool": "wikipedia_summary", "query": query, "lang": lang, "items": [], "message": "no_match"}

        page = sorted(pages, key=lambda item: item.get("index", 0))[0]
        extract = (page.get("extract") or "").strip()
        if len(extract) > max_chars:
            extract = extract[: max_chars - 3] + "..."
        url = page.get("fullurl") or f"https://{lang}.wikipedia.org/wiki/{page.get('title', '').replace(' ', '_')}"
        return {"tool": "wikipedia_summary", "query": query, "lang": lang, "items": [{
            "title": page.get("title"),
            "url": url,
            "source": f"{lang}.wikipedia.org",
            "summary": extract,
        }]}
    except Exception as exc:
        return err("wikipedia_summary", exc)
