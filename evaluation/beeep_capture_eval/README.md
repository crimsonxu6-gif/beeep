# Beeep capture evaluation

This directory builds a mixed offline dataset and evaluates two separate risks:

1. MediaPipe Face + Pose cascade preflight and its stateful fail-open presence gate.
2. ShutterMuse bbox parsing and Beeep `GuidanceAdapter` action semantics.

Third-party and AI-generated image files stay local under `images/` and are gitignored.
The repository only keeps provenance manifests, scripts, aggregate statistics and reports.

## Dataset shape

- Subject preflight: 30 cases: 10 public real photographs, 10 AI boundary images and 10 deterministic transforms.
- Composition actions: 20 cases: 15 public/public-derived photographs and 5 AI extreme compositions.
- Transform library: dark, overexposed, Gaussian blur, motion blur, JPEG compression, partial occlusion,
  subject shrink, horizontal mirror, rotation and four directional crops.

Public images are pinned to Wikimedia Commons file titles. `download_images.py` rejects files unless their
API metadata reports CC0, CC BY, CC BY-SA or public-domain licensing. The generated metadata contains
`source_url`, `author`, `license`, `downloaded_at`, `scenario` and `expected_person_present`.

## Build and run

Use the backend virtual environment because it already contains MediaPipe, OpenCV, Pillow and pytest:

```powershell
cd D:\beeep
.\.venv\Scripts\python.exe evaluation\beeep_capture_eval\scripts\run_all.py
```

Individual stages:

```powershell
.\.venv\Scripts\python.exe evaluation\beeep_capture_eval\scripts\download_images.py
.\.venv\Scripts\python.exe evaluation\beeep_capture_eval\scripts\transform_images.py
.\.venv\Scripts\python.exe evaluation\beeep_capture_eval\scripts\build_manifests.py
.\.venv\Scripts\python.exe evaluation\beeep_capture_eval\scripts\run_preflight_eval.py
.\.venv\Scripts\python.exe evaluation\beeep_capture_eval\scripts\run_composition_eval.py --mode fixture
.\.venv\Scripts\python.exe evaluation\beeep_capture_eval\scripts\render_report.py
```

`fixture` mode validates deterministic bbox-to-action behavior only. It must not be presented as a
ShutterMuse model score. To evaluate the real model, start a Beeep backend with
`GUIDANCE_ENGINE=shuttermuse`, keep `SUBJECT_PREFLIGHT_BLOCKING=0`, and run:

```powershell
.\.venv\Scripts\python.exe evaluation\beeep_capture_eval\scripts\run_composition_eval.py `
  --mode api `
  --api-url http://127.0.0.1:8000/v1/analyze `
  --request-timeout 180 `
  --run-id 4060_4bit_offload_768_sdpa_96_run01 `
  --gpu "RTX 4060 Laptop" `
  --precision 4bit_nf4 `
  --cpu-offload
```

Run IDs are immutable and write to `reports/runs/<run-id>/`. Each run contains
`composition_api_results.jsonl`, `composition_api_summary.json`, `run_config.json`,
`raw_outputs.jsonl`, `index.html`, and local overlay artifacts. The runner also refreshes
the legacy latest files for convenience. Enable `SHUTTERMUSE_EVAL_CAPTURE_RAW_OUTPUT=1`
on the model service to populate raw-output diagnostics; production keeps it disabled.

Greedy repeatability is measured separately on five representative images:

```powershell
.\.venv\Scripts\python.exe evaluation\beeep_capture_eval\scripts\run_repeatability_eval.py `
  --api-url http://127.0.0.1:8000/v1/analyze `
  --request-timeout 180 `
  --run-id 4060_4bit_offload_768_sdpa_96_repeat01
```

The report records exact raw-output matches, parse counts, decisions, bbox means and standard
deviations, placeholder/format changes, and latency. It marks a configuration
`MODEL_REPEATABILITY_FAILED` instead of hiding unstable output.

The modes write separate artifacts:

- fixture: `reports/composition_fixture_summary.json` and
  `reports/data/composition_fixture_results.jsonl`;
- live API: `reports/composition_api_summary.json`,
  `reports/data/composition_api_results.jsonl`, and `reports/artifacts/shuttermuse_api/`;
- human review: `manifests/composition_reviews.jsonl`.

The API runner preserves existing review values, records errors per image without stopping the batch,
and saves model prompt mode, coordinate source, decision, normalized bbox, confidence, raw-output
diagnostics, preflight signal, actions, and timing. Set `output_usable=false` for format failures and
leave `bbox_quality=null`; use `output_usable=true` plus a 1-5 quality score only for legal boxes.
Rerunning the API evaluation reloads review values. Reports show format usability, average quality
among successful boxes, and product usability separately. Product usability requires API success,
a legal bbox, `output_usable=true`, and `bbox_quality >= 3`.

The combined HTML report is `reports/index.html`; the machine-readable summary is
`reports/latest.json`. It always separates preflight, deterministic fixture, and live model results.
Overlay JPEGs and raw per-image result rows are local-only because they contain derivatives of the
uncommitted source images.

Preflight reporting separates `face_only_FN`, `cascade_FN`, and the effective
`person_present_block_rate`. With `SUBJECT_PREFLIGHT_BLOCKING=0`, confirmed missing frames are still
sent to ShutterMuse; this protects recall while the cascade thresholds are evaluated. The report also
records detection source, raw Face/Pose signals, history recovery and the original false-negative cases.

## True-device validation remains required

The automated set reduces, but does not remove, real phone validation. The report retains nine
subject-preflight scenarios and six composition-action scenarios for manual device checks. This covers
sensor noise, real motion, front-camera mirroring, transient frame loss and whether instructions are
physically intuitive while a user is holding the phone.
