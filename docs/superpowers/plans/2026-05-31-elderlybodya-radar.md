# ElderlyBodya Radar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Daily $0 content radar that pulls strength/powerlifting signals from PubMed, Europe PMC, RSS, Reddit and YouTube, ranks them with Gemini Flash, and DMs ready-to-edit post drafts to the channel owner via a Telegram bot.

**Architecture:** One Python process run by GitHub Actions cron (and `workflow_dispatch` for on-demand). Pipeline: fetch sources → normalize to `Item` → dedup against SQLite store → keyword filter → Gemini ranks top-N → Gemini drafts each → format digest → Telegram send → mark seen. State persisted between runs via Actions cache. Sources fetched sequentially with per-source try/except so one failure never kills the run.

**Tech Stack:** Python 3.12, `google-genai`, `feedparser`, `requests`, `PyYAML`, stdlib `sqlite3`, `pytest`.

Spec: `docs/superpowers/specs/2026-05-31-elderlybodya-radar-design.md`

---

## File Structure

```
radar/
  __init__.py
  models.py        # Item dataclass
  config.py        # load config.yaml + env secrets
  store.py         # SQLite dedup store
  filter.py        # keyword filter + dedup
  sources/
    __init__.py
    pubmed.py
    europepmc.py
    rss.py
    reddit.py
    youtube.py
  llm.py           # Gemini wrapper (rank + draft) with retry
  writer.py        # style-guide + prompt builders
  digest.py        # format digest, split >4096
  delivery.py      # Telegram sendMessage
  main.py          # pipeline orchestration + CLI
tests/             # one test module per unit
config.yaml
config.example.yaml
requirements.txt
requirements-dev.txt
.gitignore
README.md
.github/workflows/daily.yml
```

---

## Task 0: Project scaffolding

**Files:**
- Create: `.gitignore`, `requirements.txt`, `requirements-dev.txt`, `pytest.ini`, `radar/__init__.py`, `radar/sources/__init__.py`, `tests/__init__.py`

- [ ] **Step 1: Create `.gitignore`**

```gitignore
__pycache__/
*.pyc
.venv/
venv/
.env
state/
*.sqlite
.pytest_cache/
```

- [ ] **Step 2: Create `requirements.txt`**

```text
google-genai>=0.3.0
feedparser>=6.0.11
requests>=2.31.0
PyYAML>=6.0.1
```

- [ ] **Step 3: Create `requirements-dev.txt`**

```text
-r requirements.txt
pytest>=8.0.0
```

- [ ] **Step 4: Create `pytest.ini`**

```ini
[pytest]
testpaths = tests
python_files = test_*.py
```

- [ ] **Step 5: Create empty package files**

`radar/__init__.py`, `radar/sources/__init__.py`, `tests/__init__.py` — all empty.

- [ ] **Step 6: Create venv and install**

Run:
```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
```
Expected: installs without error.

- [ ] **Step 7: Commit**

```bash
git add .gitignore requirements.txt requirements-dev.txt pytest.ini radar tests
git commit -m "chore: project scaffolding"
```

---

## Task 1: `Item` model

**Files:**
- Create: `radar/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_models.py
from datetime import datetime
from radar.models import Item


def test_item_key_combines_source_and_id():
    it = Item(
        source="reddit",
        source_id="abc123",
        title="Bench tips",
        url="https://r/x",
        text="body",
        published_at=datetime(2026, 5, 31, 6, 0),
    )
    assert it.key == "reddit:abc123"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'radar.models'`

- [ ] **Step 3: Write minimal implementation**

```python
# radar/models.py
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Item:
    source: str
    source_id: str
    title: str
    url: str
    text: str
    published_at: datetime

    @property
    def key(self) -> str:
        return f"{self.source}:{self.source_id}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest tests/test_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add radar/models.py tests/test_models.py
git commit -m "feat: Item model"
```

---

## Task 2: Config loader

**Files:**
- Create: `radar/config.py`
- Test: `tests/test_config.py`

`load_config` reads YAML, merges `keywords.ru` + `keywords.en` into one lowercased list, and exposes raw source config. `require_env` fetches a secret or raises.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
import pytest
from radar.config import load_config, require_env


def test_load_config_merges_and_lowercases_keywords(tmp_path):
    p = tmp_path / "config.yaml"
    p.write_text(
        "timezone: Europe/Moscow\n"
        "run_hour: 6\n"
        "drafts_per_day: 5\n"
        "language: ru\n"
        "keywords:\n"
        "  ru: [Жим]\n"
        "  en: [Bench]\n"
        "sources:\n"
        "  reddit:\n"
        "    enabled: true\n"
        "    subreddits: [powerlifting]\n",
        encoding="utf-8",
    )
    cfg = load_config(str(p))
    assert cfg.drafts_per_day == 5
    assert cfg.keywords == ["жим", "bench"]
    assert cfg.sources["reddit"]["subreddits"] == ["powerlifting"]


