# 小红书日报面经 Agent 实现计划

> **给 agent 执行者的要求：** 必须使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 按任务逐项执行本计划。所有步骤使用复选框 `- [ ]` 语法跟踪。

**目标：** 构建一个 Python agent，登录小红书，抓取前一天发布的后端与 AI 应用开发 / Agent 面经帖子，提取换行列表式题目，完成增强、去重、重点题目标准答案生成，并发布飞书日报。

**架构：** 当前版仍然按批处理 CLI 运行，但内部必须采用“薄编排层 + 统一状态对象 + 可替换 worker 节点”的结构。Playwright 负责登录态浏览；规则优先负责候选召回；只有当标题和正文不足以提取题目时才执行 OCR；LLM 负责分类、题目标准化、知识点打标与题目作答。使用 SQLite 持久化原始帖子、标准化题目和历史统计，支撑近 7 天趋势比较，同时让每个节点结果都可重放，为后续演进到多 agent 编排保留稳定边界。

**技术栈：** Python 3.12、Playwright、SQLite、Pydantic Settings、httpx、BeautifulSoup 4、rapidocr-onnxruntime、OpenAI Responses API、pytest

---

## 多 Agent 演进约束

当前版虽然不是多 agent，但从第一天起就必须满足下面约束：

- 所有阶段都围绕同一个 `DailyJobState` 读写，禁止节点之间通过零散参数直接耦合。
- 编排层只负责调度节点顺序和 checkpoint，不承载业务规则。
- 每个节点只做一件事，后续可以被独立 agent 或 graph node 替换。
- 每个节点的输入输出都必须可落库或可重放，便于局部重跑。
- LLM 调用统一走 client 和 prompts，不把模型调用散落到业务逻辑里。
- 当前版允许顺序执行，但节点边界必须稳定到后续可直接提升为 `crawl agent`、`extract agent`、`classify agent`、`answer agent`、`report agent`。

## 文件规划

### 项目级文件

- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `README.md`

### 应用主包

- Create: `src/xhs_agent/__init__.py`
- Create: `src/xhs_agent/config.py`
- Create: `src/xhs_agent/models.py`
- Create: `src/xhs_agent/state.py`
- Create: `src/xhs_agent/runner.py`
- Create: `src/xhs_agent/cli.py`

### 抓取与解析

- Create: `src/xhs_agent/crawl/browser.py`
- Create: `src/xhs_agent/crawl/html_extract.py`
- Create: `src/xhs_agent/crawl/candidate_filter.py`
- Create: `src/xhs_agent/extract/line_questions.py`
- Create: `src/xhs_agent/ocr/image_ocr.py`

### LLM 与业务处理

- Create: `src/xhs_agent/llm/client.py`
- Create: `src/xhs_agent/llm/prompts.py`
- Create: `src/xhs_agent/process/enricher.py`
- Create: `src/xhs_agent/process/dedupe.py`
- Create: `src/xhs_agent/process/stats.py`

### 编排与节点

- Create: `src/xhs_agent/orchestration/orchestrator.py`
- Create: `src/xhs_agent/nodes/crawl_node.py`
- Create: `src/xhs_agent/nodes/extract_node.py`
- Create: `src/xhs_agent/nodes/classify_node.py`
- Create: `src/xhs_agent/nodes/answer_node.py`
- Create: `src/xhs_agent/nodes/report_node.py`

### 存储与日报输出

- Create: `src/xhs_agent/storage/db.py`
- Create: `src/xhs_agent/storage/repository.py`
- Create: `src/xhs_agent/report/render.py`
- Create: `src/xhs_agent/report/feishu.py`

### 测试文件

- Create: `tests/test_config.py`
- Create: `tests/test_line_questions.py`
- Create: `tests/test_candidate_filter.py`
- Create: `tests/test_html_extract.py`
- Create: `tests/test_enricher.py`
- Create: `tests/test_repository_and_stats.py`
- Create: `tests/test_report_render.py`
- Create: `tests/test_runner.py`

## 任务 1：初始化 Python 项目骨架

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `README.md`
- Create: `src/xhs_agent/__init__.py`
- Create: `src/xhs_agent/config.py`
- Test: `tests/test_config.py`

- [ ] **步骤 1：初始化仓库和虚拟环境**

Run:

```powershell
git init
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
```

Expected:

```text
Initialized empty Git repository
Successfully installed pip
```

- [ ] **步骤 2：先写配置层失败测试**

```python
# tests/test_config.py
from xhs_agent.config import Settings, build_target_window


def test_build_target_window_uses_previous_day_in_shanghai():
    start, end, label = build_target_window("Asia/Shanghai", "2026-04-09")

    assert label == "2026-04-08"
    assert start.isoformat() == "2026-04-08T00:00:00+08:00"
    assert end.isoformat() == "2026-04-09T00:00:00+08:00"


def test_settings_default_report_values():
    settings = Settings(
        xhs_storage_state_path="secrets/xhs_state.json",
        feishu_app_id="cli_a",
        feishu_app_secret="secret",
        feishu_parent_folder_token="fldcn_demo",
        openai_api_key="sk-test",
    )

    assert settings.report_timezone == "Asia/Shanghai"
    assert settings.report_top_questions == 8
    assert settings.report_top_posts == 6
```

- [ ] **步骤 3：运行测试，确认当前失败**

Run:

```powershell
.venv\Scripts\python -m pytest tests/test_config.py -v
```

Expected:

```text
E   ModuleNotFoundError: No module named 'xhs_agent'
```

