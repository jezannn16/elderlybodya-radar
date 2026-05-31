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
