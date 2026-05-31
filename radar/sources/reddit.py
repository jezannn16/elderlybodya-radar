import os
from datetime import datetime, timezone

import requests

from radar.models import Item

TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
API = "https://oauth.reddit.com"


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


def _token(user_agent: str) -> str:
    auth = requests.auth.HTTPBasicAuth(
        os.environ["REDDIT_CLIENT_ID"], os.environ["REDDIT_CLIENT_SECRET"]
    )
    resp = requests.post(
        TOKEN_URL,
        auth=auth,
        data={"grant_type": "client_credentials"},
        headers={"User-Agent": user_agent},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def fetch(cfg: dict, since_days: int) -> list[Item]:
    ua = os.environ.get("REDDIT_USER_AGENT", "elderlybodya-radar/1.0")
    token = _token(ua)
    headers = {"Authorization": f"bearer {token}", "User-Agent": ua}
    items: list[Item] = []
    for sub in cfg.get("subreddits", []):
        resp = requests.get(
            f"{API}/r/{sub}/top",
            headers=headers,
            params={"t": cfg.get("time", "day"), "limit": cfg.get("limit", 25)},
            timeout=30,
        )
        resp.raise_for_status()
        items.extend(parse_listing(resp.json(), sub))
    return items
