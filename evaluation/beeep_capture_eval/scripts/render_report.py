from __future__ import annotations

import html
import json
from collections import Counter
from pathlib import Path

from common import MANIFEST_ROOT, REPORT_ROOT, read_jsonl, write_json

DEVICE_PREFLIGHT = [
    "正面半身与正面全身",
    "大侧脸与完全背影",
    "手部遮脸或口罩加帽子",
    "真实弱光与强逆光",
    "人物很远且占画面很小",
    "三人以上且人物贴近边缘",
    "前置摄像头水平镜像",
    "走动中的轻度运动模糊",
    "短暂出框后 1.5 秒内重新进入",
]

DEVICE_COMPOSITION = [
    "推荐框偏左和偏右时，用户实际移动方向",
    "推荐框偏上和偏下时，取景移动语义",
    "人物过小时“让人物再大一些”的可执行性",
    "水平移动加距离调整的双指令可执行性",
    "模型 keep 时是否应该立即拍摄",
    "连续十帧中构图框和主建议的稳定性",
]


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _percent(value: float | None) -> str:
    return "-" if value is None else f"{value * 100:.1f}%"


def _count_rate(count: int | None, total: int | None, rate: float | None) -> str:
    if count is None or total is None:
        return "-"
    return f"{count} / {total} ({_percent(rate)})"


def _action_lines(results: list[dict]) -> list[str]:
    lines = []
    for row in results:
        actions = row.get("output", {}).get("actions", [])
        messages = [action.get("message", "") for action in actions]
        lines.append(
            f"- `{row['eval_id']}` {row['scenario']}: {' / '.join(messages) or 'no action'}"
        )
    return lines


def _html_rows(results: list[dict]) -> str:
    rows = []
    for row in results:
        actions = row.get("output", {}).get("actions", [])
        messages = " / ".join(action.get("message", "") for action in actions)
        overlay = row.get("overlay_path")
        visual = f'<a href="{html.escape(overlay)}">overlay</a>' if overlay else "-"
        rows.append(
            "<tr>"
            f"<td>{html.escape(row['eval_id'])}</td>"
            f"<td>{html.escape(row['scenario'])}</td>"
            f"<td>{html.escape(str(row.get('raw_model_decision') or '-'))}</td>"
            f"<td>{html.escape(messages or '-')}</td>"
            f"<td>{html.escape(str(row.get('error_code') or '-'))}</td>"
            f"<td>{visual}</td>"
            "</tr>"
        )
    return "".join(rows)


