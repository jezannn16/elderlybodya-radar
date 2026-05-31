import re
from datetime import datetime, timezone
from time import mktime

import feedparser
import requests

from radar.models import Item

FEED = "https://www.youtube.com/feeds/videos.xml?channel_id={cid}"
_UA = {"User-Agent": "Mozilla/5.0 (compatible; elderlybodya-radar/1.0)"}
_CID_RE = re.compile(r'"(?:channelId|externalId)":"(UC[0-9A-Za-z_-]{22})"')


def _date(entry) -> datetime:
    tp = getattr(entry, "published_parsed", None) or getattr(
        entry, "updated_parsed", None
    )
    if tp:
        return datetime.fromtimestamp(mktime(tp), timezone.utc)
    return datetime.now(timezone.utc)


def resolve_channel_id(handle: str) -> str | None:
    """Resolve a @handle / URL / UC-id to a channelId by scraping the page (keyless)."""
    h = handle.strip()
    if h.startswith("UC") and len(h) == 24:
        return h
    if h.startswith("http"):
        url = h
    elif h.startswith("@"):
        url = f"https://www.youtube.com/{h}"
    else:
        url = f"https://www.youtube.com/@{h}"
    try:
        html = requests.get(url, headers=_UA, timeout=30).text
    except Exception:  # noqa: BLE001
        return None
    m = _CID_RE.search(html)
    return m.group(1) if m else None


def parse_feed(parsed) -> list[Item]:
    items: list[Item] = []
    for e in getattr(parsed, "entries", []):
        vid = getattr(e, "yt_videoid", None) or getattr(e, "id", "")
        items.append(
            Item(
                source="youtube",
                source_id=vid,
                title=getattr(e, "title", "").strip(),
                url=getattr(e, "link", ""),
                text=getattr(e, "summary", "") or "",
                published_at=_date(e),
            )
        )
    return items


def fetch(cfg: dict, since_days: int) -> list[Item]:
    items: list[Item] = []
    for handle in cfg.get("channels", []):
        cid = resolve_channel_id(handle)
        if not cid:
            continue
        parsed = feedparser.parse(FEED.format(cid=cid))
        items.extend(parse_feed(parsed))
    return items


def channel_titles(handle: str, limit: int = 12) -> list[str]:
    """Recent video titles of a channel — used as voice examples for the writer."""
    cid = resolve_channel_id(handle)
    if not cid:
        return []
    parsed = feedparser.parse(FEED.format(cid=cid))
    return [
        getattr(e, "title", "").strip()
        for e in getattr(parsed, "entries", [])[:limit]
        if getattr(e, "title", "").strip()
    ]
