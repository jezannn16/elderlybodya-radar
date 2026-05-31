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
