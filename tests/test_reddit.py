from radar.sources.reddit import parse_listing


def test_parse_listing_builds_items():
    data = {
        "data": {
            "children": [
                {
                    "data": {
                        "id": "t3abc",
                        "title": "My bench stalled, help",
                        "selftext": "Been stuck at 100kg...",
                        "permalink": "/r/powerlifting/comments/t3abc/x/",
                        "created_utc": 1769800000,
                    }
                }
            ]
        }
    }
    items = parse_listing(data, "powerlifting")
    assert len(items) == 1
    it = items[0]
    assert it.source == "reddit"
    assert it.source_id == "t3abc"
    assert it.url == "https://www.reddit.com/r/powerlifting/comments/t3abc/x/"
    assert "100kg" in it.text
