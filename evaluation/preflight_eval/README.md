# Subject preflight evaluation

Record at least 30 real-device scenes in `manifest.jsonl`. Include front-facing half/full
body, distant people, side profiles, back views, looking down, masks, hats, low light,
groups, occlusion and edge placement. Each row needs human ground truth plus the API
preflight result.

```json
{"scene":"side_profile","person_actually_present":true,"preflight_state":"missing","reason_code":"no_face","blocked_shuttermuse":true}
```

Run:

```powershell
python evaluation\preflight_eval\run_eval.py evaluation\preflight_eval\manifest.jsonl
```

The primary metric is `false_block_rate_when_person_present`. Initial target: no more
than 5-8%. The backend `/v1/status` endpoint also reports unlabeled live outcome counts
and block rate, but those counters cannot determine false blocks without human labels.
