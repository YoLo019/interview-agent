from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from dateutil import tz
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
    tzinfo = tz.gettz(timezone_name)
    if tzinfo is None:
        tzinfo = timezone(timedelta(hours=8))  # fallback to CST
    run_date = date.fromisoformat(run_date_iso)
    target_date = run_date - timedelta(days=1)
    start = datetime.combine(target_date, datetime.min.time(), tzinfo=tzinfo)
    end = start + timedelta(days=1)
    return start, end, target_date.isoformat()
