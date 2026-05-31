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
