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
- Create: `src/xhs_agent/nodes/question_select_node.py`
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

- [ ] **步骤 1：先写题目提取失败测试，覆盖有编号、无编号、明显非题行排除**

```python
# tests/test_line_questions.py
from xhs_agent.extract.line_questions import split_to_candidate_lines, should_run_ocr


def test_split_to_candidate_lines_handles_numbered_and_plain_lines():
    body = """PDD服务端一面

1. 项目怎么上线，怎么部署
2. nginx 和 springboot 如何通信
手撕：数组按 k 分组
MySQL 索引原理
字数 1024
点赞 32"""

    result = split_to_candidate_lines(body)
    assert "项目怎么上线，怎么部署" in result
    assert "nginx 和 springboot 如何通信" in result
    assert "手撕：数组按 k 分组" in result
    assert "MySQL 索引原理" in result
    # 元数据行不应出现在候选行中
    assert not any("字数" in line for line in result)
    assert not any("点赞" in line for line in result)


def test_split_to_candidate_lines_filters_too_short_and_too_long():
    body = "A\nRedis\n非常" + "长" * 300
    result = split_to_candidate_lines(body)
    assert "Redis" not in result  # 太短
    assert not any(len(line) > 200 for line in result)


def test_should_run_ocr_only_when_no_candidate_lines():
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

NUMBER_PREFIX_RE = re.compile(r"^\s*(?:\d+[.)、]|[一二三四五六七八九十]+[、.]|\(\d+\))\s*")

# 规则负责快速排除明显非题目的行，LLM 负责最终判定和标准化
_NOT_A_QUESTION_PATTERN = re.compile(
    r"^(\d{4}年|字数|阅读|点赞|收藏|分享|发布于|来自|"
    r"iOS|Android|客户端|iPhone|编辑于|已编辑)",
)


def normalize_question_line(line: str) -> str:
    line = NUMBER_PREFIX_RE.sub("", line.strip())
    return re.sub(r"\s+", " ", line)


def split_to_candidate_lines(body: str) -> list[str]:
    """把正文按换行切分为候选行（仅做最粗的噪音剔除），不做题目判定。"""
    lines = [normalize_question_line(raw) for raw in body.splitlines()]
    return [
        line
        for line in lines
        if line
        and len(line) >= 4
        and len(line) <= 200
        and not _NOT_A_QUESTION_PATTERN.match(line)
    ]


def should_run_ocr(question_lines: list[str]) -> bool:
    return len(question_lines) == 0
```

