"""TODO(student): Tool Unit Test Challenge.

Each test below is a stub. Replace `pytest.skip(...)` with a real test.
Patterns to copy are in test_tools_examples.py. Fixtures are in conftest.py.

Rules:
- Offline only: mock HTTP with `fake_http`, set fake keys with `monkeypatch.setenv`.
- One behaviour per test. Name the test after the behaviour, not the function.
- Done = `pytest tests/ -v` shows 0 skipped, 0 failed.
"""
from __future__ import annotations

import pytest

from conftest import FakeResponse  # noqa: F401  (you will need it)
from tools import TOOL_FUNCTIONS  # noqa: F401

TODO = "TODO(student): implement this test"


# ---------------- clarify ----------------

def test_clarify_choice_returns_options_and_awaits_user() -> None:
    options = ["Sam Altman", "Elon Musk"]
    result = TOOL_FUNCTIONS["clarify"](question="Bạn muốn xem tài khoản nào?", response_type="choice", options=options)

    assert result["options"] == ["Sam Altman", "Elon Musk"]
    assert result["response_type"] == "choice"
    assert result["question"] == "Bạn muốn xem tài khoản nào?"
    assert result["awaiting_user"] is True


# ---------------- format ----------------

def test_format_sections_groups_items_by_section() -> None:
    items = [
        {"title": "a1", "url": "https://a.com/1", "section": "A"},
        {"title": "b1", "url": "https://b.com/1", "section": "B"},
        {"title": "a2", "url": "https://a.com/2", "section": "A"},
    ]
    markdown = TOOL_FUNCTIONS["format"](items=items, template="sections")["markdown"]

    lines = markdown.splitlines()
    assert lines.count("## A") == 1
    assert lines.count("## B") == 1
    # both A items sit under the single "## A" header, before "## B"
    assert markdown.index("a1") < markdown.index("a2") < markdown.index("## B")


def test_format_thread_numbers_items() -> None:
    items = [{"title": f"tweet {i}", "url": f"https://x.com/u/status/{i}"} for i in range(3)]
    markdown = TOOL_FUNCTIONS["format"](items=items, template="thread")["markdown"]

    posts = markdown.split("\n\n")
    assert [post.split(" ", 1)[0] for post in posts] == ["1/", "2/", "3/"]
    assert posts[0].startswith("1/ tweet 0")


def test_format_empty_items_does_not_crash() -> None:
    for empty in (None, []):
        for template in ("brief", "sections", "bullets", "thread", "daily_ai_vn"):
            result = TOOL_FUNCTIONS["format"](items=empty, template=template)
            assert result["item_count"] == 0
            assert isinstance(result["markdown"], str)


# ---------------- send (guardrail) ----------------

def test_send_confirmed_posts_to_telegram(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "-1001")
    calls = fake_http(FakeResponse({"ok": True}))

    result = TOOL_FUNCTIONS["send"](text="Bản tin AI", confirmed=True)

    assert len(calls) == 1
    assert calls[0]["method"] == "POST"
    assert "123:abc" in calls[0]["url"]
    assert calls[0]["url"].endswith("/sendMessage")
    assert calls[0]["json"]["chat_id"] == "-1001"
    assert calls[0]["json"]["text"] == "Bản tin AI"
    assert result["status"] == "sent"


def test_send_confirmed_without_env_returns_error_and_no_request(fake_http) -> None:
    calls = fake_http(FakeResponse({"ok": True}))

    result = TOOL_FUNCTIONS["send"](text="Bản tin AI", confirmed=True)

    assert calls == []
    assert result["status"] == "error"
    assert result["error"] == "ConfigurationError"
    assert "TELEGRAM_BOT_TOKEN" in result["message"]


# ---------------- lookup ----------------

