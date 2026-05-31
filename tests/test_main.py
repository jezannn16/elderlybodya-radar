from datetime import datetime
from radar.models import Item
from radar import main as m


def _item(sid, title):
    return Item("rss", sid, title, "https://x", "жим body", datetime(2026, 5, 31))


def test_run_collects_filters_drafts_and_sends(tmp_path, monkeypatch):
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        "drafts_per_day: 1\n"
        "keywords:\n  ru: [жим]\n  en: []\n"
        "state_path: " + str(tmp_path / "seen.sqlite").replace("\\", "/") + "\n"
        "sources:\n  rss:\n    enabled: true\n    feeds: [https://x/feed]\n",
        encoding="utf-8",
    )

    # one fake source returning two on-topic items
    monkeypatch.setattr(
        m, "SOURCES", {"rss": lambda cfg, since: [_item("a", "Жим 1"), _item("b", "Жим 2")]}
    )

    class FakeLLM:
        def __init__(self, *a, **k):
            pass

        def rank(self, candidates, n):
            return [(candidates[0], "топ")]

        def draft(self, item, style_guide=None, examples=None):
            return {"text": f"пост про {item.title}", "alt_titles": []}

    monkeypatch.setattr(m, "LLM", FakeLLM)

    sent = {}
    monkeypatch.setattr(
        m, "send_messages", lambda messages, token, chat_id, **k: sent.update(msgs=messages)
    )
    monkeypatch.setenv("GROQ_API_KEY", "k")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")

    code = m.run(str(cfg_path), dry_run=False)
    assert code == 0
    assert any("пост про Жим 1" in msg for msg in sent["msgs"])
