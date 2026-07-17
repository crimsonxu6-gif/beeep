# Beeep Android Emulator Validation

> Simulator validation only. Not real-device camera validation.

## Result

Android Studio Emulator was used with bundled Fixture input. No physical camera validation was
performed. Timing data is logic-only and must not be reported as phone performance.

The 12-scenario emulator matrix passed 12/12 with no failed scenario. A real Android multipart
request reached the Beeep FastAPI backend and rendered an overlay using the rules engine. The real
ShutterMuse single-image path remains `NOT_RUN` because the current machine was not running the GPU
model service during this emulator pass.

Tested source commit:

```text
1db65f1df6ea9f218b2c1a0f647697b7a57e0d70
```

## Toolchain

```text
Android Studio: 2026.1.2 (AI-261.25134.95.2612.15822958)
SDK: D:\Android\Sdk
ADB: 37.0.0-14910828
Emulator: 36.6.11.0
Hypervisor: AEHD 2.2, running
AVD: Beeep_Pixel_7_API_34
Device: Pixel 7, API 34, x86_64, 1080x2400
ADB serial: emulator-5554
```

Only the official Android SDK hypervisor installer at
`D:\Android\Sdk\extras\google\Android_Emulator_Hypervisor_Driver\silent_install_safe.bat`
was used. SDK, AVD, Gradle cache, JDK, Expo temporary files, and build output are located on `D:`.

## Build And Launch

The project has no committed hand-maintained Android source, so prebuild regeneration is expected.
The non-ASCII Windows profile requires an ASCII temporary directory, and the native build requires
Java 17:

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
cd ..
adb install -r android\app\build\outputs\apk\debug\app-debug.apk
adb reverse tcp:8081 tcp:8081
adb reverse tcp:8000 tcp:8000
```

Results:

```text
Prebuild: PASS
Gradle assembleDebug: PASS
APK: android/app/build/outputs/apk/debug/app-debug.apk
APK bytes: 188,375,105
Install: PASS
Launch: PASS
Android JS bundle: PASS, 2,538 modules
```

The Expo development floating tools button is disabled for this build, while the dedicated Beeep
debug panel remains available when `EXPO_PUBLIC_DEBUG_PANEL=1`.

## Fixture Mode

```env
EXPO_PUBLIC_ENABLE_ANALYSIS_FIXTURE=1
EXPO_PUBLIC_ANALYSIS_FIXTURE_SOURCE=bundled
EXPO_PUBLIC_ANALYSIS_API_MODE=mock_success
EXPO_PUBLIC_ANALYSIS_UPLOAD_MODE=multipart
EXPO_PUBLIC_DEBUG_PANEL=1
```

Restart Metro after changing Expo public variables. Production still forces Fixture and Mock API
modes off.

Camera, Fixture, and Gallery use the same path:

```text
AnalysisSourceFrame
-> AnalysisFrameController.processAnalysisSourceFrame
-> ImageManipulator preprocessing
-> multipart or Base64 transport
-> response parser
-> bbox coordinate conversion
-> GuidanceOverlay
```

Eight AI-generated development fixtures are committed. They are protocol fixtures, not real camera
inputs and not a ShutterMuse quality benchmark.

| Fixture | Source | Source bytes | Processed | JPEG bytes | Preprocess |
|---|---:|---:|---:|---:|---:|
| front_portrait | 960x1280 | 156,696 | 768x1024 | 82,017 | 214ms first run |
| full_body | 960x1280 | 190,234 | 768x1024 | 96,129 | 45ms |
| side_profile | 960x1280 | 167,607 | 768x1024 | 92,520 | 43ms |
| back_view | 960x1280 | 364,802 | 768x1024 | 196,241 | 54ms |
| group_edge | 960x1280 | 196,838 | 768x1024 | 114,733 | 52ms |
| looking_down | 960x1280 | 124,606 | 768x1024 | 65,706 | 45ms |
| landscape_group | 1280x960 | 284,595 | 1024x768 | 106,462 | 31ms |
| large_portrait | 3024x4032 | 1,174,344 | 768x1024 | 78,823 | 123ms |

All eight native preprocessing runs produced non-empty JPEG files, preserved aspect ratio, and had
a 768-pixel short edge. No crash was observed. Real memory pressure was not measured.

## Multipart And HTTP

Expo 57 requires a real `expo-file-system` `File`/`Blob` in FormData. A legacy React Native URI
object failed before reaching the backend, so the client now appends `new File(uri)` and has a
regression test for this behavior.

The successful Android request used:

```text
Transport: multipart
Endpoint: http://127.0.0.1:8000/v1/analyze through adb reverse
HTTP: 200
Processed image bytes: 82,017
Estimated request body bytes: 84,975
Server total: 42ms
Network and server: 178ms
tap_to_overlay: 282ms, logic-only
```

`estimatedRequestBodyBytes` is an estimate, not measured wire bytes.

The development-only backend debug endpoint was exercised through real Android `fetch` for HTTP
500, 502, 503, 504, invalid JSON, missing bbox, bbox safety rejection, and delayed success. Every
case recovered the analysis button, did not retry automatically, and did not draw an invalid bbox.

`simulated_pre_request_delay` is only a 2.5-second delay before `fetch`.
`simulated_offline_before_fetch` throws before `fetch`. These Mock profiles validate UI mapping and
are not low-bandwidth or Android network-stack measurements.

## Scenario Matrix

1. Front portrait, rear semantics, portrait: `PASS`.
2. Front portrait, front mirror, portrait: `PASS`.
3. Side profile, rear semantics, portrait: `PASS`.
4. Back view, rear semantics, portrait: `PASS`.
5. Full body, rear semantics, 9:16: `PASS`.
6. Group, rear semantics, 3:4: `PASS`.
7. True landscape input in portrait preview: `PASS`.
8. Portrait input in landscape preview: `PASS`; debug-only text was constrained in the narrow preview.
9. Mock success: `PASS`.
10. Mock error: `PASS`.
11. Mock timeout: `PASS`.
12. Live backend multipart success with rules guidance: `PASS`.

Summary: `12 PASS`, `0 FAIL`, `0 NOT_RUN`. Real ShutterMuse single-image execution is tracked
separately as `NOT_RUN: SHUTTERMUSE_RESOURCE_UNAVAILABLE`.

Mirror symmetry, portrait/landscape recalculation, aspect-fill cropping, bbox bounds, duplicate-click
protection, timeout recovery, and stale-request behavior passed their automated and visual emulator
checks. Timing samples were 95ms, 111ms, 282ms, and 2678ms; the last value is the intentional delayed
response. These values validate instrumentation only.

## Automated Verification

```text
Frontend typecheck, lint, Vitest: 61 passed
Backend pytest: 65 passed
Evaluation pytest: 17 passed
Model-service pytest: 51 passed
Backend ruff: PASS
Model-service ruff: PASS
Total tests: 194 passed
Android export: PASS, 2,538 modules
```

## Real-Device Boundary

The following remain `DEVICE_REQUIRED`: physical `expo-camera` capture, EXIF and sensor orientation,
actual front-camera mirroring, autofocus, exposure, weak light, backlight, motion blur, real capture
and preprocessing latency, memory, heat, battery, real upload performance, real `tap_to_overlay`
P50/P95, and real preview-to-saved-image bbox alignment.

The 24GB GPU ShutterMuse benchmark also remains pending. Continue with `REAL_DEVICE_TESTING.md` for
physical-device acceptance; simulator math and visualization do not satisfy those checks.
