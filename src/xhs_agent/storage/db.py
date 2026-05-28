from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_posts (
    post_id TEXT PRIMARY KEY,
    target_date TEXT NOT NULL,
    title TEXT NOT NULL,
    body_text TEXT NOT NULL,
    category TEXT NOT NULL,
    company_name TEXT,
    round_name TEXT
);

CREATE TABLE IF NOT EXISTS normalized_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id TEXT NOT NULL,
    target_date TEXT NOT NULL,
    question_text TEXT NOT NULL,
    UNIQUE(post_id, question_text),
    FOREIGN KEY(post_id) REFERENCES raw_posts(post_id)
);

CREATE TABLE IF NOT EXISTS knowledge_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id TEXT NOT NULL,
    target_date TEXT NOT NULL,
    tag TEXT NOT NULL,
    UNIQUE(post_id, tag),
    FOREIGN KEY(post_id) REFERENCES raw_posts(post_id)
);

CREATE TABLE IF NOT EXISTS daily_snapshots (
    target_date TEXT PRIMARY KEY,
    candidate_count INTEGER NOT NULL,
    valid_count INTEGER NOT NULL,
    question_count INTEGER NOT NULL,
    top_tags_json TEXT NOT NULL DEFAULT '[]',
    top_questions_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_questions_date ON normalized_questions(target_date);
CREATE INDEX IF NOT EXISTS idx_tags_date ON knowledge_tags(target_date);
CREATE INDEX IF NOT EXISTS idx_posts_date ON raw_posts(target_date);
"""


def connect(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.executescript(SCHEMA)
    return connection
