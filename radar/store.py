import os
import sqlite3
from datetime import datetime, timedelta
from typing import Iterable

from radar.models import Item


class Store:
    def __init__(self, path: str):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.conn = sqlite3.connect(path)
        self._init()

    def _init(self) -> None:
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS seen ("
            "key TEXT PRIMARY KEY, first_seen TEXT NOT NULL)"
        )
        self.conn.commit()

    def is_seen(self, item: Item) -> bool:
        cur = self.conn.execute("SELECT 1 FROM seen WHERE key = ?", (item.key,))
        return cur.fetchone() is not None

    def mark_seen(self, items: Iterable[Item]) -> None:
        now = datetime.utcnow().isoformat()
        self.conn.executemany(
            "INSERT OR IGNORE INTO seen (key, first_seen) VALUES (?, ?)",
            [(it.key, now) for it in items],
        )
        self.conn.commit()

    def prune(self, days: int) -> None:
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        self.conn.execute("DELETE FROM seen WHERE first_seen < ?", (cutoff,))
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
