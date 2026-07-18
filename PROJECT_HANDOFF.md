# Beeep 项目交接文档

> 给新的 Codex 窗口：先读完本文件，再执行 `git status --short --branch`。不要根据早期聊天记录重复实现已经完成的模块。

## 1. 项目快照

- 仓库：`https://github.com/crimsonxu6-gif/beeep`
- 主分支：`main`
- 最后完整验证的代码提交：`57b258c0597e4f5427a528bbd82e63531b0febac`
- 产品名称：Beeep AI Photo Coach
- 技术栈：Expo 57、React Native、TypeScript、FastAPI、MediaPipe、ShutterMuse GPU 服务
- 当前产品阶段：MVP 闭环和工程验证已完成，正在验证真实 ShutterMuse 构图质量及真机体验
- 默认交互：首页进入 App；点击首页拍照按钮进入相机；相机默认采用手动“分析构图”模式

## 2. 产品目标

Beeep 是移动端 AI 摄影教练。用户举起手机后，系统分析当前画面，并告诉用户下一步如何调整。

用户应该看到：

- 一个推荐构图框；
- 一个最重要的短指令；
- 必要时一个次指令；
- 可理解的 AI 状态或错误提示。

用户不应该看到：

- AI 推理过程；
- 长篇摄影点评；
- 摄影术语教学；
- 模型故障时伪造的摄影建议；
- 不稳定、每帧变化的方向指令。

核心产品原则：

1. 每次最多给一至两个可执行动作。
2. ShutterMuse 只推荐构图决策和 `bbox_norm`，最终中文文案由 Beeep 确定性生成。
3. `GUIDANCE_ENGINE=shuttermuse` 时，模型故障不得静默降级为 rules。
4. Mock 仅允许开发环境显式开启，生产环境强制关闭。
5. 不安全或非法 bbox 不修复、不伪造、不绘制。
6. 当前模型速度不适合逐帧调用，默认使用手动分析交互。

## 3. 当前完整链路

```text
首页
  -> 相机工作区
  -> 用户点击“分析构图”
  -> 捕获低质量分析图
  -> 方向纠正、等比缩放到短边 768、JPEG 0.7
  -> multipart POST /v1/analyze
  -> MediaPipe Face + Pose 级联主体预检测
  -> rules 或 ShutterMuse Guidance Service
  -> ShutterMuse decision + bbox_norm
  -> bbox 安全校验
  -> GuidanceAdapter 生成一至两个中文动作
  -> latest-wins、旧 frameId 丢弃、稳定过滤、建议过期
  -> 推荐框、主指令和状态 Overlay
```

最终拍照使用独立高质量链路：

```text
按快门
  -> 暂停分析
  -> 高质量拍照
  -> 照片预览
  -> 重拍 / 保存 / 返回相机 / 图库选择
```

## 4. 模块职责

### 手机端 `src/`

- `application/`：App 状态、指导控制器、拍照控制器。
- `camera/`：分析帧和最终照片分离、Fixture/Camera/Gallery 统一输入、帧采样。
- `ai_engine/`：HTTP client、JSON parser、latest-wins pipeline、开发 Mock。
- `stability/`：多帧一致性、旧结果保护、建议 TTL。
- `components/`：GuidanceOverlay、构图框、姿势骨架、调试面板。
- `screens/`：首页、相机工作区、照片预览等现有页面。
- `vision/`：手机端视觉输入接口和未来原生视觉层边界。

### Beeep 后端 `backend/`

- `api/analyze.py`：统一 `POST /v1/analyze`，图片只上传一次。
- `vision/`：完整 MediaPipe processor、轻量主体 preflight、连续帧 presence gate。
- `services/rule_guidance_service.py`：本地开发规则引擎。
- `services/shuttermuse_service.py`：调用独立 GPU 模型服务。
- `services/guidance_adapter.py`：bbox 到稳定中文动作。
- `core/`：配置、错误、request_id、安全限制和日志上下文。

### GPU 模型服务 `model-service/`

- 模型和 Processor 只加载一次。
- 启动时 warmup，并区分 `runtime_ready` 与 `quality_ready`。
- 单 GPU 同时只运行一个推理，最多保留一个可替换待处理请求。
- 支持官方 Prompt、bbox-first、prefill 和 Beeep JSON 实验模式。
- 保存评测原始输出仅由显式环境变量开启，生产默认关闭。
- Parser 不从任意长文本抓数字，不交换坐标，不修复非法 bbox。

### 评测 `evaluation/beeep_capture_eval/`

