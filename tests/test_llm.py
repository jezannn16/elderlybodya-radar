from datetime import datetime
from radar.models import Item
from radar.llm import Gemini


class FakeModels:
    def __init__(self, text):
        self._text = text

    def generate_content(self, model, contents):
        class R:
            text = self._text
        return R()


class FakeClient:
    def __init__(self, text):
        self.models = FakeModels(text)


def _items(*titles):
    return [
        Item("rss", str(i), t, "https://x", "b", datetime(2026, 5, 31))
        for i, t in enumerate(titles)
    ]


def test_rank_selects_items_by_id():
    g = Gemini("k", _client=FakeClient('[{"id": 1, "reason": "топ"}]'))
    out = g.rank(_items("a", "b"), n=1)
    assert len(out) == 1
    item, reason = out[0]
    assert item.title == "b"
    assert reason == "топ"


def test_draft_parses_json_with_fences():
    fenced = '```json\n{"text": "пост", "alt_titles": ["t1"]}\n```'
    g = Gemini("k", _client=FakeClient(fenced))
    d = g.draft(_items("a")[0], "style")
    assert d["text"] == "пост"
    assert d["alt_titles"] == ["t1"]
