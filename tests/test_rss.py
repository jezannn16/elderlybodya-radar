import time
from types import SimpleNamespace
from radar.sources.rss import parse_feed


def test_parse_feed_builds_items():
    entry = SimpleNamespace(
        id="https://sbs.com/post1",
        title="How to bench more",
        summary="Technique tips for the bench press.",
        link="https://sbs.com/post1",
        published_parsed=time.struct_time((2026, 5, 30, 12, 0, 0, 0, 0, 0)),
    )
    parsed = SimpleNamespace(entries=[entry])
    items = parse_feed(parsed, "https://sbs.com/feed")
    assert len(items) == 1
    it = items[0]
    assert it.source == "rss"
    assert it.source_id == "https://sbs.com/post1"
    assert it.url == "https://sbs.com/post1"
    assert "bench" in it.text.lower()