- [ ] **步骤 4：补最小可运行包结构、依赖和配置模块**

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=69", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "xhs-agent"
version = "0.1.0"
description = "Daily Xiaohongshu interview report agent"
requires-python = ">=3.12"
dependencies = [
  "beautifulsoup4>=4.12",
  "httpx>=0.27",
  "openai>=1.75.0",
  "playwright>=1.52.0",
  "pydantic>=2.7",
  "pydantic-settings>=2.2",
  "python-dateutil>=2.9.0",
  "rapidocr-onnxruntime>=1.4.3",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.3",
]

[tool.pytest.ini_options]
pythonpath = ["src"]
```

```python
# src/xhs_agent/__init__.py
__all__ = ["__version__"]

__version__ = "0.1.0"
```

```python
# src/xhs_agent/config.py
from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    xhs_storage_state_path: str
    feishu_app_id: str
    feishu_app_secret: str
    feishu_parent_folder_token: str
    openai_api_key: str
    report_timezone: str = "Asia/Shanghai"
    report_top_questions: int = 8
    report_top_posts: int = 6


def build_target_window(timezone_name: str, run_date_iso: str) -> tuple[datetime, datetime, str]:
    tz = ZoneInfo(timezone_name)
    run_date = date.fromisoformat(run_date_iso)
    target_date = run_date - timedelta(days=1)
    start = datetime.combine(target_date, datetime.min.time(), tzinfo=tz)
    end = start + timedelta(days=1)
    return start, end, target_date.isoformat()
```

```text
# .env.example
XHS_STORAGE_STATE_PATH=secrets/xhs_state.json
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_PARENT_FOLDER_TOKEN=folder_xxx
OPENAI_API_KEY=sk-xxx
REPORT_TIMEZONE=Asia/Shanghai
REPORT_TOP_QUESTIONS=8
REPORT_TOP_POSTS=6
```

```markdown
# README.md

## Xiaohongshu Daily Interview Report Agent

Use `.env` for credentials and `python -m xhs_agent.cli run-daily --run-date YYYY-MM-DD` to generate a report after later tasks are complete.
```

- [ ] **步骤 5：安装依赖并重新跑配置测试**

Run:

```powershell
.venv\Scripts\python -m pip install -e .[dev]
.venv\Scripts\python -m pytest tests/test_config.py -v
```

Expected:

```text
2 passed
```

- [ ] **步骤 6：提交初始化骨架**

Run:

```powershell
git add pyproject.toml .env.example README.md src/xhs_agent/__init__.py src/xhs_agent/config.py tests/test_config.py
git commit -m "chore: bootstrap xhs daily report agent"
```

## 任务 2：实现换行列表式题目提取和 OCR 触发判断

**Files:**
- Create: `src/xhs_agent/extract/line_questions.py`
- Create: `src/xhs_agent/ocr/image_ocr.py`
- Test: `tests/test_line_questions.py`

- [ ] **步骤 1：先写题目提取失败测试，覆盖有编号、无编号、连续描述拒绝和 OCR 触发**

```python
# tests/test_line_questions.py
from xhs_agent.extract.line_questions import extract_question_lines, should_run_ocr


def test_extract_question_lines_supports_numbered_and_plain_lines():
    body = """PDD服务端一面

1. 项目怎么上线，怎么部署
2. nginx 和 springboot 如何通信
手撕：数组按 k 分组"""

    assert extract_question_lines(body) == [
        "项目怎么上线，怎么部署",
        "nginx 和 springboot 如何通信",
        "手撕：数组按 k 分组",
    ]


def test_extract_question_lines_supports_one_question_per_line_without_numbers():
    body = """PDD服务端一面

项目怎么上线，怎么部署
nginx 和 springboot 如何通信
缓存与 db 一致性，如何确定最终一致"""

    assert extract_question_lines(body) == [
        "项目怎么上线，怎么部署",
        "nginx 和 springboot 如何通信",
        "缓存与 db 一致性，如何确定最终一致",
    ]


def test_extract_question_lines_rejects_continuous_prose():
    body = "今天问了 redis 和 mysql，还问了 rag，整体挺散，没有逐行列题。"

    assert extract_question_lines(body) == []


def test_should_run_ocr_only_when_text_questions_are_missing():
    assert should_run_ocr(["项目怎么上线"]) is False
    assert should_run_ocr([]) is True
```

- [ ] **步骤 2：运行提取层测试，确认失败**

Run:

```powershell
.venv\Scripts\python -m pytest tests/test_line_questions.py -v
```

Expected:

```text
E   ModuleNotFoundError: No module named 'xhs_agent.extract'
```

- [ ] **步骤 3：实现题目逐行提取和 OCR gating**

```python
# src/xhs_agent/extract/line_questions.py
from __future__ import annotations

import re

QUESTION_HINTS = (
    "为什么",
    "如何",
    "怎么",
    "区别",
    "原理",
    "手撕",
    "设计",
    "实现",
    "一致性",
    "上线",
    "部署",
    "通信",
)

NUMBER_PREFIX_RE = re.compile(r"^\s*(?:\d+[.)、]|[一二三四五六七八九十]+[、.]|\(\d+\))\s*")


def normalize_question_line(line: str) -> str:
    line = NUMBER_PREFIX_RE.sub("", line.strip())
    return re.sub(r"\s+", " ", line)


def looks_like_question_line(line: str) -> bool:
    if len(line) < 4:
        return False
    if "。" in line and "：" not in line and "?" not in line and "？" not in line:
        return False
    return any(token in line for token in QUESTION_HINTS)


def extract_question_lines(body: str) -> list[str]:
    lines = [normalize_question_line(raw) for raw in body.splitlines()]
    lines = [line for line in lines if line]
    return [line for line in lines if looks_like_question_line(line)]


def should_run_ocr(question_lines: list[str]) -> bool:
    return len(question_lines) == 0
