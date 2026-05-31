from datetime import datetime
from radar.models import Item
from radar.digest import split_message, format_digest


def test_split_message_respects_limit():
    parts = split_message("a" * 50, limit=20)
    assert all(len(p) <= 20 for p in parts)
    assert "".join(parts) == "a" * 50


def test_format_digest_header_and_one_message_per_draft():
    drafts = [
        {"text": "Пост один", "alt_titles": ["А", "Б"]},
        {"text": "Пост два", "alt_titles": []},
    ]
    msgs = format_digest("2026-05-31", drafts, errors=["reddit недоступен"])
    assert len(msgs) == 3  # header + 2 drafts
    assert "2026-05-31" in msgs[0]
    assert "reddit недоступен" in msgs[0]
    assert "Пост один" in msgs[1]
    assert "Варианты заголовка" in msgs[1]
    assert "Пост два" in msgs[2]


def test_format_digest_fallback_lists_links():
    items = [Item("rss", "1", "Заголовок", "https://x", "", datetime(2026, 5, 31))]
    msgs = format_digest("2026-05-31", drafts=[], errors=[], fallback=items)
    joined = "\n".join(msgs)
    assert "https://x" in joined
    assert "Заголовок" in joined


def test_format_digest_includes_video_section():
    vids = [
        Item("youtube", "v1", "Сэм качает грудь", "https://yt/v1", "", datetime(2026, 5, 31))
    ]
    msgs = format_digest(
        "2026-05-31",
        drafts=[{"text": "пост", "alt_titles": []}],
        errors=[],
        videos=vids,
    )
    joined = "\n".join(msgs)
    assert "Видео-референс" in joined
    assert "https://yt/v1" in joined
    assert "Сэм качает грудь" in joined
