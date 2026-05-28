from __future__ import annotations

from xhs_agent.crawl.candidate_filter import is_candidate_post
from xhs_agent.models import RawPost
from xhs_agent.process.stats import build_tag_counts


class ClassifyNode:
    def __init__(self, enricher, repository) -> None:
        self._enricher = enricher
        self._repository = repository

    def run(self, state) -> None:
        enriched_posts = []
        top_posts = []
        tag_lists = []
        for item in state.extracted_posts:
            if not is_candidate_post(item["title"], item["body_text"]):
                continue
            post = RawPost(
                post_id=item["post_id"],
                title=item["title"],
                body_text=item["body_text"],
            )
            enriched = self._enricher.enrich(post, post_questions=item["question_lines"])
            self._repository.save_post(state.target_date, enriched)
            enriched_posts.append(enriched)
            top_posts.append(
                {
                    "company_name": enriched.company_name,
                    "round_name": enriched.round_name,
                    "questions": enriched.normalized_questions[:3],
                }
            )
            tag_lists.append(enriched.knowledge_tags)
        state.enriched_posts = enriched_posts
        state.top_posts = top_posts
        state.top_tags = build_tag_counts(tag_lists)