```python
# src/xhs_agent/ocr/image_ocr.py
from __future__ import annotations

from pathlib import Path

import httpx
from rapidocr_onnxruntime import RapidOCR


class ImageOcr:
    def __init__(self, cache_dir: str = ".cache/xhs-images") -> None:
        self._engine = RapidOCR()
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def download_image(self, url: str, name: str) -> str:
        suffix = Path(url.split("?")[0]).suffix or ".jpg"
        path = self._cache_dir / f"{name}{suffix}"
        response = httpx.get(url, timeout=20)
        response.raise_for_status()
        path.write_bytes(response.content)
        return str(path)

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
from xhs_agent.crawl.candidate_filter import is_candidate_post, hard_excluded, has_recall_signal


def test_candidate_filter_accepts_backend_interview_titles():
    assert is_candidate_post("PDD服务端一面", "项目怎么上线\nnginx和springboot如何通信")


def test_candidate_filter_accepts_ai_agent_interview_titles():
    assert is_candidate_post("AI应用开发一面", "RAG召回链路\nAgent tool calling")


def test_candidate_filter_rejects_excluded_targets():
    assert is_candidate_post("Golang 面试 一面", "项目介绍") is False
    assert is_candidate_post("C++面经", "手撕题") is False


def test_candidate_filter_no_false_positive_on_go_substring():
    # "mongodb" 中包含 "go" 不应触发误杀
    assert hard_excluded("后端面经", "MongoDB 索引原理") is False
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

import re

# 使用正则确保排除词匹配的是独立词，避免子串误杀（如 "mongodb" 匹配 "go"）
EXCLUDED_PATTERNS = (
    re.compile(r"\bgolang\b", re.IGNORECASE),
    re.compile(r"\bgo\b.*\b面试\b", re.IGNORECASE),      # "go 面试" 类标题
    re.compile(r"\bgolang\b.*\b面经\b", re.IGNORECASE),
    re.compile(r"\bc\+\+\b", re.IGNORECASE),
    re.compile(r"前端"),
    re.compile(r"产品经理"),
    re.compile(r"运营"),
)

RECALL_TOKENS = (
    "后端", "服务端", "java", "面经", "一面", "二面", "终面", "手撕",
    "redis", "mysql", "jvm", "rag", "agent", "llm", "mcp",
    "面试", "面试官", "八股", "校招", "社招",
)


def hard_excluded(title: str, body_text: str) -> bool:
    """第一级硬排除：文本是否明确属于非目标岗位。"""
    haystack = f"{title}\n{body_text}"
    return any(pattern.search(haystack) for pattern in EXCLUDED_PATTERNS)


def has_recall_signal(title: str, body_text: str) -> bool:
    """文本是否包含至少一个召回信号（关键词或面试信号词）。"""
    haystack = f"{title}\n{body_text}".lower()
    return any(token in haystack for token in RECALL_TOKENS)


def is_candidate_post(title: str, preview_text: str) -> bool:
    """组合判定：先排除，再检查信号。"""
    if hard_excluded(title, preview_text):
        return False
    return has_recall_signal(title, preview_text)
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

import re
import time
from pathlib import Path
from urllib.parse import quote

from playwright.sync_api import Page, sync_playwright


class BrowserSession:
    """维护单个浏览器实例和登录态，支持搜索、翻页、打开详情页。"""

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
        """搜索关键词并返回帖子 URL 列表（已去重）。"""
        page = self._new_page()
        url = self.SEARCH_URL.format(keyword=quote(keyword))
        page.goto(url, wait_until="networkidle", timeout=30000)
        time.sleep(2)  # 等待动态内容渲染

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
        """打开帖子详情页并返回完整 HTML。"""
        page = self._new_page()
        page.goto(post_url, wait_until="networkidle", timeout=30000)
        time.sleep(1)
        html = page.content()
        page.close()
        return html

    def extract_publish_time(self, html: str) -> str | None:
        """从详情页 HTML 中提取发布时间字符串。"""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        time_meta = soup.select_one('meta[itemprop="datePublished"]')
        if time_meta:
            return time_meta.get("content")
        # 备选：匹配页面中的时间文本
        match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})', html)
        return match.group(1) if match else None

    def verify_login(self) -> bool:
        """检查登录态是否仍然有效。"""
        page = self._new_page()
        page.goto("https://www.xiaohongshu.com", wait_until="networkidle", timeout=15000)
        html = page.content()
        page.close()
        # 未登录时页面标题不包含用户相关元素
        return "login" not in html.lower()[:2000] and "验证" not in html[:2000]
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

from xhs_agent.llm.prompts import (
    ANSWER_PROMPT,
    CLASSIFY_AND_ENRICH_PROMPT,
    EXTRACT_QUESTIONS_PROMPT,
)


class LlmClient:
    def __init__(self, api_key: str, model: str = "gpt-5.2") -> None:
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def _call_json(self, system_prompt: str, user_input: str) -> dict:
        response = self._client.responses.create(
            model=self._model,
            instructions=system_prompt,
            input=user_input,
            text={"format": {"type": "json_object"}},
        )
        return json.loads(response.output_text)

    def extract_questions(self, candidate_lines: list[str]) -> list[str]:
        if not candidate_lines:
            return []
        payload = self._call_json(
            EXTRACT_QUESTIONS_PROMPT,
            "\n".join(f"- {line}" for line in candidate_lines),
        )
        return payload.get("questions", [])

    def classify_and_enrich(self, title: str, questions: list[str]) -> dict:
        user_input = f"Title: {title}\nQuestions:\n" + "\n".join(f"- {q}" for q in questions)
        return self._call_json(CLASSIFY_AND_ENRICH_PROMPT, user_input)

    def answer_question(self, question: str) -> dict:
        return self._call_json(ANSWER_PROMPT, question)
```

