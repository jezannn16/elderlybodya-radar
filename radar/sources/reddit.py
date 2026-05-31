from datetime import datetime, timezone

import requests

from radar.models import Item

API = "https://www.reddit.com"
_UA = {"User-Agent": "elderlybodya-radar/1.0 (by /u/elderlybodya)"}


def parse_listing(data: dict, subreddit: str) -> list[Item]:
    items: list[Item] = []
    for child in data.get("data", {}).get("children", []):
        d = child.get("data", {})
        items.append(
            Item(
                source="reddit",
                source_id=d.get("id", ""),
                title=d.get("title", "").strip(),
                url="https://www.reddit.com" + d.get("permalink", ""),
                text=d.get("selftext", "") or "",
                published_at=datetime.fromtimestamp(
                    d.get("created_utc", 0), timezone.utc
                ),
            )
        )
    return items


def fetch(cfg: dict, since_days: int) -> list[Item]:
    """Keyless: hit Reddit's public .json endpoints with a descriptive User-Agent."""
    listing = cfg.get("listing", "top")
    items: list[Item] = []
    for sub in cfg.get("subreddits", []):
        resp = requests.get(
            f"{API}/r/{sub}/{listing}.json",
            headers=_UA,
            params={"t": cfg.get("time", "day"), "limit": cfg.get("limit", 25)},
            timeout=30,
        )
        resp.raise_for_status()
        items.extend(parse_listing(resp.json(), sub))
    return items
