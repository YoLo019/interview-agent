from __future__ import annotations

from xhs_agent.process.dedupe import dedupe_questions


CORE_BACKEND_KEYWORDS = ("Redis", "MySQL", "JVM", "缓存", "消息队列", "分布式", "Spring", "Nginx")
AI_AGENT_KEYWORDS = ("RAG", "Agent", "LLM", "MCP", "Prompt", "Function Calling", "向量", "Embedding", "Tool")


def _question_score(question: str, count: int) -> int:
    score = count * 10
    if any(keyword in question for keyword in CORE_BACKEND_KEYWORDS):
        score += 3
    if any(keyword in question for keyword in AI_AGENT_KEYWORDS):
        score += 4
    return score


class QuestionSelectNode:
    def __init__(self, llm_client, max_questions: int = 8) -> None:
        self._llm = llm_client
        self._max_questions = max_questions

    def run(self, state) -> None:
        all_questions = [
            question
            for enriched in state.enriched_posts
            for question in enriched.normalized_questions
        ]
        question_counts = dedupe_questions(all_questions, self._llm)
        ranked = sorted(
            question_counts.items(),
            key=lambda item: (-_question_score(item[0], item[1]), item[0]),
        )
        state.selected_questions = [
            {"question": question, "count": count}
            for question, count in ranked[: self._max_questions]
        ]
