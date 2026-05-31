from datetime import datetime
from radar.models import Item
from radar.writer import build_rank_prompt, build_draft_prompt, STYLE_GUIDE


def _item(t):
    return Item("rss", "1", t, "https://x", "body text", datetime(2026, 5, 31))


def test_rank_prompt_enumerates_candidates_and_asks_n():
    p = build_rank_prompt([_item("Жим лёжа"), _item("Присед")], n=1)
    assert "0" in p and "Жим лёжа" in p and "Присед" in p
    assert "1" in p  # the requested count appears
    assert "JSON" in p


def test_draft_prompt_includes_item_and_style():
    p = build_draft_prompt(_item("Жим лёжа"), STYLE_GUIDE)
    assert "Жим лёжа" in p
    assert "https://x" in p
    assert "Telegram" in p  # style guide text present
