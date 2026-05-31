import os
from datetime import datetime, timedelta, timezone

import requests

from radar.models import Item

API = "https://www.googleapis.com/youtube/v3"


def _date(s: str) -> datetime:
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, TypeError):
        return datetime.now(timezone.utc)


def parse_search(data: dict) -> list[Item]:
    items: list[Item] = []
    for row in data.get("items", []):
        vid = row.get("id", {}).get("videoId")
        if not vid:
            continue
        sn = row.get("snippet", {})
        items.append(
            Item(
                source="youtube",
                source_id=vid,
                title=sn.get("title", "").strip(),
                url=f"https://www.youtube.com/watch?v={vid}",
                text=sn.get("description", "") or "",
                published_at=_date(sn.get("publishedAt", "")),
            )
        )
    return items


def _resolve_channel_id(handle: str, api_key: str) -> str | None:
    h = handle.lstrip("@")
    resp = requests.get(
        f"{API}/channels",
        params={"part": "id", "forHandle": h, "key": api_key},
        timeout=30,
    )
    rows = resp.json().get("items", [])
    return rows[0]["id"] if rows else None


def fetch(cfg: dict, since_days: int) -> list[Item]:
    api_key = os.environ["YOUTUBE_API_KEY"]
    after = (
        datetime.now(timezone.utc) - timedelta(days=since_days)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    items: list[Item] = []
    for handle in cfg.get("channels", []):
        cid = _resolve_channel_id(handle, api_key)
        if not cid:
            continue
        resp = requests.get(
            f"{API}/search",
            params={
                "part": "snippet",
                "channelId": cid,
                "order": "date",
                "type": "video",
                "publishedAfter": after,
                "maxResults": cfg.get("max_results", 5),
                "key": api_key,
            },
            timeout=30,
        )
        items.extend(parse_search(resp.json()))
    return items
