from __future__ import annotations

import html
from collections import Counter

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


def _percent(value: float | None) -> str:
    return "-" if value is None else f"{value * 100:.1f}%"


def _action_lines(results: list[dict]) -> list[str]:
    lines = []
    for row in results:
        messages = [action["message"] for action in row["output"].get("actions", [])]
        lines.append(f"- `{row['eval_id']}` {row['scenario']}: {' / '.join(messages)}")
    return lines


def render() -> dict:
    preflight_manifest = read_jsonl(MANIFEST_ROOT / "preflight.jsonl")
    composition_manifest = read_jsonl(MANIFEST_ROOT / "composition.jsonl")
    composition_results = read_jsonl(REPORT_ROOT / "data" / "composition_results.jsonl")
    import json

    preflight_summary = json.loads(
        (REPORT_ROOT / "preflight_summary.json").read_text(encoding="utf-8")
    )
    composition_summary = json.loads(
        (REPORT_ROOT / "composition_summary.json").read_text(encoding="utf-8")
    )
    source_counts = Counter(row["source_kind"] for row in preflight_manifest)
    scenarios = sorted({row["scenario"] for row in preflight_manifest})
    matrix = preflight_summary["confusion_matrix"]
    wrong_cases = [
        row for row in composition_results if row["checks"]["wrong_direction"]
    ]
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
        "composition": composition_summary,
        "minimum_device_preflight": DEVICE_PREFLIGHT,
        "minimum_device_composition": DEVICE_COMPOSITION,
    }
    write_json(REPORT_ROOT / "latest.json", report)

    markdown = [
        "# Beeep Offline Evaluation Report",
        "",
        "> This report uses local MediaPipe for preflight and deterministic bbox fixtures for Adapter validation. ",
        "> It does not claim ShutterMuse model quality; run composition evaluation in `api` mode for that.",
        "",
        "## Dataset",
        "",
        f"- Local image library: {report['image_library_count']} ({library_counts})",
        f"- Subject preflight cases: {len(preflight_manifest)} ({dict(source_counts)})",
        f"- Composition action cases: {len(composition_manifest)}",
        f"- Covered subject scenarios: {len(scenarios)}",
        "",
        "## Subject Preflight",
        "",
        f"- Confusion matrix: TP={matrix['true_positive']}, TN={matrix['true_negative']}, FP={matrix['false_positive']}, FN={matrix['false_negative']}",
        f"- Cascade-only confusion matrix: {preflight_summary.get('cascade_confusion_matrix', {})}",
        f"- Person-present block rate: {_percent(preflight_summary['person_present_block_rate'])}",
        f"- Cascade person-missing rate before fail-open: {_percent(preflight_summary.get('cascade_person_missing_rate'))}",
        f"- P50/P95 preflight: {preflight_summary['preflight_p50_ms']} ms / {preflight_summary['preflight_p95_ms']} ms",
        f"- Face-only FN: {preflight_summary.get('face_only_FN', '-')}",
        f"- Face + Pose cascade FN: {preflight_summary.get('cascade_FN', '-')}",
        f"- History recovered: {preflight_summary.get('history_recovered_count', '-')}",
        f"- Uncertain final states: {preflight_summary.get('uncertain_count', '-')}",
        f"- Confirmed missing: {preflight_summary.get('confirmed_missing_count', '-')}",
        f"- False negatives: {preflight_summary['false_negative_ids'] or 'none'}",
        f"- False positives: {preflight_summary['false_positive_ids'] or 'none'}",
        "",
        "### Original false-negative recovery",
        "",
        *(
            f"- `{image_id}`: {recovery}"
            for image_id, recovery in preflight_summary.get(
                "old_false_negative_recovery", {}
            ).items()
        ),
        "",
        "## Composition Adapter",
        "",
        f"- Evaluation mode: `{composition_summary['evaluation_mode']}`",
        f"- Bbox parse success: {_percent(composition_summary['bbox_parse_success'])}",
        f"- Direction correct: {_percent(composition_summary['direction_correct'])}",
        f"- Primary action correct: {_percent(composition_summary['primary_action_correct'])}",
        f"- Secondary action helpful: {_percent(composition_summary['secondary_action_helpful'])}",
        f"- Contradictory actions: {composition_summary['contradictory_actions']}",
        f"- Wrong direction rate: {_percent(composition_summary['wrong_direction_rate'])}",
        f"- P50/P95 guidance: {composition_summary['guidance_p50_ms']} ms / {composition_summary['guidance_p95_ms']} ms",
        "",
        "## Guidance Samples",
        "",
        *_action_lines(composition_results[:10]),
        "",
        "## Wrong Direction Cases",
        "",
        *(f"- `{row['eval_id']}` {row['scenario']}" for row in wrong_cases),
        *(["- none"] if not wrong_cases else []),
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
        "- AI-generated images are boundary coverage, not the only quality source.",
        "- Public images are license-checked at download time but are not guaranteed smartphone captures.",
        "- Derived images simulate camera defects; they do not replace real sensor, motion, and lens behavior.",
        "- The 9 preflight and 6 composition scenarios above still require manual true-device validation.",
        "",
    ]
    (REPORT_ROOT / "latest.md").write_text("\n".join(markdown), encoding="utf-8")

    rows_html = "".join(
        "<tr>"
        f"<td>{html.escape(row['eval_id'])}</td>"
        f"<td>{html.escape(row['scenario'])}</td>"
        f"<td>{html.escape(' / '.join(action['message'] for action in row['output'].get('actions', [])))}</td>"
        f'<td><a href="{html.escape(row["overlay_path"])}">overlay</a></td>'
        "</tr>"
        for row in composition_results
    )
    document = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Beeep Offline Evaluation</title>
