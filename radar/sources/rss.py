from datetime import datetime, timezone
from time import mktime

import feedparser

from radar.models import Item


def _date(entry) -> datetime:
    tp = getattr(entry, "published_parsed", None) or getattr(
        entry, "updated_parsed", None
    )
    if tp:
        return datetime.fromtimestamp(mktime(tp))
    return datetime.now(timezone.utc)


def parse_feed(parsed, feed_url: str) -> list[Item]:
    items: list[Item] = []
    for e in getattr(parsed, "entries", []):
        link = getattr(e, "link", "")
        sid = getattr(e, "id", "") or link
        items.append(
            Item(
                source="rss",
                source_id=sid,
                title=getattr(e, "title", "").strip(),
                url=link,
                text=getattr(e, "summary", "") or "",
                published_at=_date(e),
            )
        )
    return items


def fetch(cfg: dict, since_days: int) -> list[Item]:
    items: list[Item] = []
    for url in cfg.get("feeds", []):
        parsed = feedparser.parse(url)
        items.extend(parse_feed(parsed, url))
    return items
