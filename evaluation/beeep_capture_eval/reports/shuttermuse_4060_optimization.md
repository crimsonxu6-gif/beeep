# RTX 4060 laptop optimization notes

Date: 2026-07-14

This file records observed engineering results only. It is not a production benchmark and does
not replace the per-run API archives.

## Previous 1024 baseline

- Environment: RTX 4060 Laptop 8 GB, 4-bit NF4, CPU offload, official prompt.
- Latest completed 20-image run: 11 successes, 9 `INVALID_MODEL_OUTPUT` failures.
- Bbox parse rate: 55%.
- Guidance P50/P95: 6455/8396 ms.
- Total P50/P95: 6465/8404 ms.
- Model lifetime across three runs: 60 inferences, `load_count=1`.

The old run did not capture raw model output, so its nine failures cannot be assigned a truthful
fine-grained cause after the fact.

## Current diagnostic attempts

| Configuration | Result | Observed cause |
|---|---|---|
| 1024 / default / 96 | warmup failed | CUDA OOM while SDPA requested another 66 MiB |
| 768 / SDPA / 48 | generation completed in about 5.3 s; readiness failed | `OUTPUT_TRUNCATED` inside `instance_info.reason` |
| 768 / SDPA / 96 | generation completed in about 8.6 s; readiness failed | `OUTPUT_TRUNCATED` inside the second `composition_xy` coordinate |
| 768 / SDPA / 256 | model reload could not complete | Windows process terminated under current 16 GB host-memory pressure |
| 640 / SDPA / 48 | not run | 48-token truncation already invalidated the candidate before quality comparison |

The 48/96 observations prove that this checkpoint can ignore the concise pair contract and emit a
verbose training JSON envelope. They do not prove that 4-bit quantization is the root cause. A full
20-image Baseline/A/B matrix and repeatability run still require a clean host session or a 24 GB GPU.

## Existing visual review

The eleven legal boxes from the previous completed run were inspected against their overlays:

- Format-usable output: 11/20 (55%).
- Human-reviewed legal boxes: 11/11.
- Mean bbox quality among legal boxes: 3.45/5.
- Product-usable output (`quality >= 3`): 8/20 (40%).
- Three legal boxes scored below 3 because of body/head cuts or poor subject preservation.

Nine format failures remain excluded from visual-quality averaging rather than being assigned a
fabricated score of 1.
