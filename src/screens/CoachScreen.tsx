import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { Activity, ArrowLeftRight, CircleDot, Lightbulb, ScanFace } from "lucide-react-native";

import { AppRoute } from "@/application/navigation";
import { colors, radii, typography } from "@/theme/design";
import { ToolHeader } from "@/ui/ToolHeader";

interface CoachScreenProps {
  onNavigate: (route: AppRoute) => void;
}

const checks = [
  { title: "主体位置", value: "中线偏右", Icon: CircleDot },
  { title: "镜头移动", value: "往右一点", Icon: ArrowLeftRight },
  { title: "姿势", value: "肩膀放松", Icon: ScanFace },
  { title: "光线", value: "避开逆光", Icon: Lightbulb }
];

export function CoachScreen({ onNavigate }: CoachScreenProps) {
  return (
    <View style={styles.root}>
      <ToolHeader title="构图" subtitle="实时建议" />
      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.content}>
        <View style={styles.canvas}>
          <View style={styles.ruleVertical} />
          <View style={[styles.ruleVertical, styles.ruleVerticalRight]} />
          <View style={styles.ruleHorizontal} />
          <View style={[styles.ruleHorizontal, styles.ruleHorizontalBottom]} />
          <View style={styles.subjectDot}>
            <Activity size={28} strokeWidth={2.3} color={colors.accent} />
          </View>
          <Text style={styles.canvasLabel}>画面</Text>
        </View>

        <View style={styles.actionRow}>
          <Pressable style={styles.captureButton} onPress={() => onNavigate("camera")}>
            <Text style={styles.captureButtonText}>拍照键</Text>
          </Pressable>
          <Pressable style={styles.secondaryButton} onPress={() => onNavigate("camera")}>
            <Text style={styles.secondaryButtonText}>姿势推荐</Text>
          </Pressable>
        </View>

        <View style={styles.checkList}>
          {checks.map(({ title, value, Icon }) => (
            <View key={title} style={styles.checkRow}>
              <View style={styles.checkIcon}>
                <Icon size={18} strokeWidth={2.1} color={colors.text} />
              </View>
              <Text style={styles.checkTitle}>{title}</Text>
              <Text style={styles.checkValue}>{value}</Text>
            </View>
          ))}
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    paddingTop: 54,
    paddingHorizontal: 18,
    backgroundColor: colors.background
  },
  content: {
    paddingTop: 20,
    paddingBottom: 118
  },
  canvas: {
    height: 420,
    overflow: "hidden",
    borderRadius: radii.md,
    borderWidth: 1,
    borderColor: colors.hairline,
    backgroundColor: colors.surface
  },
  canvasLabel: {
    position: "absolute",
    top: 18,
    alignSelf: "center",
    ...typography.section,
    color: colors.accent
  },
  ruleVertical: {
    position: "absolute",
    top: 0,
    bottom: 0,
    left: "33.333%",
    width: 1,
    backgroundColor: colors.hairline
  },
  ruleVerticalRight: {
    left: "66.666%"
  },
  ruleHorizontal: {
    position: "absolute",
    left: 0,
    right: 0,
    top: "33.333%",
    height: 1,
    backgroundColor: colors.hairline
  },
  ruleHorizontalBottom: {
    top: "66.666%"
  },
  subjectDot: {
    position: "absolute",
    left: "50%",
    top: "50%",
    width: 62,
    height: 62,
    alignItems: "center",
    justifyContent: "center",
    marginLeft: -31,
    marginTop: -31,
    borderRadius: radii.round,
    backgroundColor: colors.accentSoft
  },
  actionRow: {
    flexDirection: "row",
    gap: 10,
    marginTop: 14
  },
  captureButton: {
    flex: 1,
    height: 46,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: radii.md,
    backgroundColor: colors.text
  },
  captureButtonText: {
    ...typography.body,
    color: colors.white,
    fontWeight: "800"
  },
  secondaryButton: {
    flex: 1,
    height: 46,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: radii.md,
    backgroundColor: colors.surfaceMuted
  },
  secondaryButtonText: {
    ...typography.body,
    color: colors.text,
    fontWeight: "800"
  },
  checkList: {
    marginTop: 14,
    borderRadius: radii.md,
    borderWidth: 1,
    borderColor: colors.hairline,
    backgroundColor: colors.surface,
    overflow: "hidden"
  },
  checkRow: {
    minHeight: 62,
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    borderBottomWidth: 1,
    borderBottomColor: colors.hairline,
    paddingHorizontal: 14
  },
  checkIcon: {
    width: 34,
    height: 34,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: radii.sm,
    backgroundColor: colors.surfaceMuted
  },
  checkTitle: {
    flex: 1,
    ...typography.body,
    color: colors.text,
    fontWeight: "800"
  },
  checkValue: {
    ...typography.caption,
    color: colors.textMuted
  }
});
