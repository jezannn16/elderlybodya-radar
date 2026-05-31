from datetime import datetime, timedelta, timezone
from radar.models import Item
from radar.store import Store


def _item(sid):
    return Item("reddit", sid, "t", "u", "x", datetime(2026, 5, 31))


def test_unseen_then_seen_after_mark(tmp_path):
    s = Store(str(tmp_path / "s.sqlite"))
    it = _item("a1")
    assert s.is_seen(it) is False
    s.mark_seen([it])
    assert s.is_seen(it) is True
    s.close()


def test_prune_removes_old(tmp_path):
    s = Store(str(tmp_path / "s.sqlite"))
    it = _item("old")
    s.mark_seen([it])
    # backdate the row
    s.conn.execute(
        "UPDATE seen SET first_seen = ? WHERE key = ?",
        ((datetime.now(timezone.utc) - timedelta(days=90)).isoformat(), it.key),
    )
    s.conn.commit()
    s.prune(days=60)
    assert s.is_seen(it) is False
    s.close()
