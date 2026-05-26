from __future__ import annotations

from bs4 import BeautifulSoup

from xhs_agent.models import RawPost


def extract_post_detail(html: str) -> RawPost:
    soup = BeautifulSoup(html, "html.parser")
    title_node = soup.select_one(".title")
    title = title_node.get_text(strip=True) if title_node else ""
    body_lines = [node.get_text(strip=True) for node in soup.select(".content p")]
    image_urls = [node["src"] for node in soup.select("img.note-image") if node.get("src")]
    return RawPost(
        post_id="",
        title=title,
        body_text="\n".join(line for line in body_lines if line),
        image_urls=image_urls,
    )
