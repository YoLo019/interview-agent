from __future__ import annotations

import re

EXCLUDED_PATTERNS = (
    re.compile(r"\bgolang\b", re.IGNORECASE),
    re.compile(r"\bgo\b.*\b面试\b", re.IGNORECASE),
    re.compile(r"\bgolang\b.*\b面经\b", re.IGNORECASE),
    re.compile(r"\bc\+\+\b", re.IGNORECASE),
    re.compile(r"前端"),
    re.compile(r"产品经理"),
    re.compile(r"运营"),
)

RECALL_TOKENS = (
    "后端", "服务端", "java", "面经", "一面", "二面", "终面", "手撕",
    "redis", "mysql", "jvm", "rag", "agent", "llm", "mcp",
    "面试", "面试官", "八股", "校招", "社招",
)


def hard_excluded(title: str, body_text: str) -> bool:
    haystack = f"{title}\n{body_text}"
    return any(pattern.search(haystack) for pattern in EXCLUDED_PATTERNS)


def has_recall_signal(title: str, body_text: str) -> bool:
    haystack = f"{title}\n{body_text}".lower()
    return any(token in haystack for token in RECALL_TOKENS)


def is_candidate_post(title: str, preview_text: str) -> bool:
    if hard_excluded(title, preview_text):
        return False
    return has_recall_signal(title, preview_text)