```

```python
# src/xhs_agent/ocr/image_ocr.py
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
```

- [ ] **步骤 4：再次运行提取层测试，确认通过**

Run:

```powershell
.venv\Scripts\python -m pytest tests/test_line_questions.py -v
```

Expected:

```text
4 passed
```

- [ ] **步骤 5：提交题目提取切片**

Run:

```powershell
git add src/xhs_agent/extract/line_questions.py src/xhs_agent/ocr/image_ocr.py tests/test_line_questions.py
git commit -m "feat: add newline-list question extraction"
```

## 任务 3：解析小红书卡片和帖子详情

**Files:**
- Create: `src/xhs_agent/models.py`
- Create: `src/xhs_agent/crawl/candidate_filter.py`
- Create: `src/xhs_agent/crawl/html_extract.py`
- Create: `src/xhs_agent/crawl/browser.py`
- Test: `tests/test_candidate_filter.py`
- Test: `tests/test_html_extract.py`

- [ ] **步骤 1：先写候选召回和详情解析失败测试**

```python
# tests/test_candidate_filter.py
from xhs_agent.crawl.candidate_filter import is_candidate_post


def test_candidate_filter_accepts_backend_interview_titles():
    assert is_candidate_post("PDD服务端一面", "项目怎么上线\nnginx和springboot如何通信")


def test_candidate_filter_accepts_ai_agent_interview_titles():
    assert is_candidate_post("AI应用开发一面", "RAG召回链路\nAgent tool calling")


def test_candidate_filter_rejects_excluded_targets():
    assert is_candidate_post("Golang一面", "项目介绍") is False
    assert is_candidate_post("C++面经", "手撕题") is False
```

```python
# tests/test_html_extract.py
from xhs_agent.crawl.html_extract import extract_post_detail


HTML = """
<html>
  <body>
    <div class="title">PDD服务端一面</div>
    <div class="content">
      <p>项目怎么上线，怎么部署</p>
      <p>nginx和springboot如何通信</p>
      <p>手撕：数组按k分组</p>
    </div>
    <img class="note-image" src="https://cdn.example.com/1.png" />
  </body>
</html>
"""


def test_extract_post_detail_reads_title_body_and_images():
    post = extract_post_detail(HTML)

    assert post.title == "PDD服务端一面"
    assert post.body_text == "项目怎么上线，怎么部署\nnginx和springboot如何通信\n手撕：数组按k分组"
    assert post.image_urls == ["https://cdn.example.com/1.png"]
```

- [ ] **步骤 2：运行解析层测试，确认失败**

Run:

```powershell
.venv\Scripts\python -m pytest tests/test_candidate_filter.py tests/test_html_extract.py -v
```

Expected:

```text
E   ModuleNotFoundError: No module named 'xhs_agent.crawl'
```

- [ ] **步骤 3：实现领域模型和 HTML 解析**

```python
# src/xhs_agent/models.py
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class RawPost:
    post_id: str
    title: str
    body_text: str
    image_urls: list[str] = field(default_factory=list)
    published_date: str = ""
    author_name: str = ""
```

```python
# src/xhs_agent/crawl/candidate_filter.py
from __future__ import annotations

EXCLUDED_TOKENS = ("golang", "go ", "c++", "前端", "产品", "运营")
RECALL_TOKENS = (
    "后端",
    "服务端",
    "java",
    "面经",
    "一面",
    "二面",
    "终面",
    "手撕",
    "redis",
    "mysql",
    "jvm",
    "rag",
    "agent",
    "llm",
    "mcp",
)


def is_candidate_post(title: str, preview_text: str) -> bool:
    haystack = f"{title}\n{preview_text}".lower()
    if any(token in haystack for token in EXCLUDED_TOKENS):
        return False
    return any(token in haystack for token in RECALL_TOKENS)
```

```python
# src/xhs_agent/crawl/html_extract.py
from __future__ import annotations

from bs4 import BeautifulSoup

from xhs_agent.models import RawPost


def extract_post_detail(html: str) -> RawPost:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.select_one(".title").get_text(strip=True)
    body_lines = [node.get_text(strip=True) for node in soup.select(".content p")]
    image_urls = [node["src"] for node in soup.select("img.note-image")]
    return RawPost(
        post_id="",
        title=title,
        body_text="\n".join(line for line in body_lines if line),
        image_urls=image_urls,
    )
```

```python
# src/xhs_agent/crawl/browser.py
from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page, sync_playwright


class BrowserSession:
    def __init__(self, storage_state_path: str) -> None:
        self.storage_state_path = storage_state_path

    def open_page(self, url: str) -> str:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(storage_state=str(Path(self.storage_state_path)))
            page: Page = context.new_page()
            page.goto(url, wait_until="networkidle")
            html = page.content()
            context.close()
            browser.close()
            return html
```

- [ ] **步骤 4：再次运行解析层测试，确认通过**

Run:

```powershell
.venv\Scripts\python -m pytest tests/test_candidate_filter.py tests/test_html_extract.py -v
```

Expected:

```text
4 passed
```

- [ ] **步骤 5：安装 Playwright Chromium 并提交**

Run:

```powershell
.venv\Scripts\python -m playwright install chromium
git add src/xhs_agent/models.py src/xhs_agent/crawl/candidate_filter.py src/xhs_agent/crawl/html_extract.py src/xhs_agent/crawl/browser.py tests/test_candidate_filter.py tests/test_html_extract.py
git commit -m "feat: add xiaohongshu parsing primitives"
```

## 任务 4：实现分类、标准化、知识点标签和题目作答

**Files:**
- Create: `src/xhs_agent/llm/client.py`
- Create: `src/xhs_agent/llm/prompts.py`
- Create: `src/xhs_agent/process/enricher.py`
- Test: `tests/test_enricher.py`

- [ ] **步骤 1：先写分类和增强层失败测试**

```python
# tests/test_enricher.py
from xhs_agent.models import RawPost
from xhs_agent.process.enricher import Enricher, EnrichedPost