def test_require_env_raises_when_missing(monkeypatch):
    monkeypatch.delenv("NOPE", raising=False)
    with pytest.raises(RuntimeError):
        require_env("NOPE")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'radar.config'`

- [ ] **Step 3: Write minimal implementation**

```python
# radar/config.py
import os
from dataclasses import dataclass

import yaml


@dataclass
class Config:
    timezone: str
    run_hour: int
    drafts_per_day: int
    language: str
    keywords: list[str]
    sources: dict
    raw: dict


def load_config(path: str = "config.yaml") -> Config:
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    kw = raw.get("keywords", {}) or {}
    keywords = [w.lower() for w in (kw.get("ru", []) + kw.get("en", []))]
    return Config(
        timezone=raw.get("timezone", "Europe/Moscow"),
        run_hour=int(raw.get("run_hour", 6)),
        drafts_per_day=int(raw.get("drafts_per_day", 5)),
        language=raw.get("language", "ru"),
        keywords=keywords,
        sources=raw.get("sources", {}) or {},
        raw=raw,
    )


def require_env(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        raise RuntimeError(f"Missing required env var: {name}")
    return val
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest tests/test_config.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add radar/config.py tests/test_config.py
git commit -m "feat: config loader"
```

---

## Task 3: SQLite dedup store

**Files:**
- Create: `radar/store.py`
- Test: `tests/test_store.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_store.py
from datetime import datetime, timedelta
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
        ((datetime.utcnow() - timedelta(days=90)).isoformat(), it.key),
    )
    s.conn.commit()
    s.prune(days=60)
    assert s.is_seen(it) is False
    s.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest tests/test_store.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'radar.store'`

- [ ] **Step 3: Write minimal implementation**

```python
# radar/store.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest tests/test_store.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add radar/store.py tests/test_store.py
git commit -m "feat: SQLite dedup store"
```

---

## Task 4: Keyword filter + batch dedup

**Files:**
- Create: `radar/filter.py`
- Test: `tests/test_filter.py`

`filter_items` drops already-seen items, keeps only keyword matches, and removes intra-batch duplicates by `key`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_filter.py
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
        _item("c", "Жим лёжа разбор"),      # off-topic? no — keep but...
        _item("a", "Жим лёжа разбор"),      # duplicate key of first
    ]
    store = FakeStore(seen_keys={"rss:c"})  # c already seen
    out = filter_items(items, ["жим"], store)
    keys = [i.key for i in out]
    assert keys == ["rss:a"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest tests/test_filter.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'radar.filter'`

- [ ] **Step 3: Write minimal implementation**

```python
# radar/filter.py
from radar.models import Item


def matches_keywords(item: Item, keywords: list[str]) -> bool:
    hay = f"{item.title} {item.text}".lower()
    return any(k in hay for k in keywords)


def filter_items(items: list[Item], keywords: list[str], store) -> list[Item]:
    out: list[Item] = []
    seen_in_batch: set[str] = set()
    for it in items:
        if it.key in seen_in_batch:
            continue
        if store.is_seen(it):
            continue
        if not matches_keywords(it, keywords):
            continue
        seen_in_batch.add(it.key)
        out.append(it)
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest tests/test_filter.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add radar/filter.py tests/test_filter.py
git commit -m "feat: keyword filter + batch dedup"
```

---

## Task 5: PubMed source

**Files:**
- Create: `radar/sources/pubmed.py`
- Test: `tests/test_pubmed.py`

Pure `parse_summary(data)` turns an esummary JSON into `Item`s. `fetch(cfg, since_days)` does esearch→esummary (network) then calls `parse_summary`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_pubmed.py
from radar.sources.pubmed import parse_summary


def test_parse_summary_builds_items():
    data = {
        "result": {
            "uids": ["40000001"],
            "40000001": {
                "uid": "40000001",
                "title": "Resistance training and hypertrophy",
                "pubdate": "2026 May",
                "fulljournalname": "J Strength",
            },
        }
    }
    items = parse_summary(data)
    assert len(items) == 1
    it = items[0]
    assert it.source == "pubmed"
    assert it.source_id == "40000001"
    assert it.title == "Resistance training and hypertrophy"
    assert it.url == "https://pubmed.ncbi.nlm.nih.gov/40000001/"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest tests/test_pubmed.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'radar.sources.pubmed'`

- [ ] **Step 3: Write minimal implementation**

```python
# radar/sources/pubmed.py
import os
from datetime import datetime

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
    return datetime.utcnow()


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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest tests/test_pubmed.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add radar/sources/pubmed.py tests/test_pubmed.py
git commit -m "feat: PubMed source"
```

---

## Task 6: Europe PMC source

**Files:**
- Create: `radar/sources/europepmc.py`
- Test: `tests/test_europepmc.py`

Europe PMC REST returns title + abstract in one call. Pure `parse(data)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_europepmc.py
from radar.sources.europepmc import parse


