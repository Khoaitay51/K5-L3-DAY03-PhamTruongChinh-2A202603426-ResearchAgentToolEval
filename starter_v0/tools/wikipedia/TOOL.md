---
name: wikipedia
track: bonus
kind: live_api
provider: Wikipedia MediaWiki Action API (no key)
requires_env: []
inputs: [query, lang, max_chars]
outputs: [items]
side_effect: false
---
# wikipedia

Finds the best-matching Wikipedia article for `query` and returns its intro as
plain text, in one request (`generator=search` + `prop=extracts`). No API key.

- `lang`: `en` (default) or `vi`; anything else falls back to `en`.
- `max_chars` is clamped to 200..5000; longer intros are cut with `...`.
- No match -> `items: []` with `message: "no_match"` (not an error).
- Empty `query` returns an error dict without calling the network.

Use for stable background knowledge (definitions, who/what is X), not for news.

Team-added tool (Day 03 lab).