def render() -> dict:
    preflight_manifest = read_jsonl(MANIFEST_ROOT / "preflight.jsonl")
    composition_manifest = read_jsonl(MANIFEST_ROOT / "composition.jsonl")
    fixture_results_path = REPORT_ROOT / "data" / "composition_fixture_results.jsonl"
    if not fixture_results_path.exists():
        fixture_results_path = REPORT_ROOT / "data" / "composition_results.jsonl"
    fixture_results = read_jsonl(fixture_results_path)
    api_results = read_jsonl(REPORT_ROOT / "data" / "composition_api_results.jsonl")

    preflight_summary = _load_json(REPORT_ROOT / "preflight_summary.json") or {}
    fixture_summary = _load_json(REPORT_ROOT / "composition_fixture_summary.json")
    if fixture_summary is None:
        fixture_summary = _load_json(REPORT_ROOT / "composition_summary.json") or {}
    api_summary = _load_json(REPORT_ROOT / "composition_api_summary.json")
    source_counts = Counter(row["source_kind"] for row in preflight_manifest)
    scenarios = sorted({row["scenario"] for row in preflight_manifest})
    matrix = preflight_summary.get("confusion_matrix", {})
    library_counts = {
        "public_real": len(read_jsonl(MANIFEST_ROOT / "public_sources.jsonl")),
        "ai_generated": len(read_jsonl(MANIFEST_ROOT / "ai_sources.jsonl")),
        "transformed": len(read_jsonl(MANIFEST_ROOT / "transformed_sources.jsonl")),
    }
    report = {
        "image_library_count": sum(library_counts.values()),
        "library_source_counts": library_counts,
        "preflight_case_count": len(preflight_manifest),
        "composition_case_count": len(composition_manifest),
        "scenario_coverage": scenarios,
        "preflight": preflight_summary,
        "composition_fixture": fixture_summary,
        "composition_api": api_summary,
        "composition": fixture_summary,
        "minimum_device_preflight": DEVICE_PREFLIGHT,
        "minimum_device_composition": DEVICE_COMPOSITION,
    }
    write_json(REPORT_ROOT / "latest.json", report)

    markdown = [
        "# Beeep Photography Evaluation Report",
        "",
        "> Results are separated into subject preflight, deterministic GuidanceAdapter fixture, and live ShutterMuse API layers.",
        "> Fixture output is not evidence of ShutterMuse composition quality.",
        "",
        "## Dataset",
        "",
        f"- Local image library: {report['image_library_count']} ({library_counts})",
        f"- Subject preflight cases: {len(preflight_manifest)} ({dict(source_counts)})",
        f"- Composition cases: {len(composition_manifest)}",
        f"- Covered subject scenarios: {len(scenarios)}",
        "",
        "## 1. Subject Preflight",
        "",
        f"- Final fail-open gate: {matrix}",
        f"- Face-only FN: {preflight_summary.get('face_only_FN', '-')}",
        f"- Face + Pose cascade: {preflight_summary.get('cascade_confusion_matrix', {})}",
        f"- Final person-present block rate: {_percent(preflight_summary.get('person_present_block_rate'))}",
        f"- P50/P95: {preflight_summary.get('preflight_p50_ms')} / {preflight_summary.get('preflight_p95_ms')} ms",
        "",
        "## 2. GuidanceAdapter Fixture",
        "",
        "This layer verifies deterministic bbox-to-action conversion only.",
        "",
        f"- Total: {fixture_summary.get('total', 0)}",
        f"- Bbox parse success: {_percent(fixture_summary.get('bbox_parse_success'))}",
        f"- Fixture direction match: {_percent(fixture_summary.get('direction_correct'))}",
        f"- Contradictory actions: {fixture_summary.get('contradictory_actions', 0)}",
        f"- Wrong direction: {_count_rate(fixture_summary.get('wrong_direction_count', 0), fixture_summary.get('total', 0), fixture_summary.get('wrong_direction_rate'))}",
        "",
        "### Fixture Samples",
        "",
        *_action_lines(fixture_results[:10]),
        "",
        "## 3. ShutterMuse API",
        "",
    ]
    if api_summary is None:
        markdown.extend(
            [
                "- Status: not run",
                "- Start the real model service and run `run_composition_eval.py --mode api`.",
            ]
        )
    else:
        review = api_summary.get("review", {})
        reviewed_direction_count = review.get("primary_direction_correct_count", 0)
        reviewed_wrong_direction = (
            _count_rate(
                api_summary.get("wrong_direction_count"),
                reviewed_direction_count,
                api_summary.get("wrong_direction_rate"),
            )
            if reviewed_direction_count
            else "pending human review"
        )
        markdown.extend(
            [
                f"- Total: {api_summary.get('total', 0)}",
                f"- Run ID: {api_summary.get('run_id', '-')}",
                f"- API success: {_count_rate(api_summary.get('api_success_count'), api_summary.get('total'), api_summary.get('api_success_rate'))}",
                f"- Bbox parse: {_count_rate(api_summary.get('bbox_parse_success_count'), api_summary.get('bbox_parse_attempts'), api_summary.get('bbox_parse_success'))}",
                f"- Invalid output: {_count_rate(api_summary.get('invalid_output_count'), api_summary.get('total'), api_summary.get('invalid_output_rate'))}",
                f"- Decision distribution: {api_summary.get('decision_distribution', {})}",
                f"- Coordinate sources: {api_summary.get('coordinate_source_distribution', {})}",
                f"- Parse failures: {api_summary.get('parse_failure_distribution', {})}",
                f"- Parser comparison: {api_summary.get('parser_comparison_distribution', {})}",
                f"- Errors: {api_summary.get('error_distribution', {})}",
                f"- Generated tokens mean/P50/P95: {api_summary.get('generated_token_mean')} / {api_summary.get('generated_token_p50')} / {api_summary.get('generated_token_p95')}",
                f"- Reached max tokens: {api_summary.get('reached_max_new_tokens_count', 0)}",
                f"- Output truncated: {api_summary.get('output_truncated_count', 0)}",
                f"- Human-reviewed direction correct: {_percent(api_summary.get('human_primary_direction_correct_rate'))}",
                f"- Human-reviewed wrong direction: {reviewed_wrong_direction}",
                f"- Human-reviewed primary action helpful: {_percent(api_summary.get('human_primary_action_helpful_rate'))}",
                f"- Human-reviewed secondary action helpful: {_percent(api_summary.get('human_secondary_action_helpful_rate'))}",
                f"- Guidance P50/P95: {api_summary.get('guidance_p50_ms')} / {api_summary.get('guidance_p95_ms')} ms",
                f"- Total P50/P95: {api_summary.get('total_p50_ms')} / {api_summary.get('total_p95_ms')} ms",
                f"- Human review: {review.get('reviewed_count', 0)} reviewed, {review.get('unreviewed_count', 0)} pending",
                f"- Bbox quality mean/median: {review.get('bbox_quality_mean')} / {review.get('bbox_quality_median')}",
                f"- Output usable: {_count_rate(review.get('output_usable_count'), review.get('output_usable_reviewed_count'), review.get('output_usable_rate'))}",
                f"- Product usable: {_count_rate(review.get('product_usable_count'), api_summary.get('total'), review.get('product_usable_rate'))}",
                "",
                "### API Samples",
                "",
                *_action_lines(api_results[:10]),
            ]
        )
    markdown.extend(
        [
            "",
            "## Minimum True-device Preflight Validation (9)",
            "",
            *(f"- {item}" for item in DEVICE_PREFLIGHT),
            "",
            "## Minimum True-device Composition Validation (6)",
            "",
            *(f"- {item}" for item in DEVICE_COMPOSITION),
            "",
            "## Limitations",
            "",
            "- AI-generated images provide boundary coverage and are not the only quality source.",
            "- Public and transformed images do not replace real sensor, motion, lens, or front-camera behavior.",
            "- Human review scores apply only to the archived model outputs that were actually inspected.",
            "- The 9 preflight and 6 composition scenarios above still require true-device validation.",
            "",
        ]
    )
    (REPORT_ROOT / "latest.md").write_text("\n".join(markdown), encoding="utf-8")

    api_status = (
        f"{api_summary.get('api_success_count', 0)} / {api_summary.get('total', 0)} succeeded"
        if api_summary
        else "not run"
    )
    fixture_rows = _html_rows(fixture_results)
    api_rows = _html_rows(api_results)
    document = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Beeep Photography Evaluation</title>
