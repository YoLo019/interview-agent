from __future__ import annotations

from datetime import date, timedelta


def build_tag_counts(tag_lists: list[list[str]]) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for tags in tag_lists:
        for tag in tags:
            counts[tag] = counts.get(tag, 0) + 1
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def compute_trend_lines(
    target_date: str,
    current_tags: list[tuple[str, int]],
    repository,
) -> list[str]:
    try:
        end = date.fromisoformat(target_date)
        start = end - timedelta(days=7)
        history = repository.tag_counts_for_date_range(start.isoformat(), end.isoformat())

        historical_counts: dict[str, int] = {}
        for day_tags in history.values():
            for tag, cnt in day_tags:
                historical_counts[tag] = historical_counts.get(tag, 0) + cnt

        trend_lines = []
        for tag, today_cnt in current_tags[:10]:
            hist_cnt = historical_counts.get(tag, 0)
            avg = max(hist_cnt - today_cnt, 0) / max(len(history) - 1, 1)
            if avg > 0 and today_cnt > avg * 1.5:
                trend_lines.append(f"{tag} 当天出现 {today_cnt} 次，高于近 7 天日均 {avg:.1f} 次")

        ai_tags = {"RAG", "Agent", "LLM", "MCP", "Prompt", "Function Calling", "向量数据库", "Embedding", "Tool Calling", "Memory", "工作流", "评测", "观测"}
        today_ai = sum(cnt for tag, cnt in current_tags if tag in ai_tags)
        today_total = sum(cnt for _, cnt in current_tags)
        hist_ai = sum(cnt for tag, cnt in historical_counts.items() if tag in ai_tags)
        hist_total = sum(historical_counts.values())
        if today_total > 0 and hist_total > 0:
            today_ratio = today_ai / today_total * 100
            hist_ratio = hist_ai / hist_total * 100
            if today_ratio > hist_ratio + 5:
                trend_lines.append(f"AI/Agent 相关题占比 {today_ratio:.0f}%，较近 7 天均值 {hist_ratio:.0f}% 明显上升")

        return trend_lines
    except Exception:
        return []


def compute_observation_lines(
    target_date: str,
    company_summary: list[tuple[str, int]],
    current_tags: list[tuple[str, int]],
    repository,
) -> list[str]:
    lines = []

    for company, cnt in company_summary[:5]:
        if cnt >= 2:
            lines.append(f"{company} 当天出现 {cnt} 篇面经")

    try:
        tag_set = {tag for tag, _ in current_tags[:8]}
        end = date.fromisoformat(target_date)
        start = end - timedelta(days=3)
        recent = repository.tag_counts_for_date_range(start.isoformat(), end.isoformat())
        for tag in tag_set:
            days_seen = sum(1 for day_tags in recent.values() if tag in dict(day_tags))
            if days_seen >= 3:
                lines.append(f"{tag} 连续 {days_seen} 天高频出现")
                break
    except Exception:
        pass

    return lines[:5]
