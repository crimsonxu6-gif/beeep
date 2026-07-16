import { Modal, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { ImagePlus, RotateCcw, X } from "lucide-react-native";

import { AnalysisFixture } from "@/camera/analysisFixtures";
import {
  FIXTURE_DEVICE_PRESETS,
  FIXTURE_PREVIEW_RATIOS,
  FixtureSessionSettings
} from "@/camera/fixtureSession";

interface Props {
  visible: boolean;
  settings: FixtureSessionSettings;
  fixtures: readonly AnalysisFixture[];
  error: string | null;
  onChange: (patch: Partial<FixtureSessionSettings>) => void;
  onPickGallery: () => void;
  onClear: () => void;
  onClose: () => void;
}

function Choice<T extends string>({ value, current, label, onSelect }: {
  value: T;
  current: T;
  label: string;
  onSelect: (value: T) => void;
}) {
  return (
    <Pressable style={[styles.choice, value === current && styles.choiceActive]} onPress={() => onSelect(value)}>
      <Text style={[styles.choiceText, value === current && styles.choiceTextActive]}>{label}</Text>
    </Pressable>
  );
}

export function AnalysisFixtureControls({
  visible,
  settings,
  fixtures,
  error,
  onChange,
  onPickGallery,
  onClear,
  onClose
}: Props) {
  return (
    <Modal visible={visible} animationType="slide" transparent onRequestClose={onClose}>
      <View style={styles.scrim}>
        <View style={styles.sheet}>
          <View style={styles.header}>
            <View>
              <Text style={styles.title}>模拟分析</Text>
              <Text style={styles.subtitle}>Simulator validation only</Text>
            </View>
            <Pressable style={styles.iconButton} onPress={onClose} accessibilityLabel="关闭模拟分析">
              <X color="#fff" size={20} />
            </Pressable>
          </View>
          <ScrollView contentContainerStyle={styles.content}>
            <Text style={styles.label}>测试图片</Text>
            <View style={styles.wrap}>
              {fixtures.map((fixture) => (
                <Choice key={fixture.id} value={fixture.id} current={settings.fixtureId} label={fixture.label} onSelect={(fixtureId) => onChange({ fixtureId })} />
              ))}
            </View>
            <Pressable style={styles.command} onPress={onPickGallery}>
              <ImagePlus color="#fff" size={18} />
              <Text style={styles.commandText}>从模拟器图库选择</Text>
            </Pressable>

            <Text style={styles.label}>摄像头语义</Text>
            <View style={styles.wrap}>
              <Choice value="back" current={settings.cameraFacing} label="模拟后置" onSelect={(cameraFacing) => onChange({ cameraFacing })} />
              <Choice value="front" current={settings.cameraFacing} label="模拟前置" onSelect={(cameraFacing) => onChange({ cameraFacing })} />
              <Choice value="false" current={String(settings.imageMirrored) as "true" | "false"} label="上传不镜像" onSelect={() => onChange({ imageMirrored: false })} />
              <Choice value="true" current={String(settings.imageMirrored) as "true" | "false"} label="上传镜像" onSelect={() => onChange({ imageMirrored: true })} />
            </View>

            <Text style={styles.label}>方向与预览比例</Text>
            <View style={styles.wrap}>
              <Choice value="portrait" current={settings.deviceOrientation === "portrait" ? "portrait" : "landscape_right"} label="竖屏" onSelect={() => onChange({ deviceOrientation: "portrait" })} />
              <Choice value="landscape_right" current={settings.deviceOrientation === "portrait" ? "portrait" : "landscape_right"} label="横屏" onSelect={() => onChange({ deviceOrientation: "landscape_right" })} />
              {FIXTURE_PREVIEW_RATIOS.map((ratio) => <Choice key={ratio} value={ratio} current={settings.previewRatio} label={ratio} onSelect={(previewRatio) => onChange({ previewRatio })} />)}
            </View>

            <Text style={styles.label}>模拟设备</Text>
            <View style={styles.wrap}>
              {FIXTURE_DEVICE_PRESETS.map((device) => <Choice key={device.id} value={device.id} current={settings.devicePresetId} label={device.label} onSelect={(devicePresetId) => onChange({ devicePresetId })} />)}
            </View>

            <Text style={styles.label}>上传与 API</Text>
            <View style={styles.wrap}>
              <Choice value="multipart" current={settings.uploadMode} label="multipart" onSelect={(uploadMode) => onChange({ uploadMode })} />
              <Choice value="base64_json" current={settings.uploadMode} label="base64 JSON" onSelect={(uploadMode) => onChange({ uploadMode })} />
              {(["live", "live_debug", "mock_success", "mock_error", "mock_timeout"] as const).map((apiMode) => <Choice key={apiMode} value={apiMode} current={settings.apiMode} label={apiMode} onSelect={(value) => onChange({ apiMode: value })} />)}
            </View>

            <Text style={styles.label}>网络</Text>
            <View style={styles.wrap}>
              {(["normal", "simulated_pre_request_delay", "simulated_offline_before_fetch"] as const).map((networkProfile) => <Choice key={networkProfile} value={networkProfile} current={settings.networkProfile} label={networkProfile} onSelect={(value) => onChange({ networkProfile: value })} />)}
            </View>
            <Text style={styles.label}>错误子场景</Text>
            <View style={styles.wrap}>
              {(["success", "delayed_success", "invalid_model_output", "http_500", "http_502", "http_503", "http_504", "invalid_json", "missing_bbox", "bbox_safety_rejected"] as const).map((failureScenario) => (
                <Choice key={failureScenario} value={failureScenario} current={settings.failureScenario} label={failureScenario} onSelect={(value) => onChange({ failureScenario: value })} />
              ))}
            </View>
            {error ? <Text style={styles.error}>{error}</Text> : null}
            <Pressable style={styles.command} onPress={onClear}>
              <RotateCcw color="#fff" size={18} />
              <Text style={styles.commandText}>清除分析结果</Text>
            </Pressable>
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  scrim: { flex: 1, justifyContent: "flex-end", backgroundColor: "rgba(0,0,0,0.48)" },
  sheet: { maxHeight: "88%", backgroundColor: "#15171a", borderTopLeftRadius: 8, borderTopRightRadius: 8 },
  header: { minHeight: 72, paddingHorizontal: 18, flexDirection: "row", alignItems: "center", justifyContent: "space-between", borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: "rgba(255,255,255,0.14)" },
  title: { color: "#fff", fontSize: 18, fontWeight: "800" },
  subtitle: { color: "rgba(255,255,255,0.58)", fontSize: 12, marginTop: 3 },
  iconButton: { width: 38, height: 38, alignItems: "center", justifyContent: "center" },
  content: { padding: 18, paddingBottom: 40, gap: 10 },
  label: { color: "rgba(255,255,255,0.62)", fontSize: 12, fontWeight: "700", marginTop: 8 },
  wrap: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  choice: { minHeight: 34, justifyContent: "center", paddingHorizontal: 11, borderWidth: 1, borderColor: "rgba(255,255,255,0.18)", borderRadius: 6 },
  choiceActive: { backgroundColor: "#fff", borderColor: "#fff" },
  choiceText: { color: "rgba(255,255,255,0.76)", fontSize: 12, fontWeight: "700" },
  choiceTextActive: { color: "#111" },
  command: { minHeight: 42, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8, borderRadius: 6, backgroundColor: "rgba(255,255,255,0.12)", marginTop: 4 },
  commandText: { color: "#fff", fontSize: 13, fontWeight: "700" },
  error: { color: "#ff9d9d", fontSize: 12 }
});
