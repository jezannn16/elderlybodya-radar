import os
from datetime import datetime, timezone

import requests

from radar.models import Item

ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"


def _parse_date(pubdate: str) -> datetime:
    for fmt in ("%Y %b %d", "%Y %b", "%Y"):
        try:
            return datetime.strptime(pubdate.strip(), fmt)
        except ValueError:
            continue
    return datetime.now(timezone.utc)


def parse_summary(data: dict) -> list[Item]:
    result = data.get("result", {})
    items: list[Item] = []
    for uid in result.get("uids", []):
        rec = result.get(uid, {})
        items.append(
            Item(
                source="pubmed",
                source_id=uid,
                title=rec.get("title", "").strip(),
                url=f"https://pubmed.ncbi.nlm.nih.gov/{uid}/",
                text=rec.get("fulljournalname", ""),
                published_at=_parse_date(rec.get("pubdate", "")),
            )
        )
    return items


def fetch(cfg: dict, since_days: int) -> list[Item]:
    api_key = os.environ.get("PUBMED_API_KEY")
    items: list[Item] = []
    for term in cfg.get("queries", []):
        params = {
            "db": "pubmed",
            "term": term,
            "retmax": cfg.get("retmax", 15),
            "sort": "date",
            "datetype": "pdat",
            "reldate": since_days,
            "retmode": "json",
        }
        if api_key:
            params["api_key"] = api_key
        ids = (
            requests.get(ESEARCH, params=params, timeout=30)
            .json()
            .get("esearchresult", {})
            .get("idlist", [])
        )
        if not ids:
            continue
        sp = {"db": "pubmed", "id": ",".join(ids), "retmode": "json"}
        if api_key:
            sp["api_key"] = api_key
        data = requests.get(ESUMMARY, params=sp, timeout=30).json()
        items.extend(parse_summary(data))
    return items
