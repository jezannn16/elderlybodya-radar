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


def test_draft_prompt_includes_item_style_and_examples():
    p = build_draft_prompt(_item("Жим лёжа"), STYLE_GUIDE, examples=["мой шортс про жим"])
    assert "Жим лёжа" in p
    assert "degen" in p.lower()  # style guide present
    assert "мой шортс про жим" in p  # voice examples injected


def test_draft_prompt_without_examples_omits_section():
    p = build_draft_prompt(_item("Присед"), STYLE_GUIDE)
    assert "НАШЕГО канала" not in p