- 30 个主体预检测场景。
- 20 个确定性 bbox-to-action fixture。
- 20 个真实 ShutterMuse API 构图场景。
- Android Emulator Fixture 和真实设备验收清单。
- 图片原文件大部分被 gitignore；仓库只保留允许提交的 Fixture、manifest、脚本和报告。

## 5. 已完成能力

### 移动端

- Expo + React Native + TypeScript 工程。
- 默认首页和首页拍照入口。
- 全屏相机、细直线三分法网格、方向指令、推荐构图框。
- 闪光动画和快门音效已关闭。
- 手动、`stable_auto` 配置边界和开发用 `continuous` 三种触发模式。
- 分析中禁用重复点击，超过两秒显示分阶段等待文案。
- Camera、Fixture、Gallery 共用 `AnalysisSourceFrame` 和正式预处理链路。
- 短边 768、JPEG 0.7、multipart 默认上传；Base64 JSON 仅保留回归模式。
- 前置镜像、横竖屏、aspect-fill 和 overlay 坐标转换。
- latest-wins、旧 frameId 丢弃、页面退出取消、稳定过滤和 TTL。
- 拍照、照片预览、保存、重拍和图库选择闭环。
- Debug Panel 显示请求、frame、预检测、延迟、动作和引擎状态。
- 生产环境强制关闭 Fixture、Mock API 和调试后端。

### 后端

- FastAPI 统一接口 `POST /v1/analyze`。
- 图片 MIME、字节数、最长边、总像素限制。
- request_id、CORS 环境配置、API Key 预留、health/readiness。
- MediaPipe 实例复用和并发锁。
- rules 与 ShutterMuse service interface 分离。
- Face 优先、Face 弱时 Pose 的级联预检测。
- `confirmed / uncertain / missing` 三态和连续帧历史。
- `uncertain` 永远 fail-open；`SUBJECT_PREFLIGHT_BLOCKING=0` 为当前默认。
- ShutterMuse 错误返回结构化用户状态，不使用 rules 伪装。
- GuidanceAdapter 候选动作评分和最多两条不冲突动作。
- 构图框的人脸、主体、全身完整性、目标比例和最小面积安全检查。

### ShutterMuse 模型服务

- 官方已训练权重加载接口。
- 4-bit NF4、CPU offload、BF16 配置边界。
- 模型只加载一次，warmup 后 readiness。
- 有界 GPU 队列和 `MODEL_BUSY` 状态。
- 固定贪心解码：`do_sample=False`、`num_beams=1`。
- 官方坐标、JSON bbox、`composition_bbox`、`composition_xy` 等明确格式解析。
- 空输出、占位符、截断、非法几何和非法范围细分错误。
- 原始输出归档、run ID、重复稳定性和参数矩阵评测工具。

## 6. 已验证结果

### 自动化测试基线

最后验证于 2026-07-17：

```text
前端 TypeScript / ESLint / Vitest：61 passed
Beeep 后端 pytest：65 passed
评测工具 pytest：17 passed
模型服务 pytest：51 passed
总计：194 passed
Backend ruff：PASS
Model-service ruff：PASS
Android JS bundle：PASS，2538 modules
```

### Android Studio Emulator

环境：

```text
Android Studio 2026.1.2
SDK D:\Android\Sdk
ADB 37.0.0-14910828
Emulator 36.6.11.0
AEHD 2.2
AVD Beeep_Pixel_7_API_34
Pixel 7 / API 34 / x86_64 / 1080x2400
```

结果：

```text
Development APK build：PASS
Install：PASS
Launch：PASS
8/8 Fixture 原生预处理：PASS
真实 Android multipart -> Beeep rules backend：1/1 PASS
HTTP 500/502/503/504、非法 JSON、缺 bbox、延迟响应：PASS
模拟器最小场景：12 PASS / 0 FAIL / 0 NOT_RUN
```

这只证明原生模块、协议、错误恢复、坐标数学和 UI 状态可运行，不是真实相机或手机性能验收。

详细报告：`evaluation/beeep_capture_eval/reports/simulator_latest.json`。

### Redmi 9A 物理 Android 部分验收

2026-07-18 在 Redmi 9A（Android 10 / API 29、2 GB、720x1600）完成首轮物理设备验证：

```text
Development APK 安装、启动：PASS
后置/前置相机打开：PASS
后置真实 multipart 请求：PASS，capture 1255 ms / preprocess 572 ms / HTTP 200
前置真实 multipart 请求：PASS，capture 709 ms / preprocess 185 ms / HTTP 200
连续 10 次手动分析：10/10 请求，frame 12/12/12，stale 0，无崩溃或冻结
快速双击：只产生 1 个后端请求，PASS
高质量拍照 -> 预览 -> 重拍：PASS，未保存测试照片
图库选择 -> 预览：PASS
```

