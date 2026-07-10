# Beeep Capture Evaluation

This folder compares the `rules` and `shuttermuse` Beeep backends on the same real phone images.
Images are intentionally not committed. Put review images in `images/`, copy
`manifest.example.jsonl` to `manifest.jsonl`, and run:

```powershell
python run_eval.py `
  --manifest manifest.jsonl `
  --rules-url http://127.0.0.1:8000/v1/analyze `
  --shuttermuse-url http://127.0.0.1:8001/v1/analyze `
  --output results.jsonl
```

Run two Beeep backend processes, one with `GUIDANCE_ENGINE=rules` and one with
`GUIDANCE_ENGINE=shuttermuse`. Start with 50-100 images across portrait, landscape,
lighting, clutter, orientation and target-ratio categories. Human reviewers fill in
`human_review` after generation.

Primary safety metric: wrong-direction guidance rate. A missed suggestion is safer than
an action that moves the camera in the opposite direction.