<style>body{{font:15px system-ui;margin:32px;max-width:1100px;color:#18201f}}.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}.metric{{border:1px solid #d7dfdd;padding:16px;border-radius:6px}}table{{width:100%;border-collapse:collapse}}th,td{{padding:9px;border-bottom:1px solid #e5e9e8;text-align:left}}code{{background:#eef2f1;padding:2px 5px}}</style></head>
<body><h1>Beeep Offline Evaluation</h1><p>MediaPipe preflight + deterministic GuidanceAdapter fixture report. This is not a ShutterMuse quality score.</p>
<div class="grid"><div class="metric"><b>Preflight</b><br>{len(preflight_manifest)} cases</div><div class="metric"><b>Block rate</b><br>{_percent(preflight_summary["person_present_block_rate"])}</div><div class="metric"><b>Cascade FN</b><br>{preflight_summary.get("cascade_FN", "-")}</div><div class="metric"><b>P95</b><br>{preflight_summary["preflight_p95_ms"]} ms</div></div>
<h2>Confusion matrix</h2><table><tr><th></th><th>Predicted person</th><th>Predicted missing</th></tr><tr><th>Person present</th><td>{matrix["true_positive"]}</td><td>{matrix["false_negative"]}</td></tr><tr><th>Person absent</th><td>{matrix["false_positive"]}</td><td>{matrix["true_negative"]}</td></tr></table>
<h2>Composition overlays and actions</h2><table><tr><th>ID</th><th>Scenario</th><th>Guidance</th><th>Visual</th></tr>{rows_html}</table>
<h2>Still required on a real device</h2><p>{len(DEVICE_PREFLIGHT)} preflight scenarios and {len(DEVICE_COMPOSITION)} composition scenarios remain mandatory; see <code>latest.md</code>.</p></body></html>"""
    (REPORT_ROOT / "index.html").write_text(document, encoding="utf-8")
    return report


if __name__ == "__main__":
    result = render()
    print(f"report_images={result['image_library_count']}")
