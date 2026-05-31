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
