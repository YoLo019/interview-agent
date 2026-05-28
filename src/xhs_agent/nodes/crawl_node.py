from __future__ import annotations

import random
import uuid

from xhs_agent.crawl.html_extract import extract_post_detail

FIXED_QUERIES = [
    "后端面经", "后端面试", "服务端面经", "Java 面经",
    "AI 应用开发 面经", "Agent 面经", "LLM 面经", "RAG 面经",
]

ANCHOR_QUERIES_POOL = [
    "Redis 面试", "MySQL 面试", "分布式 面试", "JVM 面试",
    "MQ 面试", "微服务 面试", "MCP 面试", "Function Calling 面试",
    "Prompt 面试", "向量数据库 面试",
]

MAX_CANDIDATE_URLS = 200
MAX_DETAIL_PAGES = 100


class CrawlNode:
    def __init__(self, browser) -> None:
        self._browser = browser

    def run(self, state) -> None:
        if not self._browser.verify_login():
            state.warnings.append("login_expired")
            return

        all_urls: set[str] = set()

        for query in FIXED_QUERIES:
            urls = self._browser.search_posts(query, max_scrolls=3)
            all_urls.update(urls)
            if len(all_urls) >= MAX_CANDIDATE_URLS:
                break

        anchor_queries = random.sample(ANCHOR_QUERIES_POOL, k=min(3, len(ANCHOR_QUERIES_POOL)))
        for query in anchor_queries:
            urls = self._browser.search_posts(query, max_scrolls=3)
            all_urls.update(urls)

        posts = []
        urls_to_fetch = list(all_urls)[:MAX_DETAIL_PAGES]
        for post_url in urls_to_fetch:
            try:
                html = self._browser.open_post_detail(post_url)
                publish_time = self._browser.extract_publish_time(html)
                if not publish_time:
                    state.warnings.append("publish_time_missing")
                    continue
                if not publish_time.startswith(state.target_date):
                    continue
                post = extract_post_detail(html)
                post.post_id = str(uuid.uuid4())
                post.published_date = publish_time
                posts.append(
                    {
                        "post_id": post.post_id,
                        "title": post.title,
                        "body_text": post.body_text,
                        "image_urls": post.image_urls,
                        "published_date": post.published_date,
                    }
                )
            except Exception:
                continue
        state.raw_posts = posts
