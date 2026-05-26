from __future__ import annotations

import json

from xhs_agent.llm.prompts import (
    ANSWER_PROMPT,
    CLASSIFY_AND_ENRICH_PROMPT,
    EXTRACT_QUESTIONS_PROMPT,
)


class LlmClient:
    def __init__(self, api_key: str, model: str = "gpt-5.2") -> None:
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)
        self._model = model

    def _call_json(self, system_prompt: str, user_input: str) -> dict:
        response = self._client.responses.create(
            model=self._model,
            instructions=system_prompt,
            input=user_input,
            text={"format": {"type": "json_object"}},
        )
        return json.loads(response.output_text)

    def extract_questions(self, candidate_lines: list[str]) -> list[str]:
        if not candidate_lines:
            return []
        payload = self._call_json(
            EXTRACT_QUESTIONS_PROMPT,
            "\n".join(f"- {line}" for line in candidate_lines),
        )
        return payload.get("questions", [])

    def classify_and_enrich(self, title: str, questions: list[str]) -> dict:
        user_input = f"Title: {title}\nQuestions:\n" + "\n".join(f"- {q}" for q in questions)
        return self._call_json(CLASSIFY_AND_ENRICH_PROMPT, user_input)

    def answer_question(self, question: str) -> dict:
        return self._call_json(ANSWER_PROMPT, question)
