import argparse
import sys
from datetime import date

from radar.config import load_config, require_env
from radar.store import Store
from radar.filter import filter_items
from radar.llm import LLM
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
            llm = LLM(
                require_env("GROQ_API_KEY"),
                cfg.raw.get("model", "llama-3.3-70b-versatile"),
            )
            selected = llm.rank(candidates, cfg.drafts_per_day)
            for item, _reason in selected:
                drafts.append(llm.draft(item))
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
