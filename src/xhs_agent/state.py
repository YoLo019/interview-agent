from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class DailyJobState:
    target_date: str
    raw_posts: list[dict] = field(default_factory=list)
    extracted_posts: list[dict] = field(default_factory=list)
    enriched_posts: list = field(default_factory=list)
    selected_questions: list[dict] = field(default_factory=list)
    answer_cards: list[dict] = field(default_factory=list)
    top_posts: list[dict] = field(default_factory=list)
    top_tags: list[tuple[str, int]] = field(default_factory=list)
    trend_lines: list[str] = field(default_factory=list)
    observation_lines: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    report_markdown: str = ""
    report_url: str = ""
    dedupe_map: dict[str, int] | None = None
