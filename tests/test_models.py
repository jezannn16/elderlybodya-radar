from datetime import datetime
from radar.models import Item


def test_item_key_combines_source_and_id():
    it = Item(
        source="reddit",
        source_id="abc123",
        title="Bench tips",
        url="https://r/x",
        text="body",
        published_at=datetime(2026, 5, 31, 6, 0),
    )
    assert it.key == "reddit:abc123"