class FakeLlmClient:
    def classify_and_enrich(self, title: str, questions: list[str]) -> dict:
        return {
            "category": "backend",
            "company_name": "PDD",
            "round_name": "一面",
            "normalized_questions": [
                "项目怎么部署上线？",
                "Nginx 和 Spring Boot 如何通信？",
            ],
            "knowledge_tags": ["部署", "Nginx", "Spring Boot"],
        }

    def answer_question(self, question: str) -> dict:
        return {
            "question": question,
            "answer": "先给结论，再讲方案和边界。",
            "why_asked": "考察候选人是否理解核心原理和工程取舍。",
            "answer_structure": ["结论", "原理", "落地做法", "边界"],
            "follow_ups": ["有什么坑？"],
        }


def test_enricher_returns_structured_backend_post():
    post = RawPost(
        post_id="1",
        title="PDD服务端一面",
        body_text="项目怎么上线\nnginx 和 springboot 如何通信",
    )

    enriched = Enricher(FakeLlmClient()).enrich(post, post_questions=post.body_text.splitlines())

    assert isinstance(enriched, EnrichedPost)
    assert enriched.category == "backend"
    assert enriched.company_name == "PDD"
    assert enriched.round_name == "一面"
    assert enriched.knowledge_tags == ["部署", "Nginx", "Spring Boot"]


def test_enricher_rejects_excluded_go_and_cpp_posts():
    post = RawPost(
        post_id="2",
        title="Golang一面",
        body_text="项目介绍",
    )

    assert Enricher(FakeLlmClient()).is_supported_post(post) is False
```

- [ ] **步骤 2：运行增强层测试，确认失败**

Run:

```powershell
.venv\Scripts\python -m pytest tests/test_enricher.py -v
```

Expected:

```text
E   ModuleNotFoundError: No module named 'xhs_agent.process'
```

- [ ] **步骤 3：实现 LLM client、提示词和增强器**

```python
# src/xhs_agent/llm/client.py
from __future__ import annotations

import json

from openai import OpenAI


class LlmClient:
    def __init__(self, api_key: str, model: str = "gpt-5.2") -> None:
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def classify_and_enrich(self, title: str, questions: list[str]) -> dict:
        prompt = f"Title: {title}\nQuestions:\n" + "\n".join(f"- {q}" for q in questions)
        response = self._client.responses.create(
            model=self._model,
            input=prompt,
            text={"format": {"type": "json_object"}},
        )
        return json.loads(response.output_text)

    def answer_question(self, question: str) -> dict:
        response = self._client.responses.create(
            model=self._model,
            input=question,
            text={"format": {"type": "json_object"}},
        )
        return json.loads(response.output_text)
```

```python
# src/xhs_agent/llm/prompts.py
CLASSIFY_AND_ENRICH_PROMPT = """
You classify Xiaohongshu interview posts.
Allowed categories: backend, ai_agent, reject.
Reject Go, Golang, C++.
Only use facts present in the title and question lines.
Return JSON with company_name, round_name, normalized_questions, knowledge_tags.
"""

ANSWER_PROMPT = """
Return a standard interview answer in JSON.
Fields: question, answer, why_asked, answer_structure, follow_ups.
Keep the answer concise and directly useful for interview prep.
"""
```

```python
# src/xhs_agent/process/enricher.py
from __future__ import annotations

from dataclasses import dataclass, field

from xhs_agent.models import RawPost

EXCLUDED_TITLE_TOKENS = ("golang", "go ", "c++")


@dataclass(slots=True)
class AnswerCard:
    question: str
    answer: str
    why_asked: str
    answer_structure: list[str]
    follow_ups: list[str]


@dataclass(slots=True)
class EnrichedPost:
    post_id: str
    title: str
    body_text: str
    category: str
    company_name: str
    round_name: str
    normalized_questions: list[str] = field(default_factory=list)
    knowledge_tags: list[str] = field(default_factory=list)


class Enricher:
    def __init__(self, llm_client) -> None:
        self._llm = llm_client

    def is_supported_post(self, post: RawPost) -> bool:
        return not any(token in post.title.lower() for token in EXCLUDED_TITLE_TOKENS)

    def enrich(self, post: RawPost, post_questions: list[str]) -> EnrichedPost:
        payload = self._llm.classify_and_enrich(post.title, post_questions)
        return EnrichedPost(
            post_id=post.post_id,
            title=post.title,
            body_text=post.body_text,
            category=payload["category"],
            company_name=payload["company_name"],
            round_name=payload["round_name"],
            normalized_questions=payload["normalized_questions"],
            knowledge_tags=payload["knowledge_tags"],
        )

    def answer(self, question: str) -> AnswerCard:
        payload = self._llm.answer_question(question)
        return AnswerCard(
            question=payload["question"],
            answer=payload["answer"],
            why_asked=payload["why_asked"],
            answer_structure=payload["answer_structure"],
            follow_ups=payload["follow_ups"],
        )
```

- [ ] **步骤 4：再次运行增强层测试，确认通过**

Run:

```powershell
.venv\Scripts\python -m pytest tests/test_enricher.py -v
```

Expected:

```text
2 passed
```

- [ ] **步骤 5：提交增强层切片**

Run:

```powershell
git add src/xhs_agent/llm/client.py src/xhs_agent/llm/prompts.py src/xhs_agent/process/enricher.py tests/test_enricher.py
git commit -m "feat: add llm enrichment and answer generation"
```

## 任务 5：持久化帖子、题目去重和趋势统计

**Files:**
- Create: `src/xhs_agent/storage/db.py`
- Create: `src/xhs_agent/storage/repository.py`
- Create: `src/xhs_agent/process/dedupe.py`
- Create: `src/xhs_agent/process/stats.py`
- Test: `tests/test_repository_and_stats.py`

- [ ] **步骤 1：先写存储、去重、统计失败测试**

```python
# tests/test_repository_and_stats.py
from xhs_agent.process.dedupe import dedupe_questions
from xhs_agent.process.stats import build_tag_counts


