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