def test_parse_builds_items_with_abstract():
    data = {
        "resultList": {
            "result": [
                {
                    "id": "12345",
                    "source": "MED",
                    "title": "Protein intake and muscle",
                    "abstractText": "We studied protein...",
                    "firstPublicationDate": "2026-05-20",
                    "doi": "10.1/x",
                }
            ]
        }
    }
    items = parse(data)
    assert len(items) == 1
    it = items[0]
    assert it.source == "europepmc"
    assert it.source_id == "MED/12345"
    assert "protein" in it.text.lower()
    assert it.url == "https://europepmc.org/abstract/MED/12345"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest tests/test_europepmc.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# radar/sources/europepmc.py
from datetime import datetime

import requests

from radar.models import Item

SEARCH = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


def _parse_date(s: str) -> datetime:
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except (ValueError, TypeError):
        return datetime.utcnow()


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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest tests/test_europepmc.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add radar/sources/europepmc.py tests/test_europepmc.py
git commit -m "feat: Europe PMC source"
```

---

## Task 7: RSS source

**Files:**
- Create: `radar/sources/rss.py`
- Test: `tests/test_rss.py`

`parse_feed(parsed, feed_url)` maps a `feedparser`-style object to `Item`s. `fetch` calls `feedparser.parse` per URL.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_rss.py
import time
from types import SimpleNamespace
from radar.sources.rss import parse_feed


def test_parse_feed_builds_items():
    entry = SimpleNamespace(
        id="https://sbs.com/post1",
        title="How to bench more",
        summary="Technique tips for the bench press.",
        link="https://sbs.com/post1",
        published_parsed=time.struct_time((2026, 5, 30, 12, 0, 0, 0, 0, 0)),
    )
    parsed = SimpleNamespace(entries=[entry])
    items = parse_feed(parsed, "https://sbs.com/feed")
    assert len(items) == 1
    it = items[0]
    assert it.source == "rss"
    assert it.source_id == "https://sbs.com/post1"
    assert it.url == "https://sbs.com/post1"
    assert "bench" in it.text.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest tests/test_rss.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# radar/sources/rss.py
from datetime import datetime
from time import mktime

import feedparser

from radar.models import Item


def _date(entry) -> datetime:
    tp = getattr(entry, "published_parsed", None) or getattr(
        entry, "updated_parsed", None
    )
    if tp:
        return datetime.fromtimestamp(mktime(tp))
    return datetime.utcnow()


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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest tests/test_rss.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add radar/sources/rss.py tests/test_rss.py
git commit -m "feat: RSS source"
```

---

## Task 8: Reddit source

**Files:**
- Create: `radar/sources/reddit.py`
- Test: `tests/test_reddit.py`

`parse_listing(data, subreddit)` maps Reddit JSON → `Item`s. `fetch` gets an OAuth app-only token then queries `/r/{sub}/top`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_reddit.py
from radar.sources.reddit import parse_listing


def test_parse_listing_builds_items():
    data = {
        "data": {
            "children": [
                {
                    "data": {
                        "id": "t3abc",
                        "title": "My bench stalled, help",
                        "selftext": "Been stuck at 100kg...",
                        "permalink": "/r/powerlifting/comments/t3abc/x/",
                        "created_utc": 1769800000,
                    }
                }
            ]
        }
    }
    items = parse_listing(data, "powerlifting")
    assert len(items) == 1
    it = items[0]
    assert it.source == "reddit"
    assert it.source_id == "t3abc"
    assert it.url == "https://www.reddit.com/r/powerlifting/comments/t3abc/x/"
    assert "100kg" in it.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest tests/test_reddit.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# radar/sources/reddit.py
