# Beeep Android Emulator Validation

> Simulator validation only. Not real-device camera validation.

## Purpose

The development-only analysis fixture sends bundled or gallery images through the same
`AnalysisSourceFrame -> AnalysisFrameController -> multipart -> /v1/analyze -> GuidancePipeline -> overlay`
path used by camera analysis. It validates protocol, state, preprocessing configuration, and
coordinate math without claiming physical-camera behavior or phone performance.

## Enable

```env
EXPO_PUBLIC_ENABLE_ANALYSIS_FIXTURE=1
EXPO_PUBLIC_ANALYSIS_FIXTURE_SOURCE=bundled
EXPO_PUBLIC_ANALYSIS_API_MODE=mock_success
EXPO_PUBLIC_ANALYSIS_UPLOAD_MODE=multipart
EXPO_PUBLIC_DEBUG_PANEL=1
```

Restart Metro after changing Expo public environment variables. In the camera workspace, tap the
flask icon to select a bundled image or emulator gallery image, front/rear semantics, upload-image
mirroring, orientation, preview ratio, simulated device size, transport, API mode, and network
profile. Tap `分析构图` to submit exactly one request.

## API modes

- `live`: performs the real multipart or Base64 request to `/v1/analyze`.
- `live_debug`: performs a real Android HTTP request to the development-only response endpoint.
- `mock_success`: deterministic bbox `[0.15, 0.1, 0.8, 0.9]` and one primary action.
- `mock_error`: structured `INVALID_MODEL_OUTPUT` error.
- `mock_timeout`: waits past the normal client timeout and exercises abort recovery.

`simulated_pre_request_delay` adds 2.5 seconds before submission.
`simulated_offline_before_fetch` throws before `fetch`. These are UI-state simulations, not real
low-bandwidth or Android network-stack measurements. No mode automatically retries. With
`live_debug`, the error selector covers real HTTP 500/502/503/504 responses, invalid JSON, missing
bbox, delayed success, and bbox safety rejection.

## Fixture set

Eight AI-generated development images are committed under `assets/analysis-fixtures`: front portrait,
distant full body, side profile, back view, group at the edge, looking down, a real landscape input,
and a 3024 x 4032 high-resolution portrait. Exact source dimensions and bytes are stored in
`manifest.json`. They are protocol fixtures, not a ShutterMuse quality benchmark.

## Android development build

The repository is an Expo managed project with no committed native Android directory or manual
native edits, so clean prebuild is the intended local workflow:

```powershell
$env:TEMP="D:\beeep\.codex\tmp-expo"
$env:TMP=$env:TEMP
npx expo prebuild --clean --platform android
npx expo run:android
```

On this Windows account the ASCII `TEMP/TMP` override is required because Expo template extraction
exited early under the default non-ASCII user temp path. Clean prebuild completed with this override.

The Android Studio 2026.1.2 toolchain is installed with SDK and AVD data on `D:`:

```text
SDK: D:\Android\Sdk
ADB: 37.0.0-14910828
Emulator: 36.6.11.0
AVD: Beeep_Pixel_7_API_34 (Pixel 7, API 34, x86_64, 1080x2400)
```

Clean prebuild and `assembleDebug` passed. The generated APK is
`android/app/build/outputs/apk/debug/app-debug.apk` (188,374,933 bytes). The build uses a local
Microsoft OpenJDK 17 toolchain because the Android Studio JBR is Java 21 while the React Native
Gradle plugin requests Java 17.

The emulator cannot boot until the Android Emulator Hypervisor Driver is installed with Windows
administrator approval. APK install, app launch, native Fixture preprocessing, Android multipart,
and the twelve visual scenarios therefore remain `NOT_RUN`; the report records
`HYPERVISOR_DRIVER_REQUIRES_ADMIN_APPROVAL`. Host-side HTTP debug endpoint checks are reported
separately and are not Android fetch validation.

## Minimum emulator matrix

1. Front portrait, rear semantics, portrait.
2. Front portrait, front mirrored preview, portrait.
3. Side profile, rear, portrait.
4. Back view, rear, portrait.
5. Full body, rear, 9:16.
6. Group, rear, 3:4.
7. Landscape input in portrait preview.
8. Portrait input in landscape preview.
9. Mock success.
10. Mock error.
11. Mock timeout.
12. One live API success.

## Real-device boundary

Physical camera capture, EXIF behavior, actual front-camera mirroring, autofocus, exposure, weak
light, motion blur, memory, heat, upload performance, and real `tap_to_overlay` P50/P95 remain
`DEVICE_REQUIRED`. Continue using `REAL_DEVICE_TESTING.md`; emulator results must not mark those
items as passed.
