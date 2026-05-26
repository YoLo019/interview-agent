from xhs_agent.config import Settings, build_target_window
import tomllib


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


def test_declared_python_version_matches_type_syntax():
    with open("pyproject.toml", "rb") as handle:
        project = tomllib.load(handle)["project"]

    assert project["requires-python"] == ">=3.10"
