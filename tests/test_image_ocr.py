from pathlib import Path

from xhs_agent.ocr.image_ocr import ImageOcr


class _FakeEngine:
    def __call__(self, image_path: str):
        assert Path(image_path).name == "post-1.png"
        return ([[None, "Redis 为什么快"], [None, "MySQL 索引原理"]], None)


class _FakeHttpClient:
    def get(self, url: str, timeout: int):
        assert url == "https://cdn.example.com/post-1.png?x=1"
        assert timeout == 20
        return _FakeResponse()


class _FakeResponse:
    content = b"image-bytes"

    def raise_for_status(self) -> None:
        return None


def test_image_ocr_downloads_image_to_cache(tmp_path):
    ocr = ImageOcr(cache_dir=str(tmp_path), http_client=_FakeHttpClient(), engine=_FakeEngine())

    path = ocr.download_image("https://cdn.example.com/post-1.png?x=1", "post-1")

    assert Path(path) == tmp_path / "post-1.png"
    assert Path(path).read_bytes() == b"image-bytes"


def test_image_ocr_extracts_text_with_injected_engine(tmp_path):
    image_path = tmp_path / "post-1.png"
    image_path.write_bytes(b"image-bytes")
    ocr = ImageOcr(cache_dir=str(tmp_path), http_client=_FakeHttpClient(), engine=_FakeEngine())

    assert ocr.extract_text(str(image_path)) == "Redis 为什么快\nMySQL 索引原理"