这轮通过 ADB reverse 连接本机 rules 后端，不是 Wi-Fi 性能或 ShutterMuse 质量评测。横屏只做了
ADB 强制 UI 旋转，手机没有物理旋转；镜像、四角 bbox、真实横屏、场景矩阵、逐次内存和 Overlay
时序仍未验收。因此真机 P0 仍是部分完成。详细机器报告：
`evaluation/beeep_capture_eval/reports/real_device_redmi9a_2026-07-18.json`。

### 主体预检测

相同 30 个离线场景：

```text
Face-only FN：7
Face + Pose cascade：TP 23 / TN 3 / FP 2 / FN 2
最终 fail-open gate：TP 25 / TN 0 / FP 5 / FN 0
人物存在阻断率：0%
P50 / P95：18 / 74 ms
```

级联仍会漏掉多人远景和人物极小场景，因此当前不得开启硬阻断。

### GuidanceAdapter fixture

```text
bbox parse：100%
主方向匹配：100%
次建议匹配：100%
错误方向：0 / 20
冲突动作：0
```

这只证明固定 bbox 到动作的确定性逻辑，不能描述为 ShutterMuse 模型质量。

## 7. 真实 ShutterMuse 当前状态

RTX 4060 Laptop 8GB、4-bit NF4、CPU offload、官方 Prompt 的最近完整 20 图结果：

```text
API / bbox 成功：11 / 20（55%）
INVALID_MODEL_OUTPUT：9 / 20
decision：keep 4 / refine 7
Guidance P50 / P95：6455 / 8396 ms
合法 bbox 人工审查：11 / 11
合法 bbox 平均质量：3.45 / 5
产品可用：8 / 20（40%）
```

关键解释：

- 55% 是格式可解析率，不是构图准确率。
- 3.45 分只计算合法 bbox，不把格式失败伪造为 1 分。
- 当前 6 至 8 秒不应宣传为实时摄影指导。
- 模型三轮共 60 次推理，`load_count=1`，说明没有重复加载。
- 旧 9 个失败没有保存 raw output，不能事后编造细分失败原因。
- 768/SDPA/48 和 96 token 诊断出现 verbose JSON 截断；不能直接归因于 4-bit。
- 当前 8GB 数据是研究结果，不是生产基准。

详细记录：`evaluation/beeep_capture_eval/reports/shuttermuse_4060_optimization.md`。

## 8. 当前关键配置

手机端默认：

```env
EXPO_PUBLIC_ENABLE_MOCK=0
EXPO_PUBLIC_DEBUG_PANEL=0
EXPO_PUBLIC_GUIDANCE_TRIGGER_MODE=manual
EXPO_PUBLIC_ENABLE_SECONDARY_GUIDANCE=0
EXPO_PUBLIC_ANALYSIS_IMAGE_SHORT_EDGE=768
EXPO_PUBLIC_ANALYSIS_JPEG_QUALITY=0.7
EXPO_PUBLIC_ANALYSIS_UPLOAD_MODE=multipart
EXPO_PUBLIC_ENABLE_ANALYSIS_FIXTURE=0
EXPO_PUBLIC_ANALYSIS_API_MODE=live
```

后端默认：

```env
GUIDANCE_ENGINE=rules
SUBJECT_PREFLIGHT_ENABLED=1
SUBJECT_PREFLIGHT_BLOCKING=0
SUBJECT_PRESENCE_TTL_MS=1500
SUBJECT_MISSING_CONFIRM_FRAMES=3
```

模型服务默认值和所有配置见 `.env.example`。本地 `.env` / `.env.local` 不提交，不写入密钥或固定个人局域网 IP。

## 9. 常用启动方式

### 本地 rules 模式

```powershell
cd D:\beeep
.\.venv\Scripts\Activate.ps1
$env:GUIDANCE_ENGINE="rules"
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

另开终端：

```powershell
cd D:\beeep
npx expo start --dev-client
```

Android Emulator 使用 ADB reverse：

```powershell
adb reverse tcp:8081 tcp:8081
adb reverse tcp:8000 tcp:8000
```

### Android Development Build

本机 Windows 用户路径包含非 ASCII 字符，Gradle/Expo 临时目录必须使用 ASCII 路径：

```powershell
$env:TEMP="D:\beeep\.codex\tmp-expo"
$env:TMP=$env:TEMP
$env:ANDROID_HOME="D:\Android\Sdk"
$env:ANDROID_SDK_ROOT=$env:ANDROID_HOME
$env:JAVA_HOME="D:\Java\MicrosoftJDK17\PFiles64\Microsoft\jdk-17.0.19.10-hotspot"
$env:GRADLE_USER_HOME="D:\Android\GradleBuildCache"
$env:GRADLE_OPTS="-Djava.io.tmpdir=D:\beeep\.codex\tmp-expo"