import os
from datetime import datetime

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
                published_at=datetime.utcfromtimestamp(
                    d.get("created_utc", 0)
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest tests/test_reddit.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add radar/sources/reddit.py tests/test_reddit.py
git commit -m "feat: Reddit source"
```

---

## Task 9: YouTube source

**Files:**
- Create: `radar/sources/youtube.py`
- Test: `tests/test_youtube.py`

`parse_search(data)` maps YouTube `search.list` JSON → `Item`s. `fetch` resolves each handle to a channelId, then pulls recent uploads via `search.list`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_youtube.py
from radar.sources.youtube import parse_search


def test_parse_search_builds_items():
    data = {
        "items": [
            {
                "id": {"kind": "youtube#video", "videoId": "vid123"},
                "snippet": {
                    "title": "Full bench day",
                    "description": "Programming a bench session.",
                    "publishedAt": "2026-05-29T10:00:00Z",
                },
            }
        ]
    }
    items = parse_search(data)
    assert len(items) == 1
    it = items[0]
    assert it.source == "youtube"
    assert it.source_id == "vid123"
    assert it.url == "https://www.youtube.com/watch?v=vid123"
    assert "bench" in it.text.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest tests/test_youtube.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# radar/sources/youtube.py
import os
from datetime import datetime, timedelta, timezone

import requests

from radar.models import Item

API = "https://www.googleapis.com/youtube/v3"


def _date(s: str) -> datetime:
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, TypeError):
        return datetime.utcnow()


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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest tests/test_youtube.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add radar/sources/youtube.py tests/test_youtube.py
git commit -m "feat: YouTube source"
```

---

## Task 10: Writer (style-guide + prompt builders)

**Files:**
- Create: `radar/writer.py`
- Test: `tests/test_writer.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_writer.py
from datetime import datetime
from radar.models import Item
from radar.writer import build_rank_prompt, build_draft_prompt, STYLE_GUIDE


def _item(t):
    return Item("rss", "1", t, "https://x", "body text", datetime(2026, 5, 31))


def test_rank_prompt_enumerates_candidates_and_asks_n():
    p = build_rank_prompt([_item("Жим лёжа"), _item("Присед")], n=1)
    assert "0" in p and "Жим лёжа" in p and "Присед" in p
    assert "1" in p  # the requested count appears
    assert "JSON" in p


def test_draft_prompt_includes_item_and_style():
    p = build_draft_prompt(_item("Жим лёжа"), STYLE_GUIDE)
    assert "Жим лёжа" in p
    assert "https://x" in p
    assert "Telegram" in p  # style guide text present
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest tests/test_writer.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# radar/writer.py
from radar.models import Item

STYLE_GUIDE = (
    "Ты пишешь посты для Telegram-канала о силовых тренировках, "
    "пауэрлифтинге и бодибилдинге. Аудитория — мужчины-лифтеры со средним "
    "и большим стажем.\n"
    "Голос: прямой, экспертный, без воды и канцелярита. Конкретика — "
    "килограммы, проценты от 1ПМ, подходы и повторы. Обращение на «вы». "
    "Уместна лёгкая ирония. Допустим сленг зала.\n"
    "Формат: цепляющий первый абзац; 2–4 коротких абзаца по делу; "
    "практический вывод; затем строка «Источник: <url>».\n"
    "Если пост касается тренировочных или медицинских утверждений — добавь "
    "короткую оговорку, что это не индивидуальная мед-рекомендация.\n"
    "Не выдумывай цифры и факты, которых нет в источнике."
)


def build_rank_prompt(candidates: list[Item], n: int) -> str:
    lines = [
        f"{i}. [{it.source}] {it.title} — {it.text[:200]}"
        for i, it in enumerate(candidates)
    ]
    body = "\n".join(lines)
    return (
        "Ниже пронумерованный список кандидатов для постов канала о силовых "
        "тренировках, пауэрлифтинге и бодибилдинге.\n\n"
        f"{body}\n\n"
        f"Отбери {n} самых релевантных и интересных аудитории. Верни СТРОГО "
        'JSON-массив объектов {"id": <число>, "reason": "<кратко по-русски>"} '
        "без markdown и без пояснений."
    )


def build_draft_prompt(item: Item, style_guide: str) -> str:
    return (
        f"{style_guide}\n\n"
        "Напиши готовый пост для Telegram на основе материала ниже.\n"
        f"Заголовок материала: {item.title}\n"
        f"Текст материала: {item.text[:1500]}\n"
        f"Ссылка-источник: {item.url}\n\n"
        'Верни СТРОГО JSON-объект {"text": "<готовый пост с переносами строк>", '
        '"alt_titles": ["<вариант 1>", "<вариант 2>"]} без markdown.'
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest tests/test_writer.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add radar/writer.py tests/test_writer.py
git commit -m "feat: writer style-guide and prompt builders"
```

---

## Task 11: Gemini LLM wrapper (rank + draft + retry)

**Files:**
- Create: `radar/llm.py`
- Test: `tests/test_llm.py`

`Gemini` accepts an injectable client for testing. `rank` returns `list[(Item, reason)]`; `draft` returns `{"text","alt_titles"}`. Both strip code fences and parse JSON. `_generate` retries on exception.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_llm.py
from datetime import datetime
from radar.models import Item
from radar.llm import Gemini


class FakeModels:
    def __init__(self, text):
        self._text = text

    def generate_content(self, model, contents):
        class R:
            text = self._text
        return R()


class FakeClient:
    def __init__(self, text):
        self.models = FakeModels(text)


def _items(*titles):
    return [
        Item("rss", str(i), t, "https://x", "b", datetime(2026, 5, 31))
        for i, t in enumerate(titles)
    ]


def test_rank_selects_items_by_id():
    g = Gemini("k", _client=FakeClient('[{"id": 1, "reason": "топ"}]'))
    out = g.rank(_items("a", "b"), n=1)
    assert len(out) == 1
    item, reason = out[0]
    assert item.title == "b"
    assert reason == "топ"


def test_draft_parses_json_with_fences():
    fenced = '```json\n{"text": "пост", "alt_titles": ["t1"]}\n```'
    g = Gemini("k", _client=FakeClient(fenced))
    d = g.draft(_items("a")[0], "style")
    assert d["text"] == "пост"
    assert d["alt_titles"] == ["t1"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest tests/test_llm.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# radar/llm.py
import json
import time

from google import genai

from radar.models import Item
from radar.writer import build_rank_prompt, build_draft_prompt, STYLE_GUIDE


def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t[3:]
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    return t.strip()


class Gemini:
    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash", _client=None):
        self.model_name = model_name
        self.client = _client or genai.Client(api_key=api_key)

    def _generate(self, prompt: str, retries: int = 3) -> str:
        last = None
        for attempt in range(retries):
            try:
                resp = self.client.models.generate_content(
                    model=self.model_name, contents=prompt
                )
                return resp.text
            except Exception as e:  # noqa: BLE001 - retry any transient error
                last = e
                time.sleep(2 ** attempt)
        raise last

    def rank(self, candidates: list[Item], n: int) -> list[tuple[Item, str]]:
        raw = self._generate(build_rank_prompt(candidates, n))
        picks = json.loads(_strip_fences(raw))
        out: list[tuple[Item, str]] = []
        for p in picks[:n]:
            idx = int(p["id"])
            if 0 <= idx < len(candidates):
                out.append((candidates[idx], p.get("reason", "")))
        return out

    def draft(self, item: Item, style_guide: str = STYLE_GUIDE) -> dict:
        raw = self._generate(build_draft_prompt(item, style_guide))
        return json.loads(_strip_fences(raw))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest tests/test_llm.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add radar/llm.py tests/test_llm.py
git commit -m "feat: Gemini wrapper with rank, draft, retry"
```

---

## Task 12: Digest formatter + message splitter

**Files:**
- Create: `radar/digest.py`
- Test: `tests/test_digest.py`

`split_message` chunks long text to ≤ limit. `format_digest` returns a list of Telegram messages: a header, then one message per draft; on `fallback` it lists raw links instead.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_digest.py
from datetime import datetime
from radar.models import Item
from radar.digest import split_message, format_digest


def test_split_message_respects_limit():
    parts = split_message("a" * 50, limit=20)
    assert all(len(p) <= 20 for p in parts)
    assert "".join(parts) == "a" * 50


def test_format_digest_header_and_one_message_per_draft():
    drafts = [
        {"text": "Пост один\nИсточник: u1", "alt_titles": ["А", "Б"]},
        {"text": "Пост два\nИсточник: u2", "alt_titles": []},
    ]
    msgs = format_digest("2026-05-31", drafts, errors=["Reddit недоступен"])
    assert len(msgs) == 3  # header + 2 drafts
    assert "2026-05-31" in msgs[0]
    assert "Reddit недоступен" in msgs[0]
    assert "Пост один" in msgs[1]
    assert "Варианты заголовка" in msgs[1]
    assert "Пост два" in msgs[2]


def test_format_digest_fallback_lists_links():
    items = [Item("rss", "1", "Заголовок", "https://x", "", datetime(2026, 5, 31))]
    msgs = format_digest("2026-05-31", drafts=[], errors=[], fallback=items)
    joined = "\n".join(msgs)
    assert "https://x" in joined
    assert "Заголовок" in joined
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest tests/test_digest.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# radar/digest.py
from radar.models import Item

LIMIT = 4096


def split_message(text: str, limit: int = LIMIT) -> list[str]:
    return [text[i : i + limit] for i in range(0, len(text), limit)] or [""]


def format_digest(
    date_str: str,
    drafts: list[dict],
    errors: list[str],
    fallback: list[Item] | None = None,
) -> list[str]:
    messages: list[str] = []

    header = [f"🏋️ Радар @elderlybodya — {date_str}"]
    if fallback:
        header.append(f"Черновиков нет (LLM недоступен). Сырьё: {len(fallback)}")
    else:
        header.append(f"Черновиков: {len(drafts)}")
    if errors:
        header.append("⚠ " + "; ".join(errors))
    messages.extend(split_message("\n".join(header)))

    if fallback:
        lines = [f"• {it.title}\n{it.url}" for it in fallback]
        messages.extend(split_message("\n\n".join(lines)))
        return messages

    for i, d in enumerate(drafts, 1):
        block = f"✏️ Черновик {i}\n\n{d.get('text', '')}"
        alts = d.get("alt_titles") or []
        if alts:
            block += "\n\nВарианты заголовка:\n" + "\n".join(f"— {a}" for a in alts)
        messages.extend(split_message(block))

    return messages
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest tests/test_digest.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add radar/digest.py tests/test_digest.py
git commit -m "feat: digest formatter and splitter"
```

---

## Task 13: Telegram delivery

**Files:**
- Create: `radar/delivery.py`
- Test: `tests/test_delivery.py`

`send_messages` POSTs each message to the Bot API. The HTTP poster is injectable for testing.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_delivery.py
from radar.delivery import send_messages


class FakePoster:
    def __init__(self):
        self.calls = []

    def __call__(self, url, json, timeout):
        self.calls.append((url, json))

        class R:
            def raise_for_status(self):
                pass
        return R()


def test_send_messages_posts_each():
    poster = FakePoster()
    send_messages(["m1", "m2"], token="TOK", chat_id="42", poster=poster)
    assert len(poster.calls) == 2
    url, payload = poster.calls[0]
    assert "botTOK" in url
    assert payload["chat_id"] == "42"
    assert payload["text"] == "m1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest tests/test_delivery.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# radar/delivery.py
import requests

API = "https://api.telegram.org"


def send_messages(messages: list[str], token: str, chat_id: str, poster=None) -> None:
    post = poster or requests.post
    url = f"{API}/bot{token}/sendMessage"
    for text in messages:
        resp = post(url, json={"chat_id": chat_id, "text": text}, timeout=30)
        resp.raise_for_status()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest tests/test_delivery.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add radar/delivery.py tests/test_delivery.py
git commit -m "feat: Telegram delivery"
```

---

## Task 14: Pipeline orchestration (`main.py`)

**Files:**
- Create: `radar/main.py`
- Test: `tests/test_main.py`

`run` wires everything: collect from each enabled source (isolated try/except), filter, rank, draft, format, deliver, mark seen. A source registry maps names → modules. `--dry-run` prints messages instead of sending and skips marking seen.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_main.py
from datetime import datetime
from radar.models import Item
from radar import main as m


def _item(sid, title):
    return Item("rss", sid, title, "https://x", "жим body", datetime(2026, 5, 31))


def test_run_collects_filters_drafts_and_sends(tmp_path, monkeypatch):
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        "drafts_per_day: 1\n"
        "keywords:\n  ru: [жим]\n  en: []\n"
        "state_path: " + str(tmp_path / "seen.sqlite").replace("\\", "/") + "\n"
        "sources:\n  rss:\n    enabled: true\n    feeds: [https://x/feed]\n",
        encoding="utf-8",
    )

    # one fake source returning two on-topic items
    monkeypatch.setattr(
        m, "SOURCES", {"rss": lambda cfg, since: [_item("a", "Жим 1"), _item("b", "Жим 2")]}
    )

    class FakeLLM:
        def __init__(self, *a, **k):
            pass

        def rank(self, candidates, n):
            return [(candidates[0], "топ")]

        def draft(self, item, style_guide=None):
            return {"text": f"пост про {item.title}", "alt_titles": []}

    monkeypatch.setattr(m, "Gemini", FakeLLM)

    sent = {}
    monkeypatch.setattr(
        m, "send_messages", lambda messages, token, chat_id, **k: sent.update(msgs=messages)
    )
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")

    code = m.run(str(cfg_path), dry_run=False)
    assert code == 0
    assert any("пост про Жим 1" in msg for msg in sent["msgs"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest tests/test_main.py -v`
Expected: FAIL — `AttributeError: module 'radar.main' has no attribute 'SOURCES'` (or ModuleNotFoundError)

- [ ] **Step 3: Write minimal implementation**

```python
# radar/main.py
import argparse
import os
import sys
from datetime import date

from radar.config import load_config, require_env
from radar.store import Store
from radar.filter import filter_items
from radar.llm import Gemini
from radar.digest import format_digest
from radar.delivery import send_messages
from radar.sources import pubmed, europepmc, rss, reddit, youtube

SOURCES = {
    "pubmed": pubmed.fetch,
    "europepmc": europepmc.fetch,
    "rss": rss.fetch,
    "reddit": reddit.fetch,
    "youtube": youtube.fetch,
}


def run(config_path: str = "config.yaml", dry_run: bool = False) -> int:
    cfg = load_config(config_path)
    since_days = int(cfg.raw.get("since_days", 2))
    state_path = cfg.raw.get("state_path", "state/seen.sqlite")

    collected = []
    errors: list[str] = []
    for name, fetch in SOURCES.items():
        scfg = cfg.sources.get(name, {})
        if not scfg.get("enabled"):
            continue
        try:
            collected.extend(fetch(scfg, since_days))
        except Exception as e:  # noqa: BLE001 - isolate source failures
            errors.append(f"{name} недоступен ({type(e).__name__})")

    store = Store(state_path)
    store.prune(days=int(cfg.raw.get("prune_days", 60)))
    candidates = filter_items(collected, cfg.keywords, store)

    drafts: list[dict] = []
    fallback = None
    if candidates:
        try:
            gem = Gemini(require_env("GEMINI_API_KEY"), cfg.raw.get("model", "gemini-2.0-flash"))
            selected = gem.rank(candidates, cfg.drafts_per_day)
            for item, _reason in selected:
                drafts.append(gem.draft(item))
        except Exception as e:  # noqa: BLE001 - LLM failure -> raw fallback
            errors.append(f"LLM недоступен ({type(e).__name__})")
            fallback = candidates[: cfg.drafts_per_day]

    messages = format_digest(date.today().isoformat(), drafts, errors, fallback)

    if dry_run:
        print("\n\n---\n\n".join(messages))
        store.close()
        return 0

    send_messages(
        messages,
        token=require_env("TELEGRAM_BOT_TOKEN"),
        chat_id=require_env("TELEGRAM_CHAT_ID"),
    )
    store.mark_seen(candidates)
    store.close()
    return 0


def _cli() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    return run(args.config, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(_cli())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest tests/test_main.py -v`
Expected: PASS

- [ ] **Step 5: Run the full suite**

Run: `.venv\Scripts\pytest -v`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add radar/main.py tests/test_main.py
git commit -m "feat: pipeline orchestration and CLI"
```

---

## Task 15: Config files + README

**Files:**
- Create: `config.example.yaml`, `config.yaml`, `README.md`

- [ ] **Step 1: Create `config.example.yaml`**

```yaml
timezone: Europe/Moscow
run_hour: 6
drafts_per_day: 5
language: ru
since_days: 2
prune_days: 60
state_path: state/seen.sqlite
model: gemini-2.0-flash

keywords:
  ru: [жим, присед, становая, гипертрофия, масса, бжу, креатин, профицит,
       программа, периодизация, объём, техника, протеин, силовые]
  en: [hypertrophy, resistance training, strength, bench press, "1rm",
       progressive overload, muscle protein synthesis, periodization, creatine]

sources:
  pubmed:
    enabled: true
    retmax: 15
    queries: ["resistance training", "muscle hypertrophy", "bench press",
              "progressive overload", "creatine supplementation"]
  europepmc:
    enabled: true
    page_size: 15
    queries: ["resistance training hypertrophy", "powerlifting performance",
              "protein muscle synthesis"]
  rss:
    enabled: true
    feeds:
      - https://www.strongerbyscience.com/feed/
      - https://barbend.com/feed/
      - https://t-nation.com/feed
      - https://rpstrength.com/blogs/articles.atom
      - https://zozhnik.ru/feed/
  reddit:
    enabled: true
    time: day
    limit: 25
    subreddits: [powerlifting, weightroom, naturalbodybuilding, bodybuilding, Fitness]
  youtube:
    enabled: true
    max_results: 5
    channels: ["@JeffNippard", "@RenaissancePeriodization",
               "@JuggernautTrainingSystems", "@SquatUniversity", "@alanthrall"]
```

- [ ] **Step 2: Create `config.yaml`**

Copy `config.example.yaml` to `config.yaml` (the live config; tweak feeds/channels later).

- [ ] **Step 3: Create `README.md`**

```markdown
# ElderlyBodya Radar

Daily $0 content radar for the Telegram channel **@elderlybodya** (strength /
powerlifting / bodybuilding). Pulls fresh signals from PubMed, Europe PMC, RSS,
Reddit and YouTube, ranks them with Gemini Flash, and DMs ready-to-edit post
drafts to the owner via a Telegram bot. The owner edits and publishes manually.

## Run locally (dry run, no sending)

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m radar.main --dry-run
```

## Secrets (env vars / GitHub Actions Secrets)

- `GEMINI_API_KEY`
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT`
- `YOUTUBE_API_KEY`
- optional `PUBMED_API_KEY`

## Schedule

Runs daily at 06:00 MSK via GitHub Actions, and on demand via the
"Run workflow" button (`workflow_dispatch`).
```

- [ ] **Step 4: Verify dry-run wiring (no secrets needed if all sources disabled)**

Run: `.venv\Scripts\python -c "import radar.main"`
Expected: imports cleanly (no syntax/import errors).

- [ ] **Step 5: Commit**

```bash
git add config.example.yaml config.yaml README.md
git commit -m "docs: config example, live config, README"
```

---

## Task 16: GitHub Actions workflow

**Files:**
- Create: `.github/workflows/daily.yml`

- [ ] **Step 1: Create the workflow**

```yaml
name: radar

on:
  schedule:
    - cron: "0 3 * * *"   # 03:00 UTC = 06:00 MSK
  workflow_dispatch: {}

jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Restore state
        uses: actions/cache@v4
        with:
          path: state
          key: radar-state-${{ github.run_id }}
          restore-keys: |
            radar-state-

      - name: Install deps
        run: pip install -r requirements.txt

      - name: Run radar
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
          REDDIT_CLIENT_ID: ${{ secrets.REDDIT_CLIENT_ID }}
          REDDIT_CLIENT_SECRET: ${{ secrets.REDDIT_CLIENT_SECRET }}
          REDDIT_USER_AGENT: ${{ secrets.REDDIT_USER_AGENT }}
          YOUTUBE_API_KEY: ${{ secrets.YOUTUBE_API_KEY }}
          PUBMED_API_KEY: ${{ secrets.PUBMED_API_KEY }}
        run: python -m radar.main
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/daily.yml
git commit -m "ci: daily radar workflow (cron + manual dispatch)"
```

---

## Task 17: Deploy — GitHub repo, secrets, first run

> This task performs outward-facing actions (creating a public repo, setting secrets, pushing). **Confirm with the owner before each push/secret step.** Account `jezannn16` is authenticated; token currently lacks the `workflow` scope, which is required to push workflow files.

- [ ] **Step 1: Add the `workflow` scope to the gh token**

Run: `gh auth refresh -h github.com -s workflow`
Expected: browser/device prompt; on success scopes include `workflow`.

- [ ] **Step 2: Create the public repo (no push yet)**

Run: `gh repo create elderlybodya-radar --public --source D:\elderlybodya-radar --remote origin`
Expected: repo created, `origin` remote added.

- [ ] **Step 3: Obtain the credentials**

- Telegram: create bot via @BotFather → `TELEGRAM_BOT_TOKEN`. Send the bot a message, then read your numeric chat id from `https://api.telegram.org/bot<token>/getUpdates` → `TELEGRAM_CHAT_ID`.
- Gemini: create key at Google AI Studio → `GEMINI_API_KEY`.
- Reddit: create a "script" app at reddit.com/prefs/apps → `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`; set `REDDIT_USER_AGENT` like `elderlybodya-radar/1.0 by u/<you>`.
- YouTube: enable YouTube Data API v3 in Google Cloud → `YOUTUBE_API_KEY`.

- [ ] **Step 4: Set repository secrets**

Run (one per secret, paste value when prompted):
```bash
gh secret set GEMINI_API_KEY -R jezannn16/elderlybodya-radar
gh secret set TELEGRAM_BOT_TOKEN -R jezannn16/elderlybodya-radar
gh secret set TELEGRAM_CHAT_ID -R jezannn16/elderlybodya-radar
gh secret set REDDIT_CLIENT_ID -R jezannn16/elderlybodya-radar
gh secret set REDDIT_CLIENT_SECRET -R jezannn16/elderlybodya-radar
gh secret set REDDIT_USER_AGENT -R jezannn16/elderlybodya-radar
gh secret set YOUTUBE_API_KEY -R jezannn16/elderlybodya-radar
```
(Optional: `gh secret set PUBMED_API_KEY ...`)

- [ ] **Step 5: Push**

Run: `git push -u origin master`
Expected: push succeeds (workflow scope present).

- [ ] **Step 6: Trigger a manual run**

Run: `gh workflow run radar -R jezannn16/elderlybodya-radar`
Then watch: `gh run watch -R jezannn16/elderlybodya-radar`
Expected: green run; the Telegram bot DMs you the digest.

- [ ] **Step 7: Verify dedup on a second run**

Run `gh workflow run radar` again; expected: far fewer/no repeated items (seen-state restored from cache).

---

## Self-Review (completed by plan author)

- **Spec coverage:** sources PubMed/EuropePMC/RSS/Reddit/YouTube → Tasks 5–9; filter/dedup → Task 4 + Task 3; Gemini rank+draft + free-tier-saving (filter before LLM) → Tasks 10–11; Telegram delivery → Task 13; digest + fallback on LLM failure + per-source error isolation → Tasks 12, 14; Actions cache state → Task 16; cron + on-demand dispatch → Task 16; config/secrets → Tasks 2, 15, 17. All spec sections mapped.
- **Placeholder scan:** no TBD/TODO; every code step has complete code.
- **Type consistency:** `Item(source, source_id, title, url, text, published_at)` + `.key` used identically across all tasks; every source exposes `fetch(cfg, since_days)`; `Gemini.rank -> list[(Item, reason)]`, `Gemini.draft -> {"text","alt_titles"}`; `format_digest(date_str, drafts, errors, fallback)`; `send_messages(messages, token, chat_id, poster=None)`; `main.SOURCES` registry + `run(config_path, dry_run)` match the test stubs.

Known acceptable deviation from spec: sources fetched sequentially (not async) — fine for ~5 sources on a daily cron; revisit only if runtime becomes an issue.
