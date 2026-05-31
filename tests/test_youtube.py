from radar.sources.youtube import parse_search


def test_parse_search_builds_items():
    data = {
        "items": [
            {
                "id": {"kind": "youtube#video", "videoId": "vid123"},
                "snippet": {
                    "title": "Full bench day",
                    "description": "Programming a bench session.",
                    "publishedAt": "2026-05-29T10:00:00Z",
                },
            }
        ]
    }
    items = parse_search(data)
    assert len(items) == 1
    it = items[0]
    assert it.source == "youtube"
    assert it.source_id == "vid123"
    assert it.url == "https://www.youtube.com/watch?v=vid123"
    assert "bench" in it.text.lower()