<style>body{{font:15px system-ui;margin:32px;max-width:1200px;color:#18201f}}.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}.metric{{border:1px solid #d7dfdd;padding:16px;border-radius:6px}}table{{width:100%;border-collapse:collapse}}th,td{{padding:9px;border-bottom:1px solid #e5e9e8;text-align:left}}code{{background:#eef2f1;padding:2px 5px}}.note{{padding:12px;background:#eef7f5;border-left:3px solid #38b99c}}</style></head>
<body><h1>Beeep Photography Evaluation</h1><p class="note">Three independent layers: preflight, deterministic adapter fixture, and live ShutterMuse API. Fixture results are not model quality.</p>
<div class="grid"><div class="metric"><b>Preflight block</b><br>{_percent(preflight_summary.get("person_present_block_rate"))}</div><div class="metric"><b>Cascade FN</b><br>{preflight_summary.get("cascade_FN", "-")}</div><div class="metric"><b>Fixture</b><br>{fixture_summary.get("total", 0)} cases</div><div class="metric"><b>Live API</b><br>{html.escape(api_status)}</div></div>
<h2>GuidanceAdapter fixture</h2><p>Fixed bbox-to-action validation only.</p><table><tr><th>ID</th><th>Scenario</th><th>Decision</th><th>Guidance</th><th>Error</th><th>Visual</th></tr>{fixture_rows}</table>
<h2>Live ShutterMuse API</h2><p>{html.escape(api_status)}. Human reviews are stored separately in <code>manifests/composition_reviews.jsonl</code>.</p><table><tr><th>ID</th><th>Scenario</th><th>Decision</th><th>Guidance</th><th>Error</th><th>Visual</th></tr>{api_rows}</table>
<h2>Still required on a real device</h2><p>{len(DEVICE_PREFLIGHT)} preflight scenarios and {len(DEVICE_COMPOSITION)} composition scenarios remain mandatory; see <code>latest.md</code>.</p></body></html>"""
    (REPORT_ROOT / "index.html").write_text(document, encoding="utf-8")
    return report


if __name__ == "__main__":
    result = render()
    print(
        f"report_images={result['image_library_count']} "
        f"live_api={'present' if result['composition_api'] else 'not_run'}"
    )
