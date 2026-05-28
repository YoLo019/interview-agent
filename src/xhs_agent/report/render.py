from __future__ import annotations


def render_daily_report(
    *,
    target_date: str,
    top_posts: list[dict],
    top_tags: list[tuple[str, int]],
    answered_questions: list[dict],
    trend_lines: list[str],
    observation_lines: list[str],
    candidate_count: int = 0,
    valid_count: int = 0,
) -> str:
    month, day = target_date.split("-")[1:]
    lines = [
        f"# {int(month)}月{int(day)}日 小红书后端 / AI 应用开发面经日报",
        "",
        "## 今日概览",
        f"- 候选帖子数：{candidate_count}",
        f"- 有效面经数：{valid_count}",
        f"- 入选重点面经：{len(top_posts)}",
        f"- 入选重点题目：{len(answered_questions)}",
        "",
        "## 最新面经",
    ]
    for item in top_posts:
        lines.append(f"- {item['company_name']} {item['round_name']}：{'；'.join(item['questions'])}")
    lines.extend(["", "## 高频知识点"])
    for tag, count in top_tags:
        lines.append(f"- {tag} x {count}")
    lines.extend(["", "## 高频题目与标准回答"])
    for item in answered_questions:
        lines.append(f"### {item['question']}")
        lines.append(f"- 标准回答：{item['answer']}")
        lines.append(f"- 考察点：{item['why_asked']}")
        lines.append(f"- 回答结构：{' / '.join(item['answer_structure'])}")
        lines.append(f"- 常见追问：{'；'.join(item['follow_ups'])}")
    lines.extend(["", "## 趋势变化"])
    if trend_lines:
        lines.extend(f"- {line}" for line in trend_lines)
    else:
        lines.append("- 暂无足够历史数据用于趋势分析")
    lines.extend(["", "## 重点观察"])
    if observation_lines:
        lines.extend(f"- {line}" for line in observation_lines)
    else:
        lines.append("- 本期无特别观察")
    return "\n".join(lines)