def test_dedupe_questions_merges_simple_synonyms():
    questions = [
        "Redis 为什么快？",
        "为什么 Redis 这么快？",
        "MySQL 索引失效场景有哪些？",
    ]

    result = dedupe_questions(questions)

    assert result["Redis 为什么快？"] == 2
    assert result["MySQL 索引失效场景有哪些？"] == 1


def test_build_tag_counts_returns_descending_frequency():
    counts = build_tag_counts(
        [
            ["Redis", "缓存"],
            ["Redis", "MySQL"],
            ["MySQL"],
        ]
    )

    assert counts == [("Redis", 2), ("MySQL", 2), ("缓存", 1)]
```

- [ ] **步骤 2：运行存储和统计测试，确认失败**

Run:

```powershell
.venv\Scripts\python -m pytest tests/test_repository_and_stats.py -v
```

Expected:

```text
E   ModuleNotFoundError: No module named 'xhs_agent.process.dedupe'
```

- [ ] **步骤 3：实现 SQLite schema、Repository、去重和统计**

```python
# src/xhs_agent/storage/db.py
from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_posts (
    post_id TEXT PRIMARY KEY,
    target_date TEXT NOT NULL,
    title TEXT NOT NULL,
    body_text TEXT NOT NULL,
    category TEXT NOT NULL,
    company_name TEXT,
    round_name TEXT
);

CREATE TABLE IF NOT EXISTS normalized_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id TEXT NOT NULL,
    question_text TEXT NOT NULL,
    FOREIGN KEY(post_id) REFERENCES raw_posts(post_id)
);

CREATE TABLE IF NOT EXISTS knowledge_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id TEXT NOT NULL,
    tag TEXT NOT NULL,
    FOREIGN KEY(post_id) REFERENCES raw_posts(post_id)
);
"""


def connect(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.executescript(SCHEMA)
    return connection
```

```python
# src/xhs_agent/storage/repository.py
from __future__ import annotations

import sqlite3

from xhs_agent.process.enricher import EnrichedPost


class Repository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def save_post(self, target_date: str, post: EnrichedPost) -> None:
        self._connection.execute(
            """
            INSERT OR REPLACE INTO raw_posts (post_id, target_date, title, body_text, category, company_name, round_name)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                post.post_id,
                target_date,
                post.title,
                post.body_text,
                post.category,
                post.company_name,
                post.round_name,
            ),
        )
        self._connection.executemany(
            "INSERT INTO normalized_questions (post_id, question_text) VALUES (?, ?)",
            [(post.post_id, question) for question in post.normalized_questions],
        )
        self._connection.executemany(
            "INSERT INTO knowledge_tags (post_id, tag) VALUES (?, ?)",
            [(post.post_id, tag) for tag in post.knowledge_tags],
        )
        self._connection.commit()
```

```python
# src/xhs_agent/process/dedupe.py
from __future__ import annotations


def canonicalize(question: str) -> str:
    return question.replace("这么", "").replace("？", "?").replace(" ?", "?").strip()


def dedupe_questions(questions: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    aliases: dict[str, str] = {}
    for question in questions:
        key = canonicalize(question)
        canonical = aliases.setdefault(key, question)
        counts[canonical] = counts.get(canonical, 0) + 1
    return counts
```

```python
# src/xhs_agent/process/stats.py
from __future__ import annotations


def build_tag_counts(tag_lists: list[list[str]]) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for tags in tag_lists:
        for tag in tags:
            counts[tag] = counts.get(tag, 0) + 1
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))
```

- [ ] **步骤 4：再次运行存储和统计测试，确认通过**

Run:

```powershell
.venv\Scripts\python -m pytest tests/test_repository_and_stats.py -v
```

Expected:

```text
2 passed
```

- [ ] **步骤 5：提交存储和统计切片**

Run:

```powershell
git add src/xhs_agent/storage/db.py src/xhs_agent/storage/repository.py src/xhs_agent/process/dedupe.py src/xhs_agent/process/stats.py tests/test_repository_and_stats.py
git commit -m "feat: add storage and trend statistics"
```

## 任务 6：渲染日报并发布到飞书文档

**Files:**
- Create: `src/xhs_agent/report/render.py`
- Create: `src/xhs_agent/report/feishu.py`
- Test: `tests/test_report_render.py`

- [ ] **步骤 1：先写日报渲染失败测试**

```python
# tests/test_report_render.py
from xhs_agent.report.render import render_daily_report


def test_render_daily_report_contains_required_sections():
    report = render_daily_report(
        target_date="2026-04-08",
        top_posts=[
            {
                "company_name": "PDD",
                "round_name": "一面",
                "questions": ["项目怎么上线？", "Nginx 和 Spring Boot 如何通信？"],
            }
        ],
        top_tags=[("Redis", 2), ("MySQL", 2)],
        answered_questions=[
            {
                "question": "Redis 为什么快？",
                "answer": "先答内存访问，再答数据结构和线程模型。",
                "why_asked": "考察缓存原理基础。",
                "answer_structure": ["结论", "原理", "工程权衡"],
                "follow_ups": ["为什么单线程还能快？"],
            }
        ],
        trend_lines=["RAG 评测题开始升温"],
        observation_lines=["PDD 当天出现 2 篇相似面经"],
    )

    assert "4月8日 小红书后端 / AI 应用开发面经日报" in report
    assert "## 今日概览" in report
    assert "## 高频题目与标准回答" in report
