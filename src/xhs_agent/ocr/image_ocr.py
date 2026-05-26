from __future__ import annotations

from pathlib import Path


class ImageOcr:
    def __init__(self, cache_dir: str = ".cache/xhs-images", http_client=None, engine=None) -> None:
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._http_client = http_client
        self._engine = engine

    def download_image(self, url: str, name: str) -> str:
        suffix = Path(url.split("?")[0]).suffix or ".jpg"
        path = self._cache_dir / f"{name}{suffix}"
        client = self._http_client
        if client is None:
            import httpx

            client = httpx
        response = client.get(url, timeout=20)
        response.raise_for_status()
        path.write_bytes(response.content)
        return str(path)

    def extract_text(self, image_path: str) -> str:
        engine = self._engine
        if engine is None:
            from rapidocr_onnxruntime import RapidOCR

            engine = self._engine = RapidOCR()
        result, _ = engine(str(Path(image_path)))
        if not result:
            return ""
        return "\n".join(item[1] for item in result)
