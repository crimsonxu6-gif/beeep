from __future__ import annotations

import json
import sys
from pathlib import Path


def evaluate(path: Path) -> dict[str, float | int]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    person_rows = [row for row in rows if row.get("person_actually_present") is True]
    false_blocks = [row for row in person_rows if row.get("blocked_shuttermuse") is True]
    empty_rows = [row for row in rows if row.get("person_actually_present") is False]
    false_passes = [row for row in empty_rows if row.get("blocked_shuttermuse") is False]
    return {
        "total": len(rows),
        "person_present": len(person_rows),
        "false_blocks": len(false_blocks),
        "false_block_rate_when_person_present": round(
            len(false_blocks) / len(person_rows), 4
        ) if person_rows else 0,
        "person_absent": len(empty_rows),
        "false_passes": len(false_passes),
        "false_pass_rate_when_person_absent": round(
            len(false_passes) / len(empty_rows), 4
        ) if empty_rows else 0,
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: run_eval.py <manifest.jsonl>")
    print(json.dumps(evaluate(Path(sys.argv[1])), ensure_ascii=False, indent=2))
