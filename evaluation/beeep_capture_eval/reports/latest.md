# Beeep Offline Evaluation Report

> This report uses local MediaPipe for preflight and deterministic bbox fixtures for Adapter validation. 
> It does not claim ShutterMuse model quality; run composition evaluation in `api` mode for that.

## Dataset

- Local image library: 36 ({'public_real': 10, 'ai_generated': 10, 'transformed': 16})
- Subject preflight cases: 30 ({'public_real': 10, 'ai_generated': 10, 'transformed': 10})
- Composition action cases: 20
- Covered subject scenarios: 25

## Subject Preflight

- Confusion matrix: TP=18, TN=3, FP=2, FN=7
- Person-present block rate: 28.0%
- P50/P95 preflight: 17.0 ms / 24.0 ms
- False negatives: ['public_back_view', 'public_looking_down', 'public_hat', 'public_group', 'ai_back_view', 'ai_distant_tiny', 'tf_mirror_side']
- False positives: ['ai_mannequin_poster', 'tf_mirror_mannequin']

## Composition Adapter

- Evaluation mode: `fixture_adapter`
- Bbox parse success: 100.0%
- Direction correct: 100.0%
- Primary action correct: 100.0%
- Secondary action helpful: 100.0%
- Contradictory actions: 0
- Wrong direction rate: 0.0%
- P50/P95 guidance: 0.0 ms / 0.0 ms

## Guidance Samples

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

## Wrong Direction Cases

- none

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

- AI-generated images are boundary coverage, not the only quality source.
- Public images are license-checked at download time but are not guaranteed smartphone captures.
- Derived images simulate camera defects; they do not replace real sensor, motion, and lens behavior.
- The 9 preflight and 6 composition scenarios above still require manual true-device validation.
