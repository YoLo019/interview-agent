from xhs_agent.models import RawPost
from xhs_agent.process.enricher import AnswerCard, EnrichedPost, Enricher


class FakeLlmClient:
    def classify_and_enrich(self, title: str, questions: list[str]) -> dict:
        return {
            "category": "backend",
            "company_name": "PDD",
            "round_name": "一面",
            "normalized_questions": [
                "项目怎么部署上线？",
                "Nginx 和 Spring Boot 如何通信？",
            ],
            "knowledge_tags": ["部署", "Nginx", "Spring Boot"],
        }

    def answer_question(self, question: str) -> dict:
        return {
            "question": question,
            "answer": "先给结论，再讲方案和边界。",
            "why_asked": "考察候选人是否理解核心原理和工程取舍。",
            "answer_structure": ["结论", "原理", "落地做法", "边界"],
            "follow_ups": ["有什么坑？"],
        }


def test_enricher_returns_structured_backend_post():
    post = RawPost(
        post_id="1",
        title="PDD服务端一面",
        body_text="项目怎么上线\nnginx 和 springboot 如何通信",
    )

    enriched = Enricher(FakeLlmClient()).enrich(post, post_questions=post.body_text.splitlines())

    assert isinstance(enriched, EnrichedPost)
    assert enriched.category == "backend"
    assert enriched.company_name == "PDD"
    assert enriched.round_name == "一面"
    assert enriched.normalized_questions == [
        "项目怎么部署上线？",
        "Nginx 和 Spring Boot 如何通信？",
    ]
    assert enriched.knowledge_tags == ["部署", "Nginx", "Spring Boot"]


def test_enricher_rejects_excluded_go_and_cpp_posts():
    post = RawPost(
        post_id="2",
        title="Golang一面",
        body_text="项目介绍",
    )

    assert Enricher(FakeLlmClient()).is_supported_post(post) is False


def test_enricher_returns_structured_answer_card():
    card = Enricher(FakeLlmClient()).answer("Redis 为什么快？")

    assert isinstance(card, AnswerCard)
    assert card.question == "Redis 为什么快？"
    assert card.answer_structure == ["结论", "原理", "落地做法", "边界"]