def test_lookup_without_timeframe_omits_time_range(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    calls = fake_http(FakeResponse({"results": []}))

    result = TOOL_FUNCTIONS["lookup"](query="OpenAI", timeframe=None)

    assert "time_range" not in calls[0]["json"]
    assert calls[0]["json"]["query"] == "OpenAI"
    assert result["timeframe"] is None
    assert result["items"] == []


# ---------------- fetch ----------------

def test_fetch_maps_firecrawl_response(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-test")
    calls = fake_http(FakeResponse({"data": {
        "markdown": "# Hello\nbody",
        "metadata": {"title": "T", "sourceURL": "https://www.example.com/post"},
    }}))

    result = TOOL_FUNCTIONS["fetch"](url="https://www.example.com/post")

    assert calls[0]["url"] == "https://api.firecrawl.dev/v1/scrape"
    assert calls[0]["json"]["url"] == "https://www.example.com/post"
    assert calls[0]["headers"]["Authorization"] == "Bearer fc-test"
    assert result["items"][0] == {
        "title": "T",
        "url": "https://www.example.com/post",
        "source": "example.com",
        "summary": "# Hello\nbody",
    }


def test_fetch_truncates_markdown_to_4000_chars(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-test")
    fake_http(FakeResponse({"data": {"markdown": "y" * 10_000, "metadata": {}}}))

    item = TOOL_FUNCTIONS["fetch"](url="https://example.com/long")["items"][0]

    assert len(item["summary"]) == 4000
    # metadata missing -> falls back to the requested url
    assert item["title"] == "https://example.com/long"
    assert item["url"] == "https://example.com/long"


# ---------------- timeline / social_search ----------------

def test_timeline_respects_limit_and_skips_items_without_id(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("RAPIDAPI_KEY", "rapid-test")
    raw = [{"text": "no id", "screen_name": "sama"}] + [
        {"tweet_id": str(100 + i), "text": f"tweet {i}", "screen_name": "sama"} for i in range(6)
    ]
    calls = fake_http(FakeResponse({"timeline": raw}))

    result = TOOL_FUNCTIONS["timeline"](screenname="sama", limit=3)

    assert calls[0]["params"] == {"screenname": "sama"}
    assert calls[0]["headers"]["x-rapidapi-key"] == "rapid-test"
    assert len(result["items"]) == 3
    assert [item["url"] for item in result["items"]] == [
        "https://x.com/sama/status/100",
        "https://x.com/sama/status/101",
        "https://x.com/sama/status/102",
    ]


def test_social_search_passes_search_type(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("RAPIDAPI_KEY", "rapid-test")
    calls = fake_http(FakeResponse({"timeline": []}))

    for search_type in ("Top", "Latest"):
        result = TOOL_FUNCTIONS["social_search"](query="OpenAI", search_type=search_type)
        assert result["search_type"] == search_type

    assert calls[0]["url"].endswith("/search.php")
    assert calls[0]["params"] == {"query": "OpenAI", "search_type": "Top"}
    assert calls[1]["params"] == {"query": "OpenAI", "search_type": "Latest"}


# ---------------- policy (local knowledge + trust boundary) ----------------

def test_policy_empty_query_returns_no_results() -> None:
    for query in ("", "   ", "?!"):
        assert TOOL_FUNCTIONS["policy"](query=query)["results"] == []


def test_policy_area_filter_only_returns_that_area() -> None:
    result = TOOL_FUNCTIONS["policy"](query="API key transcript confidential", policy_area="data_privacy", top_k=5)

    assert result["results"], "expected at least one data_privacy hit"
    assert all(hit["policy_area"] == "data_privacy" for hit in result["results"])


def test_policy_instruction_like_lines_go_to_untrusted_text() -> None:
    result = TOOL_FUNCTIONS["policy"](query="injection probe citation", policy_area="source_citation", top_k=5)

    probe = [hit for hit in result["results"] if hit["section"] == "Injection probe"]
    assert probe, "expected the Injection probe section to be retrieved"
    hit = probe[0]
    assert any("viral tweet" in line for line in hit["untrusted_text"])
    assert "viral tweet" not in hit["facts"]
    assert "trust_boundary" in result


# ---------------- YOUR NEW TOOL(S) ----------------
# Write at least 3 tests per tool your team adds:
#   1. happy path (mocked if it calls an API)
#   2. bad / missing input from the model (empty string, wrong type, out-of-enum value)
#   3. failure path (missing key, HTTP error, timeout) -> returns error dict, does not raise

import requests  # noqa: E402

hackernews = TOOL_FUNCTIONS["hackernews"]
github_repos = TOOL_FUNCTIONS["github_repos"]
wikipedia = TOOL_FUNCTIONS["wikipedia"]
hf_models = TOOL_FUNCTIONS["hf_models"]


# ---- hackernews ----

def test_hackernews_maps_hits_and_sends_story_filter(fake_http) -> None:
    calls = fake_http(FakeResponse({"hits": [
        {"objectID": "1", "title": "Show HN: agent eval", "url": "https://www.example.com/a", "points": 120,
         "num_comments": 45, "created_at": "2026-11-10T00:00:00Z"},
        {"objectID": "2", "title": "Ask HN: no link", "url": None, "points": 3, "num_comments": 1},
        {"objectID": "3", "title": None},  # junk hit without title -> skipped
    ]}))

    result = hackernews(query="agent eval", limit=5)

    assert calls[0]["url"] == "https://hn.algolia.com/api/v1/search"
    assert calls[0]["params"]["query"] == "agent eval"
    assert calls[0]["params"]["tags"] == "story"
    assert calls[0]["params"]["hitsPerPage"] == 5
    assert "numericFilters" not in calls[0]["params"]
    assert [item["title"] for item in result["items"]] == ["Show HN: agent eval", "Ask HN: no link"]
    assert result["items"][0]["source"] == "example.com"
    assert result["items"][0]["points"] == 120
    # story without its own link points to the HN discussion
    assert result["items"][1]["url"] == "https://news.ycombinator.com/item?id=2"


def test_hackernews_date_sort_and_timeframe_build_request(fake_http) -> None:
    calls = fake_http(FakeResponse({"hits": []}))

    result = hackernews(query="LLM", sort_by="date", timeframe="week", limit="3")

    assert calls[0]["url"] == "https://hn.algolia.com/api/v1/search_by_date"
    assert calls[0]["params"]["numericFilters"].startswith("created_at_i>")
    assert calls[0]["params"]["hitsPerPage"] == 3  # string "3" coerced to int
    assert result["timeframe"] == "week"


def test_hackernews_bad_input_from_model(fake_http) -> None:
    calls = fake_http(FakeResponse({"hits": []}))

    # empty / non-string query -> error dict, no network
    assert hackernews(query="")["error"] == "ValueError"
    assert hackernews(query=None)["error"] == "ValueError"
    assert calls == []

    # out-of-enum values and absurd limit fall back / clamp instead of crashing
    result = hackernews(query="AI", sort_by="popular", timeframe="decade", limit=0)
    assert result["sort_by"] == "relevance"
    assert result["timeframe"] == "all"
    assert calls[-1]["params"]["hitsPerPage"] == 1
    hackernews(query="AI", limit=500)
    assert calls[-1]["params"]["hitsPerPage"] == 20


def test_hackernews_http_error_returns_error_dict(fake_http) -> None:
    fake_http(FakeResponse(status_code=503))
    result = hackernews(query="AI")
    assert result["error"] == "HTTPError"
    assert result["tool"] == "search_hackernews"


def test_hackernews_timeout_returns_error_dict(fake_http) -> None:
    fake_http(requests.Timeout("read timed out"))
    assert hackernews(query="AI")["error"] == "Timeout"


# ---- github_repos ----

def test_github_repos_builds_query_and_maps_items(fake_http) -> None:
    calls = fake_http(FakeResponse({"total_count": 2, "items": [
        {"full_name": "langchain-ai/langgraph", "html_url": "https://github.com/langchain-ai/langgraph",
         "description": "Build agents", "stargazers_count": 9000, "language": "Python", "pushed_at": "2026-11-01"},
        {"full_name": None},  # malformed -> skipped
    ]}))

    result = github_repos(query="agent framework", language="python", limit=5)

    assert calls[0]["url"] == "https://api.github.com/search/repositories"
    assert calls[0]["params"]["q"] == "agent framework language:python"
    assert calls[0]["params"]["sort"] == "stars"
    assert calls[0]["params"]["per_page"] == 5
    assert "Authorization" not in calls[0]["headers"]
    assert result["items"] == [{
        "title": "langchain-ai/langgraph", "url": "https://github.com/langchain-ai/langgraph",
        "source": "github.com", "summary": "Build agents", "stars": 9000, "language": "Python",
        "updated": "2026-11-01",
    }]


def test_github_repos_uses_token_and_best_match_has_no_sort(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
    calls = fake_http(FakeResponse({"items": []}))

    github_repos(query="rag", sort_by="best_match")

    assert calls[0]["headers"]["Authorization"] == "Bearer ghp_test"
    assert "sort" not in calls[0]["params"]
    assert calls[0]["params"]["q"] == "rag"


def test_github_repos_bad_input_from_model(fake_http) -> None:
    calls = fake_http(FakeResponse({"items": []}))

    assert github_repos(query="   ")["error"] == "ValueError"
    assert github_repos(query=123)["error"] == "ValueError"
    assert calls == []

    result = github_repos(query="rag", sort_by="forks", limit="abc", language=None)
    assert result["sort_by"] == "stars"
    assert calls[-1]["params"]["per_page"] == 5  # unparsable limit -> default
    assert calls[-1]["params"]["q"] == "rag"


def test_github_repos_rate_limit_returns_error_dict(fake_http) -> None:
    fake_http(FakeResponse(status_code=403))
    result = github_repos(query="rag")
    assert result["error"] == "HTTPError"
    assert result["tool"] == "search_github_repos"


# ---- wikipedia ----

def test_wikipedia_returns_best_page_intro(fake_http) -> None:
    calls = fake_http(FakeResponse({"query": {"pages": [
        {"title": "Retrieval-augmented generation", "index": 1,
         "extract": "RAG is a technique...", "fullurl": "https://en.wikipedia.org/wiki/Retrieval-augmented_generation"},
        {"title": "Other", "index": 2, "extract": "x", "fullurl": "https://en.wikipedia.org/wiki/Other"},
    ]}}))

    result = wikipedia(query="RAG là gì", lang="en")

    assert calls[0]["url"] == "https://en.wikipedia.org/w/api.php"
    assert calls[0]["params"]["gsrsearch"] == "RAG là gì"
    assert calls[0]["params"]["explaintext"] == 1
    assert "User-Agent" in calls[0]["headers"]
    assert result["items"] == [{
        "title": "Retrieval-augmented generation",
        "url": "https://en.wikipedia.org/wiki/Retrieval-augmented_generation",
        "source": "en.wikipedia.org",
        "summary": "RAG is a technique...",
    }]


def test_wikipedia_truncates_and_handles_no_match(fake_http) -> None:
    fake_http(FakeResponse({"query": {"pages": [{"title": "Long", "index": 1, "extract": "z" * 9000}]}}))
    item = wikipedia(query="long", max_chars=300)["items"][0]
    assert len(item["summary"]) == 300 and item["summary"].endswith("...")
    assert item["url"] == "https://en.wikipedia.org/wiki/Long"

    fake_http(FakeResponse({"batchcomplete": True}))  # no "query" key = no match
    result = wikipedia(query="asdkjhqwe")
    assert result["items"] == [] and result["message"] == "no_match"
    assert "error" not in result


def test_wikipedia_bad_input_from_model(fake_http) -> None:
    calls = fake_http(FakeResponse({"query": {"pages": []}}))

    assert wikipedia(query="")["error"] == "ValueError"
    assert calls == []

    result = wikipedia(query="Transformer", lang="fr", max_chars=-5)
    assert result["lang"] == "en"
    assert calls[-1]["url"].startswith("https://en.wikipedia.org")


def test_wikipedia_network_error_returns_error_dict(fake_http) -> None:
    fake_http(requests.ConnectionError("dns failure"))
    assert wikipedia(query="Transformer")["error"] == "ConnectionError"


# ---- hf_models ----

def test_hf_models_maps_models_and_sends_filters(fake_http) -> None:
    calls = fake_http(FakeResponse([
        {"id": "Qwen/Qwen2.5-7B-Instruct", "pipeline_tag": "text-generation", "downloads": 1000, "likes": 50,
         "lastModified": "2026-10-01"},
        {"modelId": None},  # malformed -> skipped
    ]))

    result = hf_models(query="qwen", task="text-generation", limit=5)

    assert calls[0]["url"] == "https://huggingface.co/api/models"
    assert calls[0]["params"] == {"sort": "downloads", "direction": -1, "limit": 5,
                                  "search": "qwen", "pipeline_tag": "text-generation"}
    assert result["items"] == [{
        "title": "Qwen/Qwen2.5-7B-Instruct", "url": "https://huggingface.co/Qwen/Qwen2.5-7B-Instruct",
        "source": "huggingface.co", "summary": "text-generation; 1000 downloads, 50 likes",
        "task": "text-generation", "downloads": 1000, "likes": 50, "updated": "2026-10-01",
    }]


def test_hf_models_bad_input_from_model(fake_http) -> None:
    calls = fake_http(FakeResponse([]))

    assert hf_models(query="", task="")["error"] == "ValueError"
    assert calls == []

    result = hf_models(task="automatic-speech-recognition", sort_by="stars", limit=99)
    assert result["sort_by"] == "downloads"
    assert calls[-1]["params"]["limit"] == 20
    assert "search" not in calls[-1]["params"]


def test_hf_models_unexpected_payload_returns_error_dict(fake_http) -> None:
    fake_http(FakeResponse({"error": "Invalid"}))
    result = hf_models(query="qwen")
    assert result["error"] == "ValueError"
    assert result["tool"] == "search_hf_models"

    fake_http(FakeResponse(status_code=429))
    assert hf_models(query="qwen")["error"] == "HTTPError"
