from xhs_agent.runner import DailyRunner


class FakeCrawler:
    def fetch_posts_for_date(self, target_date):
        return [
            {
                "post_id": "1",
                "title": "PDD服务端一面",
                "body_text": "项目怎么上线\nnginx 和 springboot 如何通信",
                "image_urls": [],
            }
        ]


class FakePipeline:
    def process_posts(self, posts, target_date):
        return {
            "top_posts": [{"company_name": "PDD", "round_name": "一面", "questions": ["项目怎么上线？"]}],
            "top_tags": [("部署", 1)],
            "answered_questions": [
                {
                    "question": "项目怎么上线？",
                    "answer": "先讲部署流程，再讲回滚和监控。",
                    "why_asked": "考察工程落地能力。",
                    "answer_structure": ["流程", "风险", "监控"],
                    "follow_ups": ["如何回滚？"],
                }
            ],
            "trend_lines": ["部署题仍然高频"],
            "observation_lines": ["PDD 当天样本质量较高"],
        }


def test_daily_runner_uses_previous_day_window():
    result = DailyRunner(FakeCrawler(), FakePipeline()).run(run_date="2026-04-09")

    assert result["target_date"] == "2026-04-08"
    assert "top_posts" in result
    assert result.get("warnings") is not None


def test_daily_runner_survives_crawl_failure():
    class BrokenCrawler:
        def fetch_posts_for_date(self, target_date):
            raise RuntimeError("network unreachable")

    result = DailyRunner(BrokenCrawler(), FakePipeline()).run(run_date="2026-04-09")

    assert result["target_date"] == "2026-04-08"
    assert result["warnings"] == ["crawl_failed"]
    assert result["top_posts"] == []
