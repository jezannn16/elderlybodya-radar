from datetime import datetime
from radar.models import Item
from radar.llm import LLM


class FakeResp:
    def __init__(self, content):
        self._content = content

    def raise_for_status(self):
        pass

    def json(self):
        return {"choices": [{"message": {"content": self._content}}]}


class FakePoster:
    def __init__(self, content):
        self.content = content
        self.calls = []

    def __call__(self, url, headers, json, timeout):
        self.calls.append((url, headers, json))
        return FakeResp(self.content)


def _items(*titles):
    return [
        Item("rss", str(i), t, "https://x", "b", datetime(2026, 5, 31))
        for i, t in enumerate(titles)
    ]


def test_rank_selects_items_by_id():
    g = LLM("k", poster=FakePoster('[{"id": 1, "reason": "топ"}]'))
    out = g.rank(_items("a", "b"), n=1)
    assert len(out) == 1
    item, reason = out[0]
    assert item.title == "b"
    assert reason == "топ"


def test_draft_parses_json_with_fences():
    fenced = '```json\n{"text": "пост", "alt_titles": ["t1"]}\n```'
    g = LLM("k", poster=FakePoster(fenced))
    d = g.draft(_items("a")[0], "style")
    assert d["text"] == "пост"
    assert d["alt_titles"] == ["t1"]


def test_generate_sends_bearer_and_model():
    poster = FakePoster("[]")
    g = LLM("secret", model="llama-3.3-70b-versatile", poster=poster)
    g.rank(_items("a"), n=1)
    url, headers, payload = poster.calls[0]
    assert headers["Authorization"] == "Bearer secret"
    assert payload["model"] == "llama-3.3-70b-versatile"