```

- [ ] **步骤 2：运行日报渲染测试，确认失败**

Run:

```powershell
.venv\Scripts\python -m pytest tests/test_report_render.py -v
```

Expected:

```text
E   ModuleNotFoundError: No module named 'xhs_agent.report'
```

- [ ] **步骤 3：实现日报渲染器和飞书发布器**

```python
# src/xhs_agent/report/render.py
from __future__ import annotations


def render_daily_report(
    *,
    target_date: str,
    top_posts: list[dict],
    top_tags: list[tuple[str, int]],
    answered_questions: list[dict],
    trend_lines: list[str],
    observation_lines: list[str],
) -> str:
    month, day = target_date.split("-")[1:]
    lines = [
        f"# {int(month)}月{int(day)}日 小红书后端 / AI 应用开发面经日报",
        "",
        "## 今日概览",
        f"- 入选重点面经：{len(top_posts)}",
        f"- 入选重点题目：{len(answered_questions)}",
        "",
        "## 最新面经",
    ]
    for item in top_posts:
        lines.append(f"- {item['company_name']} {item['round_name']}：{'；'.join(item['questions'])}")
    lines.extend(["", "## 高频知识点"])
    for tag, count in top_tags:
        lines.append(f"- {tag} x {count}")
    lines.extend(["", "## 高频题目与标准回答"])
    for item in answered_questions:
        lines.append(f"### {item['question']}")
        lines.append(f"- 标准回答：{item['answer']}")
        lines.append(f"- 考察点：{item['why_asked']}")
        lines.append(f"- 回答结构：{' / '.join(item['answer_structure'])}")
        lines.append(f"- 常见追问：{'；'.join(item['follow_ups'])}")
    lines.extend(["", "## 趋势变化"])
    lines.extend(f"- {line}" for line in trend_lines)
    lines.extend(["", "## 重点观察"])
    lines.extend(f"- {line}" for line in observation_lines)
    return "\n".join(lines)
```

```python
# src/xhs_agent/report/feishu.py
from __future__ import annotations

import httpx


class FeishuDocPublisher:
    def __init__(self, app_id: str, app_secret: str) -> None:
        self._app_id = app_id
        self._app_secret = app_secret

    def _tenant_access_token(self) -> str:
        response = httpx.post(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": self._app_id, "app_secret": self._app_secret},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["tenant_access_token"]

    def publish_markdown(self, title: str, markdown: str) -> dict:
        token = self._tenant_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        response = httpx.post(
            "https://open.feishu.cn/open-apis/docx/v1/documents",
            headers=headers,
            json={"title": title},
            timeout=30,
        )
        response.raise_for_status()
        document_id = response.json()["data"]["document"]["document_id"]
        block_response = httpx.post(
            f"https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}/blocks/{document_id}/children",
            headers=headers,
            json={
                "children": [
                    {
                        "block_type": 2,
                        "paragraph": {
                            "elements": [
                                {
                                    "text_run": {
                                        "content": markdown,
                                    }
                                }
                            ]
                        },
                    }
                ]
            },
            timeout=30,
        )
        block_response.raise_for_status()
        return {"document_id": document_id}
```

- [ ] **步骤 4：再次运行日报渲染测试，确认通过**

Run:

```powershell
.venv\Scripts\python -m pytest tests/test_report_render.py -v
```

Expected:

```text
1 passed
```

- [ ] **步骤 5：提交日报输出切片**

Run:

```powershell
git add src/xhs_agent/report/render.py src/xhs_agent/report/feishu.py tests/test_report_render.py
git commit -m "feat: add report rendering and feishu publisher"
```

## 任务 7：接入日报 Runner 和 CLI 入口

**Files:**
- Create: `src/xhs_agent/runner.py`
- Create: `src/xhs_agent/cli.py`
- Test: `tests/test_runner.py`
- Modify: `README.md`

- [ ] **步骤 1：先写按前一天窗口运行的失败测试**

```python
# tests/test_runner.py
from xhs_agent.runner import DailyRunner


class FakeCrawler:
    def fetch_posts_for_date(self, target_date: str):
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
```

- [ ] **步骤 2：运行 runner 测试，确认失败**

Run:

```powershell
.venv\Scripts\python -m pytest tests/test_runner.py -v
```

Expected:

```text
E   ModuleNotFoundError: No module named 'xhs_agent.runner'
```

- [ ] **步骤 3：实现 runner 和 CLI 基础入口**

```python
# src/xhs_agent/runner.py
from __future__ import annotations

from xhs_agent.config import build_target_window


class DailyRunner:
    def __init__(self, crawler, pipeline, timezone_name: str = "Asia/Shanghai") -> None:
        self._crawler = crawler
        self._pipeline = pipeline
        self._timezone_name = timezone_name

    def run(self, run_date: str) -> dict:
        _, _, target_date = build_target_window(self._timezone_name, run_date)
        posts = self._crawler.fetch_posts_for_date(target_date)
        result = self._pipeline.process_posts(posts, target_date)
        result["target_date"] = target_date
        return result
```

```python
# src/xhs_agent/cli.py
from __future__ import annotations

import argparse

from xhs_agent.config import Settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["run-daily"])
    parser.add_argument("--run-date", required=True)
    return parser


def main() -> None:
    _ = Settings()
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "run-daily":
        print(f"Run daily pipeline for {args.run_date}")


if __name__ == "__main__":
    main()
```

```markdown
# README.md

## Local Run

```powershell
.venv\Scripts\python -m xhs_agent.cli run-daily --run-date 2026-04-09
```

