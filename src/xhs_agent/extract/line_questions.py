from __future__ import annotations

import re

NUMBER_PREFIX_RE = re.compile(r"^\s*(?:\d+[.)、]|[一二三四五六七八九十]+[、.]|\(\d+\))\s*")

# 规则负责快速排除明显非题目的行，LLM 负责最终判定和标准化
_NOT_A_QUESTION_PATTERN = re.compile(
    r"^(\d{4}年|字数|阅读|点赞|收藏|分享|发布于|来自|"
    r"iOS|Android|客户端|iPhone|编辑于|已编辑)",
)


def normalize_question_line(line: str) -> str:
    line = NUMBER_PREFIX_RE.sub("", line.strip())
    return re.sub(r"\s+", " ", line)


def split_to_candidate_lines(body: str) -> list[str]:
    """把正文按换行切分为候选行（仅做最粗的噪音剔除），不做题目判定。"""
    lines = [normalize_question_line(raw) for raw in body.splitlines()]
    return [
        line
        for line in lines
        if line
        and len(line) >= 4
        and len(line) <= 200
        and not _NOT_A_QUESTION_PATTERN.match(line)
    ]


def should_run_ocr(question_lines: list[str]) -> bool:
    return len(question_lines) == 0