```python
# src/xhs_agent/llm/prompts.py
EXTRACT_QUESTIONS_PROMPT = """
You are extracting interview questions from Xiaohongshu posts.

Given a list of candidate lines from a post body, return ONLY the lines that are interview questions.
Interview questions include:
- Technical questions (e.g. "MySQL 索引原理", "缓存穿透怎么解决", "手撕：LRU")
- Coding tasks (e.g. "编程题：实现 LRU 缓存", "手撕：数组按 k 分组")
- Scenario/design questions (e.g. "设计一个短链接系统", "秒杀系统怎么设计")
- Behavioral and project questions (e.g. "项目怎么上线部署", "介绍你做过的最有挑战的项目")
- Question-like statements (e.g. "nginx 和 springboot 如何通信", "Redis 为什么快")

NOT interview questions:
- Post titles and metadata (e.g. "PDD 服务端一面", "2024 校招", "base 上海")
- Sentiment or summary statements (e.g. "今天面试不太难", "HR 说一周内给结果")
- Single-word topics without context (e.g. "Redis", "八股")

Return a JSON object with a single field "questions" containing the extracted question lines.
If no questions found, return {"questions": []}.
"""

CLASSIFY_AND_ENRICH_PROMPT = """
You classify Xiaohongshu interview posts and extract structured information.

Allowed categories: "backend", "ai_agent", "reject".

Reject if the post is primarily about: Go, Golang, C++, front-end, PM, operations.
Only use facts present in the title and extracted question lines.
Never invent company names, rounds, or topics that are not explicitly mentioned.

Return JSON:
{
  "category": "backend" | "ai_agent" | "reject",
  "company_name": "company name or empty string",
  "round_name": "e.g. 一面, 二面, 三面, 终面, HR面, or empty string",
  "normalized_questions": ["question 1", "question 2"],
  "knowledge_tags": ["tag1", "tag2"]
}

When normalizing questions:
- Expand abbreviations (db→数据库, mq→消息队列)
- Fix obvious typos
- Keep the original meaning intact
- If a question is too vague to understand, mark it "[ambiguous] question text"

Tags should be specific technical topics: e.g. "MySQL", "Redis", "RAG", "缓存", "分布式", "Spring"
"""

ANSWER_PROMPT = """
You are writing a standard interview answer in Chinese. 

Provide an answer that:
- Leads with the key conclusion first (30-50 words)
- Explains the core principle or approach (80-150 words)
- Covers practical considerations and trade-offs where relevant
- Ends with a brief summary

The answer should be concise enough to recite in 3-5 minutes in an interview, but detailed enough to demonstrate deep understanding.

Return JSON:
{
  "question": "original question",
  "answer": "complete answer in Chinese",
  "why_asked": "what the interviewer is testing with this question",
  "answer_structure": ["step1", "step2", "step3"],
  "follow_ups": ["common follow-up question 1", "follow-up question 2"]
}
"""

```python
# src/xhs_agent/process/enricher.py
from __future__ import annotations

from dataclasses import dataclass, field

from xhs_agent.crawl.candidate_filter import hard_excluded
from xhs_agent.models import RawPost


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
        return not hard_excluded(post.title, post.body_text)

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
from datetime import date, timedelta
from xhs_agent.process.stats import build_tag_counts, compute_trend_lines


def test_build_tag_counts_returns_descending_frequency():
    counts = build_tag_counts(
        [
            ["Redis", "缓存"],
            ["Redis", "MySQL"],
            ["MySQL"],
        ]
    )

    assert counts == [("Redis", 2), ("MySQL", 2), ("缓存", 1)]


def test_compute_trend_lines_detects_surge():
    target = (date.today() - timedelta(days=1)).isoformat()

    class FakeRepo:
        def tag_counts_for_date_range(self, start, end):
            # 历史 7 天中 RAG 总量为 6，日均 ~1
            return {"2026-04-01": [("RAG", 1)], "2026-04-02": [("RAG", 2)], "2026-04-03": [("RAG", 0)],
                    "2026-04-04": [("RAG", 1)], "2026-04-05": [("RAG", 1)], "2026-04-06": [("RAG", 1)]}

    current = [("RAG", 5), ("Redis", 3)]
    lines = compute_trend_lines(target, current, FakeRepo())

    # RAG 当天 5 次，历史日均 ~1 → 应该被检测为升温
    assert any("RAG" in line for line in lines)
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
    target_date TEXT NOT NULL,
    question_text TEXT NOT NULL,
    UNIQUE(post_id, question_text),
    FOREIGN KEY(post_id) REFERENCES raw_posts(post_id)
);

CREATE TABLE IF NOT EXISTS knowledge_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id TEXT NOT NULL,
    target_date TEXT NOT NULL,
    tag TEXT NOT NULL,
    UNIQUE(post_id, tag),
    FOREIGN KEY(post_id) REFERENCES raw_posts(post_id)
);

