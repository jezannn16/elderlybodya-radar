from datetime import datetime, timezone

import requests

from radar.models import Item

SEARCH = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


def _parse_date(s: str) -> datetime:
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except (ValueError, TypeError):
        return datetime.now(timezone.utc)


def parse(data: dict) -> list[Item]:
    rows = data.get("resultList", {}).get("result", [])
    items: list[Item] = []
    for r in rows:
        src = r.get("source", "MED")
        rid = r.get("id", "")
        items.append(
            Item(
                source="europepmc",
                source_id=f"{src}/{rid}",
                title=r.get("title", "").strip(),
                url=f"https://europepmc.org/abstract/{src}/{rid}",
                text=r.get("abstractText", "") or "",
                published_at=_parse_date(r.get("firstPublicationDate", "")),
            )
        )
    return items


def fetch(cfg: dict, since_days: int) -> list[Item]:
    items: list[Item] = []
    for term in cfg.get("queries", []):
        params = {
            "query": term,
            "format": "json",
            "pageSize": cfg.get("page_size", 15),
            "sort": "P_PDATE_D desc",
        }
        data = requests.get(SEARCH, params=params, timeout=30).json()
        items.extend(parse(data))
    return items
