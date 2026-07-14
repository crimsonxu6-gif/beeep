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
  --request-timeout 180
```

The modes write separate artifacts:

- fixture: `reports/composition_fixture_summary.json` and
  `reports/data/composition_fixture_results.jsonl`;
- live API: `reports/composition_api_summary.json`,
  `reports/data/composition_api_results.jsonl`, and `reports/artifacts/shuttermuse_api/`;
- human review: `manifests/composition_reviews.jsonl`.

The API runner preserves existing review values, records errors per image without stopping the batch,
and saves model prompt mode, coordinate source, decision, normalized bbox, confidence, preflight
signal, actions, and timing. Fill `bbox_quality` with an integer from 1 to 5 and the review booleans
with `true` or `false`; rerunning the API evaluation reloads those values into the report.

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
