from __future__ import annotations

import re
import time
from pathlib import Path
from urllib.parse import quote

from playwright.sync_api import Page, sync_playwright


class BrowserSession:
    SEARCH_URL = "https://www.xiaohongshu.com/search_result?keyword={keyword}&sort=time"

    def __init__(self, storage_state_path: str) -> None:
        self.storage_state_path = storage_state_path
        self._playwright = None
        self._browser = None
        self._context = None

    def __enter__(self):
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=True)
        self._context = self._browser.new_context(
            storage_state=str(Path(self.storage_state_path)),
            viewport={"width": 1280, "height": 800},
        )
        return self

    def __exit__(self, *args):
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    def _new_page(self) -> Page:
        return self._context.new_page()

    def search_posts(self, keyword: str, max_scrolls: int = 5) -> list[str]:
        page = self._new_page()
        url = self.SEARCH_URL.format(keyword=quote(keyword))
        page.goto(url, wait_until="networkidle", timeout=30000)
        time.sleep(2)

        collected: set[str] = set()
        for _ in range(max_scrolls):
            page.evaluate("window.scrollBy(0, 800)")
            time.sleep(1.5)
            links = page.eval_on_selector_all(
                'a[href*="/explore/"]',
                "els => els.map(el => el.href)",
            )
            collected.update(links)

        page.close()
        return list(collected)

    def open_post_detail(self, post_url: str) -> str:
        page = self._new_page()
        page.goto(post_url, wait_until="networkidle", timeout=30000)
        time.sleep(1)
        html = page.content()
        page.close()
        return html

    def extract_publish_time(self, html: str) -> str | None:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        time_meta = soup.select_one('meta[itemprop="datePublished"]')
        if time_meta:
            return time_meta.get("content")
        match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})', html)
        return match.group(1) if match else None

    def verify_login(self) -> bool:
        page = self._new_page()
        page.goto("https://www.xiaohongshu.com", wait_until="networkidle", timeout=15000)
        html = page.content()
        page.close()
        return "login" not in html.lower()[:2000] and "验证" not in html[:2000]