npx expo prebuild --platform android --no-install
cd android
.\gradlew.bat --no-daemon clean assembleDebug
```

APK：`android/app/build/outputs/apk/debug/app-debug.apk`。

### 真实 ShutterMuse

启动模型服务后，只有 `/ready` 返回可用时才切换 Beeep 后端：

```env
GUIDANCE_ENGINE=shuttermuse
SHUTTERMUSE_SERVICE_URL=http://127.0.0.1:8100
```

不要在 ShutterMuse 失败时改成自动 rules fallback。

## 10. 下一阶段优先级

### P0：24GB GPU 真实模型基准

使用同一批 20 张图片、相同人工审查标准和独立 run ID，至少对比：

1. 4-bit 全 GPU、768、SDPA、合适 token 上限。
2. BF16 全 GPU、768、SDPA。
3. 条件允许时 BF16 + FlashAttention 2。

必须记录 API 成功率、raw output、失败分类、bbox 质量、人物保留、切头/切身体、P50/P95 和产品可用率。目标值只是工程目标，不能伪造达标。

### P0：真实 Android 手机验收

执行 `evaluation/beeep_capture_eval/REAL_DEVICE_TESTING.md`：

- 后置和前置摄像头；
- 竖屏和横屏；
- 真实镜像和四角 bbox 对齐；
- 弱光、逆光、运动模糊；
- 连续十次分析无重复请求、冻结和崩溃；
- 记录真实 capture、preprocess、upload、render 和 tap-to-overlay 数据。

### P1：根据真实模型证据优化

只有评测证明问题来源后，再调整 Prompt、Parser、token、输入尺寸或 GuidanceAdapter。不要因为单个样本直接重构。

### P2：姿势功能

Photographer-side 构图验证通过后，再接 ShutterMuse subject-side COCO-17 推荐姿势，并处理镜像、多人目标、可见性和当前姿势对比。

## 11. 暂时不要做

- 不重新训练或 LoRA 微调 ShutterMuse。
- 不开始会员、登录、订阅、社区和复杂首页。
- 不删除 MediaPipe。
- 不开启 `SUBJECT_PREFLIGHT_BLOCKING=1`。
- 不把 rules 作为 ShutterMuse 故障时的静默备用。
- 不把 fixture 100% 指标描述成模型质量。
- 不把 Emulator 延迟描述成真机性能。
- 不把 8GB 4-bit 结果描述成生产基准。
- 不自动修复、交换、裁剪或伪造非法 bbox。
- 不在许可证明确前宣称模型可商业使用。

## 12. 已知限制和风险

1. ShutterMuse 权重不在仓库中，需要官方 checkpoint。
2. 当前真实模型格式成功率和产品可用率尚未达标。
3. 物理手机的相机、镜像、性能、发热和 overlay 对齐尚未验收。
4. Subject-side 姿势推荐尚未接通。
5. MediaPipe 当前运行在后端，长期应迁移到手机轻量视觉层。
6. ShutterMuse 代码和权重许可证尚未明确，商业化仍被阻塞。
7. 当前自动采样仍依赖 `takePictureAsync`；长期应迁移 CameraX、AVFoundation 或原生 Frame Processor。

## 13. 关键文档

- 总体说明：`README.md`
- 本交接文档：`PROJECT_HANDOFF.md`
- 后端说明：`backend/README.md`
- 模型服务：`model-service/README.md`
- 评测说明：`evaluation/beeep_capture_eval/README.md`
- 模拟器实测：`evaluation/beeep_capture_eval/SIMULATOR_TESTING.md`
- 模拟器机器报告：`evaluation/beeep_capture_eval/reports/simulator_latest.json`
- 4060 优化记录：`evaluation/beeep_capture_eval/reports/shuttermuse_4060_optimization.md`
- 真机清单：`evaluation/beeep_capture_eval/REAL_DEVICE_TESTING.md`
- 环境变量：`.env.example`

## 14. 新窗口开始工作时

按以下顺序：

```powershell
cd D:\beeep
git status --short --branch
git pull --ff-only origin main
git log -5 --oneline
npm run check
```

然后阅读本文件和与任务直接相关的专项文档。先确认用户的新目标，再修改代码；不要重新实现已经列为完成的 latest-wins、拍照预览、Mock 策略、统一接口、主体 gate、模型服务、GuidanceAdapter、Fixture 工作流或 Emulator 验证。
