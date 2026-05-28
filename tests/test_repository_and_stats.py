from datetime import date, timedelta
from xhs_agent.process.stats import build_tag_counts, compute_trend_lines


def test_build_tag_counts_returns_descending_frequency():
    counts = build_tag_counts(
        [
            ["Redis", "缓存"],
            ["Redis", "MySQL"],
            ["MySQL"],
        ]
    )

    assert counts == [("MySQL", 2), ("Redis", 2), ("缓存", 1)]


def test_compute_trend_lines_detects_surge():
    target = (date.today() - timedelta(days=1)).isoformat()

    class FakeRepo:
        def tag_counts_for_date_range(self, start, end):
            return {"2026-04-01": [("RAG", 1)], "2026-04-02": [("RAG", 2)], "2026-04-03": [("RAG", 0)],
                    "2026-04-04": [("RAG", 1)], "2026-04-05": [("RAG", 1)], "2026-04-06": [("RAG", 1)]}

    current = [("RAG", 5), ("Redis", 3)]
    lines = compute_trend_lines(target, current, FakeRepo())

    assert any("RAG" in line for line in lines)
