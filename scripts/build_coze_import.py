#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "coze_import"
OUTPUT_FILE = OUTPUT_DIR / "project.json"

EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    ".mypy_cache",
    ".pytest_cache",
    "coze_import",
}

EXCLUDE_SUFFIXES = {".pyc"}
EXCLUDE_NAMES = {".DS_Store"}


def should_skip(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    if any(part in EXCLUDE_DIRS for part in relative.parts):
        return True
    if path.name in EXCLUDE_NAMES:
        return True
    if path.suffix in EXCLUDE_SUFFIXES:
        return True
    return False


def iter_files() -> list[dict[str, str]]:
    files: list[dict[str, str]] = []
    for path in sorted(ROOT.rglob("*")):
        if path.is_dir():
            continue
        if should_skip(path):
            continue
        relative = path.relative_to(ROOT)
        content = path.read_bytes()
        files.append(
            {
                "path": str(relative),
                "encoding": "base64",
                "content": base64.b64encode(content).decode("utf-8"),
            }
        )
    return files


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "format_version": 1,
        "project_name": ROOT.name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "files": iter_files(),
    }
    OUTPUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
