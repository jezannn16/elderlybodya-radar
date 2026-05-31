import time
from types import SimpleNamespace
from radar.sources.youtube import parse_feed


def test_parse_feed_builds_items():
    e = SimpleNamespace(
        yt_videoid="vid123",
        title="POV: leg day after 2 years natty",
        link="https://www.youtube.com/watch?v=vid123",
        summary="degen leg day",
        published_parsed=time.struct_time((2026, 5, 30, 12, 0, 0, 0, 0, 0)),
    )
    parsed = SimpleNamespace(entries=[e])
    items = parse_feed(parsed)
    assert len(items) == 1
    it = items[0]
    assert it.source == "youtube"
    assert it.source_id == "vid123"
    assert it.url == "https://www.youtube.com/watch?v=vid123"
    assert "leg day" in it.title.lower()
