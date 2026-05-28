from __future__ import annotations

import json


DEDUPE_PROMPT = """
You are merging near-duplicate interview questions.

Given a list of questions, group questions that ask the same thing (even if phrased differently) and pick the best representative text for each group.

Examples of questions that should be merged:
- "Redis 为什么快" and "为什么 Redis 这么快" → same question
- "MySQL 索引失效场景有哪些" and "哪些情况会导致 MySQL 索引失效" → same question
- "缓存和 DB 一致性怎么保证" and "如何保证缓存与数据库的一致性" → same question
- "RAG 召回怎么优化" and "怎么提升 RAG 的召回效果" → same question

Examples that should NOT be merged:
- "Redis 为什么快" and "Redis 持久化机制" → different topics
- "MySQL 索引原理" and "MySQL 索引失效场景" → related but different questions

Return JSON with a single field "groups" — a list of groups, each with:
- "representative": the best representative text for the group
- "count": how many questions are in the group
- "members": list of all questions in the group

Input:
"""


def dedupe_questions(questions: list[str], llm_client) -> dict[str, int]:
    if len(questions) <= 1:
        return {q: 1 for q in questions}

    user_input = "\n".join(f"- {q}" for q in questions)
    try:
        response = llm_client._client.responses.create(
            model=llm_client._model,
            instructions=DEDUPE_PROMPT,
            input=user_input,
            text={"format": {"type": "json_object"}},
        )
        payload = json.loads(response.output_text)
        return {
            group["representative"]: group["count"]
            for group in payload.get("groups", [])
        }
    except Exception:
        counts: dict[str, int] = {}
        for q in questions:
            counts[q] = counts.get(q, 0) + 1
        return counts
