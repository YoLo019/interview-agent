from __future__ import annotations

import argparse
import logging
import sys
import traceback

from xhs_agent.config import Settings
from xhs_agent.crawl.browser import BrowserSession
from xhs_agent.llm.client import LlmClient
from xhs_agent.ocr.image_ocr import ImageOcr
from xhs_agent.process.enricher import Enricher
from xhs_agent.nodes.answer_node import AnswerNode
from xhs_agent.nodes.classify_node import ClassifyNode
from xhs_agent.nodes.crawl_node import CrawlNode
from xhs_agent.nodes.extract_node import ExtractNode
from xhs_agent.nodes.question_select_node import QuestionSelectNode
from xhs_agent.nodes.report_node import ReportNode
from xhs_agent.orchestration.orchestrator import DailyOrchestrator
from xhs_agent.report.feishu import FeishuDocPublisher
from xhs_agent.runner import DailyRunner
from xhs_agent.storage.db import connect
from xhs_agent.storage.repository import Repository

logger = logging.getLogger("xhs_agent")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["run-daily"])
    parser.add_argument("--run-date", required=True)
    return parser


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    settings = Settings()
    parser = build_parser()
    args = parser.parse_args()

    if args.command != "run-daily":
        parser.print_help()
        sys.exit(1)

    logger.info("starting daily pipeline for run-date=%s", args.run_date)
    db_path = "data/xhs_agent.db"

    try:
        browser = BrowserSession(settings.xhs_storage_state_path)
        llm = LlmClient(settings.openai_api_key)
        repository = Repository(connect(db_path))
        enricher = Enricher(llm)
        orchestrator = DailyOrchestrator(
            crawl_node=CrawlNode(browser),
            extract_node=ExtractNode(ImageOcr(), llm),
            classify_node=ClassifyNode(enricher, repository),
            question_select_node=QuestionSelectNode(llm, settings.report_top_questions),
            answer_node=AnswerNode(enricher),
            report_node=ReportNode(repository),
        )
        publisher = FeishuDocPublisher(
            settings.feishu_app_id, settings.feishu_app_secret, settings.feishu_parent_folder_token,
        )

        runner = DailyRunner(crawler=orchestrator, pipeline=orchestrator, publisher=publisher)
        with browser:
            result = runner.run(run_date=args.run_date)

        logger.info("pipeline complete. target_date=%s, posts=%s, questions=%s, warnings=%s",
                     result["target_date"],
                     len(result.get("top_posts", [])),
                     len(result.get("answered_questions", [])),
                     result.get("warnings", []))

        if result.get("warnings"):
            for warning in result["warnings"]:
                logger.warning("pipeline warning: %s", warning)

        if result.get("url"):
            logger.info("report published: %s", result["url"])
        else:
            logger.info("report markdown (not published):\n%s", result.get("markdown", "(empty)")[:500])

    except Exception:
        logger.error("pipeline failed: %s", traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
