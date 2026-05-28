## Xiaohongshu Daily Interview Report Agent

Use `.env` for credentials and `python -m xhs_agent.cli run-daily --run-date YYYY-MM-DD` to generate a report after later tasks are complete.

## Local Run

```powershell
.venv\Scripts\python -m xhs_agent.cli run-daily --run-date 2026-04-09
```

## Scheduling

Use Windows Task Scheduler to run the command every day at 00:10 local time and let the report publish after the pipeline completes.
