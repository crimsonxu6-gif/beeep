# Beeep Photography Evaluation Report

> Results are separated into subject preflight, deterministic GuidanceAdapter fixture, and live ShutterMuse API layers.
> Fixture output is not evidence of ShutterMuse composition quality.

## Dataset

- Local image library: 36 ({'public_real': 10, 'ai_generated': 10, 'transformed': 16})
- Subject preflight cases: 30 ({'public_real': 10, 'ai_generated': 10, 'transformed': 10})
- Composition cases: 20
- Covered subject scenarios: 25

## 1. Subject Preflight

- Final fail-open gate: {'false_negative': 0, 'false_positive': 5, 'true_negative': 0, 'true_positive': 25}
- Face-only FN: 7
- Face + Pose cascade: {'false_negative': 2, 'false_positive': 2, 'true_negative': 3, 'true_positive': 23}
- Final person-present block rate: 0.0%
- P50/P95: 18.0 / 74.0 ms

## 2. GuidanceAdapter Fixture

This layer verifies deterministic bbox-to-action conversion only.

- Total: 20
- Bbox parse success: 100.0%
- Fixture direction match: 100.0%
- Contradictory actions: 0
- Wrong direction: 0 / 20 (0.0%)

### Fixture Samples

- `comp_001` front_face: 这个构图不错，可以拍了
- `comp_002` side_profile: 镜头稍微往左移 / 让人物再大一些
- `comp_003` back_view: 镜头稍微往右移 / 让人物再大一些
- `comp_004` looking_down: 取景稍微往上移
- `comp_005` hat: 取景稍微往下移
- `comp_006` sunglasses: 让人物再大一些
- `comp_007` multiple_people: 换个角度再试试
- `comp_008` empty_room: 换个角度再试试
- `comp_009` mask: 这个构图不错，可以拍了
- `comp_010` full_body: 镜头稍微往右移

## 3. ShutterMuse API

- Total: 20
- Run ID: -
- API success: 11 / 20 (55.0%)
- Bbox parse: 11 / 20 (55.0%)
- Invalid output: 9 / 20 (45.0%)
- Decision distribution: {'keep': 4, 'refine': 7}
- Coordinate sources: {'official_1000': 11}
- Parse failures: {}
- Parser comparison: {}
- Errors: {'INVALID_MODEL_OUTPUT': 9}
- Generated tokens mean/P50/P95: None / None / None
- Reached max tokens: 0
- Output truncated: 0
- Human-reviewed direction correct: 90.9%
- Human-reviewed wrong direction: 1 / 11 (9.1%)
- Human-reviewed primary action helpful: 72.7%
- Human-reviewed secondary action helpful: 0.0%
- Guidance P50/P95: 6455.0 / 8396.0 ms
- Total P50/P95: 6465.0 / 8404.0 ms
- Human review: 20 reviewed, 0 pending
- Bbox quality mean/median: 3.455 / 4.0
- Output usable: 11 / 20 (55.0%)
- Product usable: 8 / 20 (40.0%)

### API Samples

- `comp_001` front_face: no action
- `comp_002` side_profile: 这个构图不错，可以拍了
- `comp_003` back_view: 让人物再大一些
- `comp_004` looking_down: no action
- `comp_005` hat: 让人物再大一些
- `comp_006` sunglasses: 这个构图不错，可以拍了
- `comp_007` multiple_people: 构图稍微调整一下
- `comp_008` empty_room: no action
- `comp_009` mask: no action
- `comp_010` full_body: 这个构图不错，可以拍了

## Minimum True-device Preflight Validation (9)

- 正面半身与正面全身
- 大侧脸与完全背影
- 手部遮脸或口罩加帽子
- 真实弱光与强逆光
- 人物很远且占画面很小
- 三人以上且人物贴近边缘
- 前置摄像头水平镜像
- 走动中的轻度运动模糊
- 短暂出框后 1.5 秒内重新进入

## Minimum True-device Composition Validation (6)

- 推荐框偏左和偏右时，用户实际移动方向
- 推荐框偏上和偏下时，取景移动语义
- 人物过小时“让人物再大一些”的可执行性
- 水平移动加距离调整的双指令可执行性
- 模型 keep 时是否应该立即拍摄
- 连续十帧中构图框和主建议的稳定性

## Limitations

- AI-generated images provide boundary coverage and are not the only quality source.
- Public and transformed images do not replace real sensor, motion, lens, or front-camera behavior.
- Human review scores apply only to the archived model outputs that were actually inspected.
- The 9 preflight and 6 composition scenarios above still require true-device validation.
