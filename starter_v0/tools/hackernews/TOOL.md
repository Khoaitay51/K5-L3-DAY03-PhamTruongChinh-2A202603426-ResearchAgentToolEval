---
name: hackernews
track: bonus
kind: live_api
provider: Hacker News Algolia API (no key)
requires_env: []
inputs: [query, sort_by, timeframe, limit]
outputs: [items]
side_effect: false
---
# hackernews

Searches Hacker News stories via the public Algolia API
(`https://hn.algolia.com/api/v1/search` or `/search_by_date`). No API key.

- `sort_by`: `relevance` (default) or `date` (newest first).
- `timeframe`: `day | week | month | year | all` -> `numericFilters=created_at_i>...`.
- `limit` is clamped to 1..20; string numbers like `"5"` are accepted.
- Unknown `sort_by` / `timeframe` values fall back to the defaults instead of crashing.
- Empty `query` returns an error dict without calling the network.

Each item: `title`, `url` (original link, or HN discussion if the story has no link),
`source`, `summary` (points + comments), `hn_url`, `points`, `num_comments`, `date`.

Team-added tool (Day 03 lab).
