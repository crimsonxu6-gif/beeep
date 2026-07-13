from __future__ import annotations

from build_manifests import build
from download_images import download
from render_report import render
from run_composition_eval import evaluate as evaluate_composition
from run_preflight_eval import evaluate as evaluate_preflight
from transform_images import transform

from common import MANIFEST_ROOT, REPORT_ROOT, write_json, write_jsonl


def main() -> None:
    download()
    transform()
    build()

    preflight_results, preflight_summary = evaluate_preflight(
        MANIFEST_ROOT / "preflight.jsonl"
    )
    write_jsonl(REPORT_ROOT / "data" / "preflight_results.jsonl", preflight_results)
    write_json(REPORT_ROOT / "preflight_summary.json", preflight_summary)

    composition_results, composition_summary = evaluate_composition(
        MANIFEST_ROOT / "composition.jsonl",
        mode="fixture",
    )
    write_jsonl(REPORT_ROOT / "data" / "composition_results.jsonl", composition_results)
    write_json(REPORT_ROOT / "composition_summary.json", composition_summary)
    render()
    print("dataset_and_reports_ready")


if __name__ == "__main__":
    main()
