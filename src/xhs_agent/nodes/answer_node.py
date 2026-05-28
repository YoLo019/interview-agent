from __future__ import annotations


class AnswerNode:
    def __init__(self, enricher) -> None:
        self._enricher = enricher

    def run(self, state) -> None:
        answer_cards = []
        for item in state.selected_questions:
            try:
                card = self._enricher.answer(item["question"])
                answer_cards.append(
                    {
                        "question": card.question,
                        "count": item["count"],
                        "answer": card.answer,
                        "why_asked": card.why_asked,
                        "answer_structure": card.answer_structure,
                        "follow_ups": card.follow_ups,
                    }
                )
            except Exception:
                state.warnings.append("answer_generation_failed")
        state.answer_cards = answer_cards
