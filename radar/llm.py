import json
import time

import requests

from radar.models import Item
from radar.writer import build_rank_prompt, build_draft_prompt, STYLE_GUIDE

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t[3:]
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    return t.strip()


class LLM:
    """Groq chat-completions client (OpenAI-compatible)."""

    def __init__(
        self,
        api_key: str,
        model: str = "llama-3.3-70b-versatile",
        url: str = GROQ_URL,
        poster=None,
    ):
        self.api_key = api_key
        self.model = model
        self.url = url
        self._post = poster or requests.post

    def _generate(self, prompt: str, retries: int = 3) -> str:
        last = None
        for attempt in range(retries):
            try:
                resp = self._post(
                    self.url,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.7,
                    },
                    timeout=60,
                )
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]
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