CREATE TABLE IF NOT EXISTS daily_snapshots (
    target_date TEXT PRIMARY KEY,
    candidate_count INTEGER NOT NULL,
    valid_count INTEGER NOT NULL,
    question_count INTEGER NOT NULL,
    top_tags_json TEXT NOT NULL DEFAULT '[]',
    top_questions_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_questions_date ON normalized_questions(target_date);
CREATE INDEX IF NOT EXISTS idx_tags_date ON knowledge_tags(target_date);
CREATE INDEX IF NOT EXISTS idx_posts_date ON raw_posts(target_date);
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

import json
import sqlite3

from xhs_agent.process.enricher import EnrichedPost


class Repository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    # ---------- 写入 ----------

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
            "INSERT OR IGNORE INTO normalized_questions (post_id, target_date, question_text) VALUES (?, ?, ?)",
            [(post.post_id, target_date, question) for question in post.normalized_questions],
        )
        self._connection.executemany(
            "INSERT OR IGNORE INTO knowledge_tags (post_id, target_date, tag) VALUES (?, ?, ?)",
            [(post.post_id, target_date, tag) for tag in post.knowledge_tags],
        )
        self._connection.commit()

    def save_daily_snapshot(
        self, target_date: str, candidate_count: int, valid_count: int,
        question_count: int, top_tags: list[tuple[str, int]], top_questions: list[str],
    ) -> None:
        self._connection.execute(
            """
            INSERT OR REPLACE INTO daily_snapshots (target_date, candidate_count, valid_count, question_count, top_tags_json, top_questions_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (target_date, candidate_count, valid_count, question_count, json.dumps(top_tags), json.dumps(top_questions)),
        )
        self._connection.commit()

    # ---------- 当日查询 ----------

    def count_posts_for_date(self, target_date: str) -> int:
        row = self._connection.execute(
            "SELECT COUNT(*) FROM raw_posts WHERE target_date = ?", (target_date,)
        ).fetchone()
        return row[0] if row else 0

    def count_questions_for_date(self, target_date: str) -> int:
        row = self._connection.execute(
            "SELECT COUNT(*) FROM normalized_questions WHERE target_date = ?", (target_date,)
        ).fetchone()
        return row[0] if row else 0

    def tag_counts_for_date(self, target_date: str) -> list[tuple[str, int]]:
        rows = self._connection.execute(
            """
            SELECT tag, COUNT(*) as cnt FROM knowledge_tags
            WHERE target_date = ?
            GROUP BY tag ORDER BY cnt DESC, tag ASC
            """,
            (target_date,),
        ).fetchall()
        return [(row[0], row[1]) for row in rows]

    # ---------- 跨天趋势查询 ----------

    def tag_counts_for_date_range(self, start_date: str, end_date: str) -> dict[str, list[tuple[str, int]]]:
        """返回 {日期: [(tag, count), ...]} 供趋势分析使用。"""
        rows = self._connection.execute(
            """
            SELECT target_date, tag, COUNT(*) as cnt FROM knowledge_tags
            WHERE target_date >= ? AND target_date <= ?
            GROUP BY target_date, tag ORDER BY target_date DESC, cnt DESC
            """,
            (start_date, end_date),
        ).fetchall()
        result: dict[str, list[tuple[str, int]]] = {}
        for date, tag, cnt in rows:
            result.setdefault(date, []).append((tag, cnt))
        return result

    def question_counts_for_date_range(self, start_date: str, end_date: str) -> dict[str, int]:
        rows = self._connection.execute(
            """
            SELECT target_date, COUNT(*) FROM normalized_questions
            WHERE target_date >= ? AND target_date <= ?
            GROUP BY target_date
            """,
            (start_date, end_date),
        ).fetchall()
        return {row[0]: row[1] for row in rows}

    def post_company_summary_for_date(self, target_date: str) -> list[tuple[str, int]]:
        """统计当天每家公司的帖子数，用于重点观察中的异常检测。"""
        rows = self._connection.execute(
            """
            SELECT company_name, COUNT(*) FROM raw_posts
            WHERE target_date = ? AND company_name IS NOT NULL AND company_name != ''
            GROUP BY company_name ORDER BY COUNT(*) DESC
            """,
            (target_date,),
        ).fetchall()
        return [(row[0], row[1]) for row in rows]
```

```python
# src/xhs_agent/process/dedupe.py
from __future__ import annotations

import json


DEDUPE_PROMPT = """
You are merging near-duplicate interview questions.

Given a list of questions, group questions that ask the same thing (even if phrased differently) and pick the best representative text for each group.

Examples of questions that should be merged:
- "Redis 为什么快" and "为什么 Redis 这么快" → same question
- "MySQL 索引失效场景有哪些" and "哪些情况会导致 MySQL 索引失效" → same question
- "缓存和 DB 一致性怎么保证" and "如何保证缓存与数据库的一致性" → same question
- "RAG 召回怎么优化" and "怎么提升 RAG 的召回效果" → same question

Examples that should NOT be merged:
- "Redis 为什么快" and "Redis 持久化机制" → different topics
- "MySQL 索引原理" and "MySQL 索引失效场景" → related but different questions

Return JSON with a single field "groups" — a list of groups, each with:
- "representative": the best representative text for the group
- "count": how many questions are in the group
- "members": list of all questions in the group

Input:
"""


def dedupe_questions(questions: list[str], llm_client) -> dict[str, int]:
    """使用 LLM 语义去重，返回 {代表题目: 出现次数}。"""
    if len(questions) <= 1:
        return {q: 1 for q in questions}

    user_input = "\n".join(f"- {q}" for q in questions)
    try:
        response = llm_client._client.responses.create(
            model=llm_client._model,
            instructions=DEDUPE_PROMPT,
            input=user_input,
            text={"format": {"type": "json_object"}},
        )
        payload = json.loads(response.output_text)
        return {
            group["representative"]: group["count"]
            for group in payload.get("groups", [])
        }
    except Exception:
        # 降级：简单计数
        counts: dict[str, int] = {}
        for q in questions:
            counts[q] = counts.get(q, 0) + 1
        return counts
```

```python
# src/xhs_agent/process/stats.py
from __future__ import annotations

from datetime import date, timedelta


def build_tag_counts(tag_lists: list[list[str]]) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for tags in tag_lists:
        for tag in tags:
            counts[tag] = counts.get(tag, 0) + 1
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def compute_trend_lines(
    target_date: str,
    current_tags: list[tuple[str, int]],
    repository,
) -> list[str]:
    """对比近 7 天历史，发现升温知识点，返回趋势描述行列表。"""
    try:
        end = date.fromisoformat(target_date)
        start = end - timedelta(days=7)
        history = repository.tag_counts_for_date_range(start.isoformat(), end.isoformat())

        # 合并历史计数
        historical_counts: dict[str, int] = {}
        for day_tags in history.values():
            for tag, cnt in day_tags:
                historical_counts[tag] = historical_counts.get(tag, 0) + cnt

        trend_lines = []
        current_map = dict(current_tags)
        for tag, today_cnt in current_tags[:10]:
            hist_cnt = historical_counts.get(tag, 0)
            # 去掉当天后算日均
            avg = max(hist_cnt - today_cnt, 0) / max(len(history) - 1, 1)
            if avg > 0 and today_cnt > avg * 1.5:
                trend_lines.append(f"{tag} 当天出现 {today_cnt} 次，高于近 7 天日均 {avg:.1f} 次")

        # AI/Agent 题占比变化
        ai_tags = {"RAG", "Agent", "LLM", "MCP", "Prompt", "Function Calling", "向量数据库", "Embedding", "Tool Calling", "Memory", "工作流", "评测", "观测"}
        today_ai = sum(cnt for tag, cnt in current_tags if tag in ai_tags)
        today_total = sum(cnt for _, cnt in current_tags)
        hist_ai = sum(cnt for tag, cnt in historical_counts.items() if tag in ai_tags)
        hist_total = sum(historical_counts.values())
        if today_total > 0 and hist_total > 0:
            today_ratio = today_ai / today_total * 100
            hist_ratio = hist_ai / hist_total * 100
            if today_ratio > hist_ratio + 5:
                trend_lines.append(f"AI/Agent 相关题占比 {today_ratio:.0f}%，较近 7 天均值 {hist_ratio:.0f}% 明显上升")

        return trend_lines
    except Exception:
        return []


def compute_observation_lines(
    target_date: str,
    company_summary: list[tuple[str, int]],
    current_tags: list[tuple[str, int]],
    repository,
) -> list[str]:
    """生成重点观察结论。"""
    lines = []

    # 某公司当天出现多篇面经
    for company, cnt in company_summary[:5]:
        if cnt >= 2:
            lines.append(f"{company} 当天出现 {cnt} 篇面经")

    # 尝试检测连续天数高频
    try:
        tag_set = {tag for tag, _ in current_tags[:8]}
        end = date.fromisoformat(target_date)
        start = end - timedelta(days=3)
        recent = repository.tag_counts_for_date_range(start.isoformat(), end.isoformat())
        for tag in tag_set:
            days_seen = sum(1 for day_tags in recent.values() if tag in dict(day_tags))
            if days_seen >= 3:
                lines.append(f"{tag} 连续 {days_seen} 天高频出现")
                break
    except Exception:
        pass

    return lines[:5]  # 最多 5 条
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
        candidate_count=15,
        valid_count=5,
    )

    assert "4月8日 小红书后端 / AI 应用开发面经日报" in report
    assert "## 今日概览" in report
    assert "## 高频题目与标准回答" in report
    assert "15" in report  # candidate_count 显示在概览中
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
    candidate_count: int = 0,
    valid_count: int = 0,
) -> str:
    month, day = target_date.split("-")[1:]
    lines = [
        f"# {int(month)}月{int(day)}日 小红书后端 / AI 应用开发面经日报",
        "",
        "## 今日概览",
        f"- 候选帖子数：{candidate_count}",
        f"- 有效面经数：{valid_count}",
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
    if trend_lines:
        lines.extend(f"- {line}" for line in trend_lines)
    else:
        lines.append("- 暂无足够历史数据用于趋势分析")
    lines.extend(["", "## 重点观察"])
    if observation_lines:
        lines.extend(f"- {line}" for line in observation_lines)
    else:
        lines.append("- 本期无特别观察")
    return "\n".join(lines)
```

```python
# src/xhs_agent/report/feishu.py
from __future__ import annotations

import httpx

# 飞书文档 Block 类型常量
BLOCK_PAGE = 1
BLOCK_TEXT = 2
BLOCK_HEADING_1 = 3
BLOCK_HEADING_2 = 4
BLOCK_HEADING_3 = 5
BLOCK_BULLET = 9
BLOCK_ORDERED_LIST = 10
BLOCK_DIVIDER = 18


class FeishuDocPublisher:
    def __init__(self, app_id: str, app_secret: str, parent_folder_token: str) -> None:
        self._app_id = app_id
        self._app_secret = app_secret
        self._parent_folder_token = parent_folder_token

    def _tenant_access_token(self) -> str:
        response = httpx.post(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": self._app_id, "app_secret": self._app_secret},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["tenant_access_token"]

    def _api_headers(self) -> dict:
        return {"Authorization": f"Bearer {self._tenant_access_token()}", "Content-Type": "application/json"}

    def publish_markdown(self, title: str, markdown: str, max_retries: int = 3) -> dict:
        """解析 Markdown 为飞书 Block 并发布为飞书文档（支持自动重试）。"""
        import time

        blocks = self._markdown_to_blocks(markdown)
        if not blocks:
            raise ValueError("no blocks to publish")

        last_error = None
        for attempt in range(max_retries):
            try:
                token = self._api_headers()

                # 创建文档并放入指定文件夹
                response = httpx.post(
                    "https://open.feishu.cn/open-apis/docx/v1/documents",
                    headers=token,
                    json={"title": title, "folder_token": self._parent_folder_token},
                    timeout=30,
                )
                response.raise_for_status()
                document_id = response.json()["data"]["document"]["document_id"]

                # 分批次写入 blocks（飞书 API 单次限制 50 个 block）
                BATCH_SIZE = 50
                for i in range(0, len(blocks), BATCH_SIZE):
                    batch = blocks[i:i + BATCH_SIZE]
                    httpx.post(
                        f"https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}/blocks/{document_id}/children",
                        headers=token,
                        json={"children": batch},
                        timeout=60,
                    ).raise_for_status()

                doc_url = f"https://feishu.cn/docx/{document_id}"
                return {"document_id": document_id, "url": doc_url}

            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                continue

        raise RuntimeError(f"feishu publish failed after {max_retries} attempts: {last_error}")

    def _markdown_to_blocks(self, markdown: str) -> list[dict]:
        """将 Markdown 文本转换为飞书 Block 列表。"""
        blocks: list[dict] = []
        for line in markdown.split("\n"):
            block = self._line_to_block(line)
            if block is not None:
                blocks.append(block)
        return blocks

    def _line_to_block(self, line: str) -> dict | None:
        stripped = line.strip()
        if not stripped:
            return None

        if stripped.startswith("### "):
            return self._heading_block(BLOCK_HEADING_3, stripped[4:])
        if stripped.startswith("## "):
            return self._heading_block(BLOCK_HEADING_2, stripped[3:])
        if stripped.startswith("# "):
            return self._heading_block(BLOCK_HEADING_1, stripped[2:])
        if stripped.startswith("- "):
            return self._bullet_block(stripped[2:])

        return self._text_block(stripped)

    def _heading_block(self, block_type: int, text: str) -> dict:
        return {
            "block_type": block_type,
            f"heading{block_type - 2}": {
                "elements": [{"text_run": {"content": text}}],
            },
        }

    def _text_block(self, text: str) -> dict:
        return {
            "block_type": BLOCK_TEXT,
            "text": {
                "elements": [{"text_run": {"content": text}}],
            },
        }

    def _bullet_block(self, text: str) -> dict:
        return {
            "block_type": BLOCK_BULLET,
            "bullet": {
                "elements": [{"text_run": {"content": text}}],
            },
        }
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
    assert result.get("warnings") is not None


def test_daily_runner_survives_crawl_failure():
    class BrokenCrawler:
        def fetch_posts_for_date(self, target_date):
            raise RuntimeError("network unreachable")

    result = DailyRunner(BrokenCrawler(), FakePipeline()).run(run_date="2026-04-09")

    assert result["target_date"] == "2026-04-08"
    assert result["warnings"] == ["crawl_failed"]
    assert result["top_posts"] == []
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
- Create: `src/xhs_agent/nodes/question_select_node.py`
- Create: `src/xhs_agent/nodes/answer_node.py`
- Create: `src/xhs_agent/nodes/report_node.py`
- Modify: `src/xhs_agent/storage/repository.py`
- Modify: `src/xhs_agent/report/feishu.py`
- Modify: `src/xhs_agent/runner.py`
- Modify: `src/xhs_agent/cli.py`
- Test: `tests/test_runner.py`

- [ ] **步骤 1：扩展 runner 测试，覆盖按需 OCR、日期过滤、高频题选择和部分失败标记**

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


def test_crawl_node_skips_posts_without_publish_time():
    # 发布时间缺失的帖子不能进入目标自然日样本。
    ...


def test_extract_node_downloads_images_only_when_text_has_no_questions():
    # 正文已有换行列表式题目时不 OCR；正文无题且有图片时下载图片并 OCR。
    ...


def test_question_select_node_answers_global_top_questions_not_first_questions_per_post():
    # 多篇帖子中的同义题先归并计数，再选择全局重点题进入 AnswerNode。
    ...
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
    selected_questions: list[dict] = field(default_factory=list)
    answer_cards: list[dict] = field(default_factory=list)
    top_posts: list[dict] = field(default_factory=list)
    top_tags: list[tuple[str, int]] = field(default_factory=list)
    trend_lines: list[str] = field(default_factory=list)
    observation_lines: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    report_markdown: str = ""
    report_url: str = ""
    dedupe_map: dict[str, int] | None = None
```

```python
# src/xhs_agent/nodes/crawl_node.py
from __future__ import annotations

import random
import uuid

from xhs_agent.crawl.html_extract import extract_post_detail

# 固定搜索词（每轮全部使用）
FIXED_QUERIES = [
    "后端面经", "后端面试", "服务端面经", "Java 面经",
    "AI 应用开发 面经", "Agent 面经", "LLM 面经", "RAG 面经",
]

# 锚定搜索词池（每轮随机抽 3 个）
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

        # 阶段 1：用固定搜索词搜索
        for query in FIXED_QUERIES:
            urls = self._browser.search_posts(query, max_scrolls=3)
            all_urls.update(urls)
            if len(all_urls) >= MAX_CANDIDATE_URLS:
                break

        # 阶段 2：用随机锚定搜索词搜索
        anchor_queries = random.sample(ANCHOR_QUERIES_POOL, k=min(3, len(ANCHOR_QUERIES_POOL)))
        for query in anchor_queries:
            urls = self._browser.search_posts(query, max_scrolls=3)
            all_urls.update(urls)

        # 阶段 3：打开详情页提取内容，并用目标日期过滤
        posts = []
        urls_to_fetch = list(all_urls)[:MAX_DETAIL_PAGES]
        for post_url in urls_to_fetch:
            try:
                html = self._browser.open_post_detail(post_url)
                publish_time = self._browser.extract_publish_time(html)
                # 时间过滤：发布时间缺失或不属于目标日期的帖子都跳过，避免污染自然日样本
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
```

```python
# src/xhs_agent/nodes/extract_node.py
from __future__ import annotations

from xhs_agent.crawl.candidate_filter import hard_excluded
from xhs_agent.extract.line_questions import split_to_candidate_lines, should_run_ocr


class ExtractNode:
    def __init__(self, ocr, llm_client) -> None:
        self._ocr = ocr
        self._llm = llm_client

    def run(self, state) -> None:
        extracted = []
        for item in state.raw_posts:
            # 第一级硬排除：标题/正文命中 Go/C++/前端/产品/运营 → 跳过
            if hard_excluded(item["title"], item["body_text"]):
                continue

            candidate_lines = split_to_candidate_lines(item["body_text"])
            if should_run_ocr(candidate_lines):
                for index, image_url in enumerate(item.get("image_urls", [])):
                    try:
                        image_path = self._ocr.download_image(image_url, f"{item['post_id']}-{index}")
                        image_text = self._ocr.extract_text(image_path)
                        candidate_lines.extend(split_to_candidate_lines(image_text))
                    except Exception:
                        state.warnings.append("ocr_failed")
                if not candidate_lines:
                    continue

            questions = self._llm.extract_questions(candidate_lines)
            if questions:
                extracted.append({**item, "question_lines": questions})
        state.extracted_posts = extracted
```

```python
# src/xhs_agent/nodes/classify_node.py
from __future__ import annotations

from xhs_agent.crawl.candidate_filter import is_candidate_post
from xhs_agent.models import RawPost
from xhs_agent.process.stats import build_tag_counts


class ClassifyNode:
    def __init__(self, enricher, repository) -> None:
        self._enricher = enricher
        self._repository = repository

    def run(self, state) -> None:
        enriched_posts = []
        top_posts = []
        tag_lists = []
        for item in state.extracted_posts:
            if not is_candidate_post(item["title"], item["body_text"]):
                continue
            # 直接构造 RawPost，不走 HTML 解析绕路
            post = RawPost(
                post_id=item["post_id"],
                title=item["title"],
                body_text=item["body_text"],
            )
            enriched = self._enricher.enrich(post, post_questions=item["question_lines"])
            self._repository.save_post(state.target_date, enriched)
            enriched_posts.append(enriched)
            top_posts.append(
                {
                    "company_name": enriched.company_name,
                    "round_name": enriched.round_name,
                    "questions": enriched.normalized_questions[:3],
                }
            )
            tag_lists.append(enriched.knowledge_tags)
        state.enriched_posts = enriched_posts
        state.top_posts = top_posts
        state.top_tags = build_tag_counts(tag_lists)
```

```python
# src/xhs_agent/nodes/question_select_node.py
from __future__ import annotations

from xhs_agent.process.dedupe import dedupe_questions


CORE_BACKEND_KEYWORDS = ("Redis", "MySQL", "JVM", "缓存", "消息队列", "分布式", "Spring", "Nginx")
AI_AGENT_KEYWORDS = ("RAG", "Agent", "LLM", "MCP", "Prompt", "Function Calling", "向量", "Embedding", "Tool")


def _question_score(question: str, count: int) -> int:
    score = count * 10
    if any(keyword in question for keyword in CORE_BACKEND_KEYWORDS):
        score += 3
    if any(keyword in question for keyword in AI_AGENT_KEYWORDS):
        score += 4
    return score


class QuestionSelectNode:
    def __init__(self, llm_client, max_questions: int = 8) -> None:
        self._llm = llm_client
        self._max_questions = max_questions

    def run(self, state) -> None:
        all_questions = [
            question
            for enriched in state.enriched_posts
            for question in enriched.normalized_questions
        ]
        question_counts = dedupe_questions(all_questions, self._llm)
        ranked = sorted(
            question_counts.items(),
            key=lambda item: (-_question_score(item[0], item[1]), item[0]),
        )
        state.selected_questions = [
            {"question": question, "count": count}
            for question, count in ranked[: self._max_questions]
        ]
```

```python
# src/xhs_agent/nodes/answer_node.py
from __future__ import annotations


class AnswerNode:
    def __init__(self, enricher) -> None:
        self._enricher = enricher

    def run(self, state) -> None:
        answer_cards = []
        for item in state.selected_questions:
            try:
                card = self._enricher.answer(item["question"])
                answer_cards.append(
                    {
                        "question": card.question,
                        "count": item["count"],
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

from xhs_agent.process.stats import compute_observation_lines, compute_trend_lines
from xhs_agent.report.render import render_daily_report


class ReportNode:
    def __init__(self, repository) -> None:
        self._repository = repository

    def run(self, state) -> None:
        # 生成趋势分析
        state.trend_lines = compute_trend_lines(
            state.target_date,
            state.top_tags,
            self._repository,
        )
        # 生成重点观察
        company_summary = self._repository.post_company_summary_for_date(state.target_date)
        state.observation_lines = compute_observation_lines(
            state.target_date,
            company_summary,
            state.top_tags,
            self._repository,
        )
        # 保存每日快照
        self._repository.save_daily_snapshot(
            target_date=state.target_date,
            candidate_count=len(state.raw_posts),
            valid_count=len(state.enriched_posts),
            question_count=len(state.answer_cards),
            top_tags=state.top_tags[:10],
            top_questions=[item["question"] for item in state.selected_questions],
        )

        state.report_markdown = render_daily_report(
            target_date=state.target_date,
            top_posts=state.top_posts,
            top_tags=state.top_tags,
            answered_questions=state.answer_cards,
            trend_lines=state.trend_lines,
            observation_lines=state.observation_lines,
            candidate_count=len(state.raw_posts),
            valid_count=len(state.enriched_posts),
        )
```

```python
# src/xhs_agent/orchestration/orchestrator.py
from __future__ import annotations

from xhs_agent.state import DailyJobState


class DailyOrchestrator:
    def __init__(self, crawl_node, extract_node, classify_node, question_select_node, answer_node, report_node) -> None:
        self._crawl_node = crawl_node
        self._extract_node = extract_node
        self._classify_node = classify_node
        self._question_select_node = question_select_node
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
        self._question_select_node.run(state)
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
            "url": state.report_url,
        }
```

```python
# src/xhs_agent/runner.py
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

        # 阶段 1：抓取
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

        # 阶段 2：处理
        result = self._pipeline.process_posts(posts, target_date)
        result["target_date"] = target_date
        result.setdefault("warnings", [])
        result.setdefault("markdown", "")

        # 阶段 3：发布
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
```

```python
# src/xhs_agent/cli.py
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
        # spec 第 15.1 节：抓取失败时发送失败通知
        sys.exit(1)


if __name__ == "__main__":
    main()
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
