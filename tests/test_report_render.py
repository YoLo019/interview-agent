from xhs_agent.report.render import render_daily_report


def test_render_daily_report_contains_required_sections():
    report = render_daily_report(
        target_date="2026-04-08",
        top_posts=[
            {
                "company_name": "PDD",
                "round_name": "一面",
                "questions": ["项目怎么上线？", "Nginx 和 Spring Boot 如何通信？"],
            }
        ],
        top_tags=[("Redis", 2), ("MySQL", 2)],
        answered_questions=[
            {
                "question": "Redis 为什么快？",
                "answer": "先答内存访问，再答数据结构和线程模型。",
                "why_asked": "考察缓存原理基础。",
                "answer_structure": ["结论", "原理", "工程权衡"],
                "follow_ups": ["为什么单线程还能快？"],
            }
        ],
        trend_lines=["RAG 评测题开始升温"],
        observation_lines=["PDD 当天出现 2 篇相似面经"],
        candidate_count=15,
        valid_count=5,
    )

    assert "4月8日 小红书后端 / AI 应用开发面经日报" in report
    assert "## 今日概览" in report
    assert "## 高频题目与标准回答" in report
    assert "15" in report
