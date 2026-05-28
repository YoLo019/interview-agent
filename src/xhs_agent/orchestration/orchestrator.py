from __future__ import annotations

from xhs_agent.state import DailyJobState


class DailyOrchestrator:
    def __init__(self, crawl_node, extract_node, classify_node, question_select_node, answer_node, report_node) -> None:
        self._crawl_node = crawl_node
        self._extract_node = extract_node
        self._classify_node = classify_node
        self._question_select_node = question_select_node
        self._answer_node = answer_node
        self._report_node = report_node

    def fetch_posts_for_date(self, target_date: str) -> list[dict]:
        state = DailyJobState(target_date=target_date)
        self._crawl_node.run(state)
        return state.raw_posts

    def process_posts(self, posts: list[dict], target_date: str) -> dict:
        state = DailyJobState(target_date=target_date, raw_posts=posts)
        self._extract_node.run(state)
        self._classify_node.run(state)
        self._question_select_node.run(state)
        self._answer_node.run(state)
        self._report_node.run(state)
        return {
            "top_posts": state.top_posts,
            "top_tags": state.top_tags,
            "answered_questions": state.answer_cards,
            "trend_lines": state.trend_lines,
            "observation_lines": state.observation_lines,
            "warnings": state.warnings,
            "markdown": state.report_markdown,
            "url": state.report_url,
        }