## Scheduling

Use Windows Task Scheduler to run the command every day at 00:10 local time and let the report publish after the pipeline completes.
```

- [ ] **步骤 4：再次运行 runner 测试，确认通过**

Run:

```powershell
.venv\Scripts\python -m pytest tests/test_runner.py -v
```

Expected:

```text
1 passed
```

- [ ] **步骤 5：运行完整测试集**

Run:

```powershell
.venv\Scripts\python -m pytest -v
```

Expected:

```text
All tests pass
```

- [ ] **步骤 6：提交 runner 基础切片**

Run:

```powershell
git add src/xhs_agent/runner.py src/xhs_agent/cli.py README.md tests/test_runner.py
git commit -m "feat: add daily runner and cli entry point"
```

## 任务 8：把纵向切片接成真实流水线

**Files:**
- Create: `src/xhs_agent/state.py`
- Create: `src/xhs_agent/orchestration/orchestrator.py`
- Create: `src/xhs_agent/nodes/crawl_node.py`
- Create: `src/xhs_agent/nodes/extract_node.py`
- Create: `src/xhs_agent/nodes/classify_node.py`
- Create: `src/xhs_agent/nodes/answer_node.py`
- Create: `src/xhs_agent/nodes/report_node.py`
- Modify: `src/xhs_agent/storage/repository.py`
- Modify: `src/xhs_agent/report/feishu.py`
- Modify: `src/xhs_agent/runner.py`
- Modify: `src/xhs_agent/cli.py`
- Test: `tests/test_runner.py`

- [ ] **步骤 1：扩展 runner 测试，覆盖按需 OCR 和部分失败标记**

```python
def test_daily_runner_marks_partial_failure_when_answer_generation_fails():
    class BrokenPipeline:
        def process_posts(self, posts, target_date):
            return {
                "top_posts": [],
                "top_tags": [],
                "answered_questions": [],
                "trend_lines": [],
                "observation_lines": [],
                "warnings": ["answer_generation_failed"],
            }

    result = DailyRunner(FakeCrawler(), BrokenPipeline()).run(run_date="2026-04-09")

    assert result["target_date"] == "2026-04-08"
    assert result["warnings"] == ["answer_generation_failed"]
```

- [ ] **步骤 2：运行 runner 测试，确认新增场景失败**

Run:

```powershell
.venv\Scripts\python -m pytest tests/test_runner.py -v
```

Expected:

```text
E   KeyError or AssertionError for missing warnings
```

- [ ] **步骤 3：实现集成后的流水线行为**

```python
# src/xhs_agent/state.py
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class DailyJobState:
    target_date: str
    raw_posts: list[dict] = field(default_factory=list)
    extracted_posts: list[dict] = field(default_factory=list)
    enriched_posts: list = field(default_factory=list)
    answer_cards: list[dict] = field(default_factory=list)
    top_posts: list[dict] = field(default_factory=list)
    top_tags: list[tuple[str, int]] = field(default_factory=list)
    trend_lines: list[str] = field(default_factory=list)
    observation_lines: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    report_markdown: str = ""
```

```python
# src/xhs_agent/nodes/crawl_node.py
from __future__ import annotations


class CrawlNode:
    def __init__(self, browser) -> None:
        self._browser = browser

    def run(self, state) -> None:
        state.raw_posts = []
```

```python
# src/xhs_agent/nodes/extract_node.py
from __future__ import annotations

from xhs_agent.extract.line_questions import extract_question_lines, should_run_ocr


class ExtractNode:
    def __init__(self, ocr) -> None:
        self._ocr = ocr

    def run(self, state) -> None:
        extracted = []
        for item in state.raw_posts:
            question_lines = extract_question_lines(item["body_text"])
            if should_run_ocr(question_lines) and item.get("image_text"):
                question_lines = extract_question_lines(item["image_text"])
            if question_lines:
                extracted.append({**item, "question_lines": question_lines})
        state.extracted_posts = extracted
```

```python
# src/xhs_agent/nodes/classify_node.py
from __future__ import annotations

from xhs_agent.crawl.candidate_filter import is_candidate_post
from xhs_agent.crawl.html_extract import extract_post_detail


class ClassifyNode:
    def __init__(self, enricher, repository) -> None:
        self._enricher = enricher
        self._repository = repository

    def run(self, state) -> None:
        enriched_posts = []
        top_posts = []
        top_tags = []
        for item in state.extracted_posts:
            if not is_candidate_post(item["title"], item["body_text"]):
                continue
            enriched = self._enricher.enrich(
                extract_post_detail(
                    f"<div class='title'>{item['title']}</div><div class='content'>{''.join(f'<p>{q}</p>' for q in item['question_lines'])}</div>"
                ),
                post_questions=item["question_lines"],
            )
            self._repository.save_post(state.target_date, enriched)
            enriched_posts.append(enriched)
            top_posts.append(
                {
                    "company_name": enriched.company_name,
                    "round_name": enriched.round_name,
                    "questions": enriched.normalized_questions[:3],
                }
            )
            top_tags.extend((tag, 1) for tag in enriched.knowledge_tags)
        state.enriched_posts = enriched_posts
        state.top_posts = top_posts
        state.top_tags = top_tags
```

```python
# src/xhs_agent/nodes/answer_node.py
from __future__ import annotations


class AnswerNode:
    def __init__(self, enricher) -> None:
        self._enricher = enricher

    def run(self, state) -> None:
        answer_cards = []
        for enriched in state.enriched_posts:
            try:
                for question in enriched.normalized_questions[:2]:
                    card = self._enricher.answer(question)
                    answer_cards.append(
                        {
                            "question": card.question,
                            "answer": card.answer,
                            "why_asked": card.why_asked,
                            "answer_structure": card.answer_structure,
                            "follow_ups": card.follow_ups,
                        }
                    )
            except Exception:
                state.warnings.append("answer_generation_failed")
        state.answer_cards = answer_cards
