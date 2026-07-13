from __future__ import annotations

import json
import math
import re
from collections.abc import Iterable
from html import unescape
from pathlib import Path
from typing import Any

EVAL_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = EVAL_ROOT.parents[1]
IMAGES_ROOT = EVAL_ROOT / "images"
MANIFEST_ROOT = EVAL_ROOT / "manifests"
REPORT_ROOT = EVAL_ROOT / "reports"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows
    )
    path.write_text(body, encoding="utf-8")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def percentile(values: list[int | float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(float(value) for value in values)
    index = max(0, math.ceil(len(ordered) * quantile) - 1)
    return round(ordered[index], 2)


def strip_html(value: str | None) -> str:
    if not value:
        return "Unknown"
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", "", value))).strip()


def relative_image_path(path: Path) -> str:
    return path.resolve().relative_to(EVAL_ROOT.resolve()).as_posix()
