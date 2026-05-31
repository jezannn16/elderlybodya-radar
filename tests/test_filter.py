from datetime import datetime
from radar.models import Item
from radar.filter import filter_items, matches_keywords


class FakeStore:
    def __init__(self, seen_keys):
        self.seen_keys = set(seen_keys)

    def is_seen(self, item):
        return item.key in self.seen_keys


def _item(sid, title):
    return Item("rss", sid, title, "u", "", datetime(2026, 5, 31))


def test_matches_keywords_case_insensitive():
    it = _item("1", "Новый присед программа")
    assert matches_keywords(it, ["присед"]) is True
    assert matches_keywords(it, ["плавание"]) is False


def test_filter_drops_seen_offtopic_and_dupes():
    items = [
        _item("a", "Жим лёжа разбор"),     # keep
        _item("b", "Рецепт борща"),         # off-topic
        _item("c", "Жим лёжа разбор"),      # seen
        _item("a", "Жим лёжа разбор"),      # duplicate key of first
    ]
    store = FakeStore(seen_keys={"rss:c"})  # c already seen
    out = filter_items(items, ["жим"], store)
    keys = [i.key for i in out]
    assert keys == ["rss:a"]
