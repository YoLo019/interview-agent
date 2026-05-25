from __future__ import annotations

from pathlib import Path

from rapidocr_onnxruntime import RapidOCR


class ImageOcr:
    def __init__(self) -> None:
        self._engine = RapidOCR()

    def extract_text(self, image_path: str) -> str:
        result, _ = self._engine(str(Path(image_path)))
        if not result:
            return ""
        return "\n".join(item[1] for item in result)
