from __future__ import annotations

import logging

from xhs_agent.config import build_target_window

logger = logging.getLogger("xhs_agent")


class DailyRunner:
    def __init__(self, crawler, pipeline, publisher=None, timezone_name: str = "Asia/Shanghai") -> None:
        self._crawler = crawler
        self._pipeline = pipeline
        self._publisher = publisher
        self._timezone_name = timezone_name

    def run(self, run_date: str) -> dict:
        _, _, target_date = build_target_window(self._timezone_name, run_date)

        try:
            posts = self._crawler.fetch_posts_for_date(target_date)
        except Exception as e:
            logger.error("crawl failed for %s: %s", target_date, e)
            return {
                "target_date": target_date,
                "top_posts": [],
                "top_tags": [],
                "answered_questions": [],
                "trend_lines": [],
                "observation_lines": [],
                "warnings": ["crawl_failed"],
                "markdown": "",
            }

        result = self._pipeline.process_posts(posts, target_date)
        result["target_date"] = target_date
        result.setdefault("warnings", [])
        result.setdefault("markdown", "")

        if self._publisher is not None and result["markdown"]:
            try:
                pub_result = self._publisher.publish_markdown(
                    title=f"{target_date} 小红书后端 / AI 应用开发面经日报",
                    markdown=result["markdown"],
                )
                result["url"] = pub_result["url"]
                logger.info("report published to %s", pub_result["url"])
            except Exception as e:
                logger.error("feishu publish failed after retries: %s", e)
                result["warnings"].append("feishu_publish_failed")

        return result
