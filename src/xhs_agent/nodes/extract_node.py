from __future__ import annotations

from xhs_agent.crawl.candidate_filter import hard_excluded
from xhs_agent.extract.line_questions import split_to_candidate_lines, should_run_ocr


class ExtractNode:
    def __init__(self, ocr, llm_client) -> None:
        self._ocr = ocr
        self._llm = llm_client

    def run(self, state) -> None:
        extracted = []
        for item in state.raw_posts:
            if hard_excluded(item["title"], item["body_text"]):
                continue

            candidate_lines = split_to_candidate_lines(item["body_text"])
            if should_run_ocr(candidate_lines):
                for index, image_url in enumerate(item.get("image_urls", [])):
                    try:
                        image_path = self._ocr.download_image(image_url, f"{item['post_id']}-{index}")
                        image_text = self._ocr.extract_text(image_path)
                        candidate_lines.extend(split_to_candidate_lines(image_text))
                    except Exception:
                        state.warnings.append("ocr_failed")
                if not candidate_lines:
                    continue

            questions = self._llm.extract_questions(candidate_lines)
            if questions:
                extracted.append({**item, "question_lines": questions})
        state.extracted_posts = extracted
