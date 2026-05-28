from __future__ import annotations

import httpx

BLOCK_PAGE = 1
BLOCK_TEXT = 2
BLOCK_HEADING_1 = 3
BLOCK_HEADING_2 = 4
BLOCK_HEADING_3 = 5
BLOCK_BULLET = 9
BLOCK_ORDERED_LIST = 10
BLOCK_DIVIDER = 18


class FeishuDocPublisher:
    def __init__(self, app_id: str, app_secret: str, parent_folder_token: str) -> None:
        self._app_id = app_id
        self._app_secret = app_secret
        self._parent_folder_token = parent_folder_token

    def _tenant_access_token(self) -> str:
        response = httpx.post(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": self._app_id, "app_secret": self._app_secret},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["tenant_access_token"]

    def _api_headers(self) -> dict:
        return {"Authorization": f"Bearer {self._tenant_access_token()}", "Content-Type": "application/json"}

    def publish_markdown(self, title: str, markdown: str, max_retries: int = 3) -> dict:
        import time

        blocks = self._markdown_to_blocks(markdown)
        if not blocks:
            raise ValueError("no blocks to publish")

        last_error = None
        for attempt in range(max_retries):
            try:
                token = self._api_headers()

                response = httpx.post(
                    "https://open.feishu.cn/open-apis/docx/v1/documents",
                    headers=token,
                    json={"title": title, "folder_token": self._parent_folder_token},
                    timeout=30,
                )
                response.raise_for_status()
                document_id = response.json()["data"]["document"]["document_id"]

                BATCH_SIZE = 50
                for i in range(0, len(blocks), BATCH_SIZE):
                    batch = blocks[i:i + BATCH_SIZE]
                    httpx.post(
                        f"https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}/blocks/{document_id}/children",
                        headers=token,
                        json={"children": batch},
                        timeout=60,
                    ).raise_for_status()

                doc_url = f"https://feishu.cn/docx/{document_id}"
                return {"document_id": document_id, "url": doc_url}

            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                continue

        raise RuntimeError(f"feishu publish failed after {max_retries} attempts: {last_error}")

    def _markdown_to_blocks(self, markdown: str) -> list[dict]:
        blocks: list[dict] = []
        for line in markdown.split("\n"):
            block = self._line_to_block(line)
            if block is not None:
                blocks.append(block)
        return blocks

    def _line_to_block(self, line: str) -> dict | None:
        stripped = line.strip()
        if not stripped:
            return None

        if stripped.startswith("### "):
            return self._heading_block(BLOCK_HEADING_3, stripped[4:])
        if stripped.startswith("## "):
            return self._heading_block(BLOCK_HEADING_2, stripped[3:])
        if stripped.startswith("# "):
            return self._heading_block(BLOCK_HEADING_1, stripped[2:])
        if stripped.startswith("- "):
            return self._bullet_block(stripped[2:])

        return self._text_block(stripped)

    def _heading_block(self, block_type: int, text: str) -> dict:
        return {
            "block_type": block_type,
            f"heading{block_type - 2}": {
                "elements": [{"text_run": {"content": text}}],
            },
        }

    def _text_block(self, text: str) -> dict:
        return {
            "block_type": BLOCK_TEXT,
            "text": {
                "elements": [{"text_run": {"content": text}}],
            },
        }

    def _bullet_block(self, text: str) -> dict:
        return {
            "block_type": BLOCK_BULLET,
            "bullet": {
                "elements": [{"text_run": {"content": text}}],
            },
        }
