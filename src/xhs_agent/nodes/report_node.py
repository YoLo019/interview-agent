from __future__ import annotations

from xhs_agent.process.stats import compute_observation_lines, compute_trend_lines
from xhs_agent.report.render import render_daily_report


class ReportNode:
    def __init__(self, repository) -> None:
        self._repository = repository

    def run(self, state) -> None:
        state.trend_lines = compute_trend_lines(
            state.target_date,
            state.top_tags,
            self._repository,
        )
        company_summary = self._repository.post_company_summary_for_date(state.target_date)
        state.observation_lines = compute_observation_lines(
            state.target_date,
            company_summary,
            state.top_tags,
            self._repository,
        )
        self._repository.save_daily_snapshot(
            target_date=state.target_date,
            candidate_count=len(state.raw_posts),
            valid_count=len(state.enriched_posts),
            question_count=len(state.answer_cards),
            top_tags=state.top_tags[:10],
            top_questions=[item["question"] for item in state.selected_questions],
        )

        state.report_markdown = render_daily_report(
            target_date=state.target_date,
            top_posts=state.top_posts,
            top_tags=state.top_tags,
            answered_questions=state.answer_cards,
            trend_lines=state.trend_lines,
            observation_lines=state.observation_lines,
            candidate_count=len(state.raw_posts),
            valid_count=len(state.enriched_posts),
        )
