from __future__ import annotations

from dataclasses import dataclass, field

from xhs_agent.crawl.candidate_filter import hard_excluded
from xhs_agent.models import RawPost


@dataclass(slots=True)
class AnswerCard:
    question: str
    answer: str
    why_asked: str
    answer_structure: list[str]
    follow_ups: list[str]


@dataclass(slots=True)
class EnrichedPost:
    post_id: str
    title: str
    body_text: str
    category: str
    company_name: str
    round_name: str
    normalized_questions: list[str] = field(default_factory=list)
    knowledge_tags: list[str] = field(default_factory=list)


class Enricher:
    def __init__(self, llm_client) -> None:
        self._llm = llm_client

    def is_supported_post(self, post: RawPost) -> bool:
        return not hard_excluded(post.title, post.body_text)

    def enrich(self, post: RawPost, post_questions: list[str]) -> EnrichedPost:
        payload = self._llm.classify_and_enrich(post.title, post_questions)
        return EnrichedPost(
            post_id=post.post_id,
            title=post.title,
            body_text=post.body_text,
            category=payload["category"],
            company_name=payload["company_name"],
            round_name=payload["round_name"],
            normalized_questions=payload["normalized_questions"],
            knowledge_tags=payload["knowledge_tags"],
        )

    def answer(self, question: str) -> AnswerCard:
        payload = self._llm.answer_question(question)
        return AnswerCard(
            question=payload["question"],
            answer=payload["answer"],
            why_asked=payload["why_asked"],
            answer_structure=payload["answer_structure"],
            follow_ups=payload["follow_ups"],
        )
