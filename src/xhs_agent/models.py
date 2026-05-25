from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RawPost:
    post_id: str
    title: str
    body_text: str
    image_urls: list[str] = field(default_factory=list)
    published_date: str = ""
    author_name: str = ""
