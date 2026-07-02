from __future__ import annotations

from pathlib import Path


DEFAULT_DB_PATH = Path(".webhook_rescue/webhook_rescue.db")
DEFAULT_REPORT_PATH = Path("outputs/recovery_report.md")


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def project_path(value: str | Path) -> Path:
    return Path(value)