```

```python
# src/xhs_agent/nodes/report_node.py
from __future__ import annotations

from xhs_agent.report.render import render_daily_report


class ReportNode:
    def run(self, state) -> None:
        state.report_markdown = render_daily_report(
            target_date=state.target_date,
            top_posts=state.top_posts,
            top_tags=state.top_tags,
            answered_questions=state.answer_cards,
            trend_lines=state.trend_lines,
            observation_lines=state.observation_lines,
        )
```

```python
# src/xhs_agent/orchestration/orchestrator.py
from __future__ import annotations

from xhs_agent.state import DailyJobState


class DailyOrchestrator:
    def __init__(self, crawl_node, extract_node, classify_node, answer_node, report_node) -> None:
        self._crawl_node = crawl_node
        self._extract_node = extract_node
        self._classify_node = classify_node
        self._answer_node = answer_node
        self._report_node = report_node

    def fetch_posts_for_date(self, target_date: str) -> list[dict]:
        state = DailyJobState(target_date=target_date)
        self._crawl_node.run(state)
        return state.raw_posts

    def process_posts(self, posts: list[dict], target_date: str) -> dict:
        state = DailyJobState(target_date=target_date, raw_posts=posts)
        self._extract_node.run(state)
        self._classify_node.run(state)
        self._answer_node.run(state)
        self._report_node.run(state)
        return {
            "top_posts": state.top_posts,
            "top_tags": state.top_tags,
            "answered_questions": state.answer_cards,
            "trend_lines": state.trend_lines,
            "observation_lines": state.observation_lines,
            "warnings": state.warnings,
            "markdown": state.report_markdown,
        }
```

```python
# src/xhs_agent/runner.py
from __future__ import annotations

from xhs_agent.config import build_target_window
from xhs_agent.report.render import render_daily_report


class DailyRunner:
    def __init__(self, crawler, pipeline, publisher=None, timezone_name: str = "Asia/Shanghai") -> None:
        self._crawler = crawler
        self._pipeline = pipeline
        self._publisher = publisher
        self._timezone_name = timezone_name

    def run(self, run_date: str) -> dict:
        _, _, target_date = build_target_window(self._timezone_name, run_date)
        posts = self._crawler.fetch_posts_for_date(target_date)
        result = self._pipeline.process_posts(posts, target_date)
        markdown = render_daily_report(
            target_date=target_date,
            top_posts=result["top_posts"],
            top_tags=result["top_tags"],
            answered_questions=result["answered_questions"],
            trend_lines=result["trend_lines"],
            observation_lines=result["observation_lines"],
        )
        result["target_date"] = target_date
        result["markdown"] = markdown
        result.setdefault("warnings", [])
        if self._publisher is not None:
            self._publisher.publish_markdown(
                title=f"{target_date} 小红书后端 / AI 应用开发面经日报",
                markdown=markdown,
            )
        return result
```

```python
# src/xhs_agent/cli.py
from __future__ import annotations

import argparse

from xhs_agent.crawl.browser import BrowserSession
from xhs_agent.config import Settings
from xhs_agent.llm.client import LlmClient
from xhs_agent.ocr.image_ocr import ImageOcr
from xhs_agent.process.enricher import Enricher
from xhs_agent.nodes.answer_node import AnswerNode
from xhs_agent.nodes.classify_node import ClassifyNode
from xhs_agent.nodes.crawl_node import CrawlNode
from xhs_agent.nodes.extract_node import ExtractNode
from xhs_agent.nodes.report_node import ReportNode
from xhs_agent.orchestration.orchestrator import DailyOrchestrator
from xhs_agent.report.feishu import FeishuDocPublisher
from xhs_agent.runner import DailyRunner
from xhs_agent.storage.db import connect
from xhs_agent.storage.repository import Repository


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["run-daily"])
    parser.add_argument("--run-date", required=True)
    return parser


def main() -> None:
    settings = Settings()
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "run-daily":
        browser = BrowserSession(settings.xhs_storage_state_path)
        llm = LlmClient(settings.openai_api_key)
        repository = Repository(connect("data/xhs_agent.db"))
        enricher = Enricher(llm)
        orchestrator = DailyOrchestrator(
            crawl_node=CrawlNode(browser),
            extract_node=ExtractNode(ImageOcr()),
            classify_node=ClassifyNode(enricher, repository),
            answer_node=AnswerNode(enricher),
            report_node=ReportNode(),
        )
        publisher = FeishuDocPublisher(settings.feishu_app_id, settings.feishu_app_secret)
        runner = DailyRunner(crawler=orchestrator, pipeline=orchestrator, publisher=publisher)
        runner.run(run_date=args.run_date)
```

- [ ] **步骤 4：运行 runner 测试，再运行完整测试集**

Run:

```powershell
.venv\Scripts\python -m pytest tests/test_runner.py -v
.venv\Scripts\python -m pytest -v
```

Expected:

```text
All tests pass
```

- [ ] **步骤 5：提交完整流水线接线**

Run:

```powershell
git add src/xhs_agent/state.py src/xhs_agent/orchestration/orchestrator.py src/xhs_agent/nodes/crawl_node.py src/xhs_agent/nodes/extract_node.py src/xhs_agent/nodes/classify_node.py src/xhs_agent/nodes/answer_node.py src/xhs_agent/nodes/report_node.py src/xhs_agent/runner.py src/xhs_agent/cli.py src/xhs_agent/report/feishu.py tests/test_runner.py
git commit -m "feat: integrate daily report pipeline"
```
