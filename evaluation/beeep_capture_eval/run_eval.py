from __future__ import annotations

import argparse
import base64
import json
import time
from pathlib import Path

import httpx
from PIL import Image


def analyze(url: str, record: dict, frame_id: int) -> tuple[dict, int]:
    image_path = Path(record["image_path"])
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    with Image.open(image_path) as image:
        width, height = image.size
        mime = Image.MIME.get(image.format, "image/jpeg")
    payload = {
        "frame_id": frame_id,
        "timestamp": int(time.time() * 1000),
        "mode": "composition",
        "composition_mode": record["composition_mode"],
        "target_ratio": record["target_ratio"],
        "language": "zh-CN",
        "image": {
            "base64": encoded,
            "width": width,
            "height": height,
            "mime_type": mime,
        },
    }
    started = time.perf_counter()
    response = httpx.post(url, json=payload, timeout=60)
    latency_ms = int((time.perf_counter() - started) * 1000)
    try:
        body = response.json()
    except ValueError:
        body = {"status": "error", "error": {"code": "NON_JSON_RESPONSE"}}
    body["http_status"] = response.status_code
    return body, latency_ms


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--rules-url", required=True)
    parser.add_argument("--shuttermuse-url", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    records = [json.loads(line) for line in Path(args.manifest).read_text(encoding="utf-8").splitlines() if line]
    with Path(args.output).open("w", encoding="utf-8") as output:
        for frame_id, record in enumerate(records, start=1):
            rules_result, rules_ms = analyze(args.rules_url, record, frame_id)
            model_result, model_ms = analyze(args.shuttermuse_url, record, frame_id)
            result = {
                **record,
                "rules_result": rules_result,
                "shuttermuse_result": model_result,
                "latency": {"rules_ms": rules_ms, "shuttermuse_ms": model_ms},
            }
            output.write(json.dumps(result, ensure_ascii=False) + "\n")
            output.flush()


if __name__ == "__main__":
    main()
