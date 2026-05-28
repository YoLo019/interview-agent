from __future__ import annotations

import json
import sqlite3

from xhs_agent.process.enricher import EnrichedPost


class Repository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def save_post(self, target_date: str, post: EnrichedPost) -> None:
        self._connection.execute(
            """
            INSERT OR REPLACE INTO raw_posts (post_id, target_date, title, body_text, category, company_name, round_name)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                post.post_id,
                target_date,
                post.title,
                post.body_text,
                post.category,
                post.company_name,
                post.round_name,
            ),
        )
        self._connection.executemany(
            "INSERT OR IGNORE INTO normalized_questions (post_id, target_date, question_text) VALUES (?, ?, ?)",
            [(post.post_id, target_date, question) for question in post.normalized_questions],
        )
        self._connection.executemany(
            "INSERT OR IGNORE INTO knowledge_tags (post_id, target_date, tag) VALUES (?, ?, ?)",
            [(post.post_id, target_date, tag) for tag in post.knowledge_tags],
        )
        self._connection.commit()

    def save_daily_snapshot(
        self, target_date: str, candidate_count: int, valid_count: int,
        question_count: int, top_tags: list[tuple[str, int]], top_questions: list[str],
    ) -> None:
        self._connection.execute(
            """
            INSERT OR REPLACE INTO daily_snapshots (target_date, candidate_count, valid_count, question_count, top_tags_json, top_questions_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (target_date, candidate_count, valid_count, question_count, json.dumps(top_tags), json.dumps(top_questions)),
        )
        self._connection.commit()

    def count_posts_for_date(self, target_date: str) -> int:
        row = self._connection.execute(
            "SELECT COUNT(*) FROM raw_posts WHERE target_date = ?", (target_date,)
        ).fetchone()
        return row[0] if row else 0

    def count_questions_for_date(self, target_date: str) -> int:
        row = self._connection.execute(
            "SELECT COUNT(*) FROM normalized_questions WHERE target_date = ?", (target_date,)
        ).fetchone()
        return row[0] if row else 0

    def tag_counts_for_date(self, target_date: str) -> list[tuple[str, int]]:
        rows = self._connection.execute(
            """
            SELECT tag, COUNT(*) as cnt FROM knowledge_tags
            WHERE target_date = ?
            GROUP BY tag ORDER BY cnt DESC, tag ASC
            """,
            (target_date,),
        ).fetchall()
        return [(row[0], row[1]) for row in rows]

    def tag_counts_for_date_range(self, start_date: str, end_date: str) -> dict[str, list[tuple[str, int]]]:
        rows = self._connection.execute(
            """
            SELECT target_date, tag, COUNT(*) as cnt FROM knowledge_tags
            WHERE target_date >= ? AND target_date <= ?
            GROUP BY target_date, tag ORDER BY target_date DESC, cnt DESC
            """,
            (start_date, end_date),
        ).fetchall()
        result: dict[str, list[tuple[str, int]]] = {}
        for date, tag, cnt in rows:
            result.setdefault(date, []).append((tag, cnt))
        return result

    def question_counts_for_date_range(self, start_date: str, end_date: str) -> dict[str, int]:
        rows = self._connection.execute(
            """
            SELECT target_date, COUNT(*) FROM normalized_questions
            WHERE target_date >= ? AND target_date <= ?
            GROUP BY target_date
            """,
            (start_date, end_date),
        ).fetchall()
        return {row[0]: row[1] for row in rows}

    def post_company_summary_for_date(self, target_date: str) -> list[tuple[str, int]]:
        rows = self._connection.execute(
            """
            SELECT company_name, COUNT(*) FROM raw_posts
            WHERE target_date = ? AND company_name IS NOT NULL AND company_name != ''
            GROUP BY company_name ORDER BY COUNT(*) DESC
            """,
            (target_date,),
        ).fetchall()
        return [(row[0], row[1]) for row in rows]
