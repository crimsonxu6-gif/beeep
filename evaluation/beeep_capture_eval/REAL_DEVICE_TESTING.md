# Beeep real-device composition analysis

The 22 cases in `manifests/real_device_test_matrix.jsonl` are the physical-device test plan.
Only change a case to `passed` after running it on a physical device; use `partial` when the core
path ran but required evidence is still missing. The first partial Redmi 9A run is recorded in
`reports/real_device_redmi9a_2026-07-18.json`.

Minimum execution is one physical Android phone, rear and front cameras, portrait orientation, and
Wi-Fi. The preferred matrix adds an iPhone, a mid-range Android phone, and a lower-end Android
phone. For each device record model name, OS/version, App build, network type, camera facing,
analysis short edge, JPEG quality, upload mode, and backend/model run ID.

Each analysis record should capture:

```json
{
  "tap_timestamp": null,
  "capture_ms": null,
  "preprocess_ms": null,
  "payload_bytes": null,
  "request_body_bytes": null,
  "network_and_server_ms": null,
  "server_total_ms": null,
  "client_network_overhead_ms": null,
  "render_ms": null,
  "tap_to_overlay_ms": null,
  "bbox_overlay_correct": null,
  "crash": null,
  "freeze": null,
  "duplicate_request": null,
  "notes": ""
}
```

Engineering targets are tap-to-overlay P50 <= 4 s and P95 <= 6 s, zero obvious rotation/mirror/
overlay errors, format success >= 90%, bbox safety pass >= 80%, product usable >= 70%, and zero
crashes, freezes, or duplicate requests across ten analyses. These are targets only; current real
device results remain unmeasured.
