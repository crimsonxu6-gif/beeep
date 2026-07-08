import { ScrollView, StyleSheet, Text, View, Pressable } from "react-native";
import { Camera, Compass, Crop, Sparkles, UserRound } from "lucide-react-native";

import { AppRoute } from "@/application/navigation";
import { colors, radii, typography } from "@/theme/design";
import { ToolHeader } from "@/ui/ToolHeader";

interface HomeScreenProps {
  onNavigate: (route: AppRoute) => void;
}

const features = [
  { title: "构图", meta: "画面位置 / 留白", Icon: Compass },
  { title: "姿势", meta: "肩线 / 头部", Icon: Sparkles },
  { title: "裁剪", meta: "推荐比例 / 二次构图", Icon: Crop }
];

export function HomeScreen({ onNavigate }: HomeScreenProps) {
  return (
    <View style={styles.root}>
      <ToolHeader
        title="Beeep"
        subtitle="AI Photo Coach"
        rightIcon={UserRound}
        onRightPress={() => onNavigate("profile")}
      />
      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.content}>
        <View style={styles.hero}>
          <Text style={styles.heroTitle}>实时拍照指导</Text>
          <Text style={styles.heroMeta}>构图、姿势、镜头移动</Text>
          <Pressable style={styles.primaryButton} onPress={() => onNavigate("camera")}>
            <Camera size={20} strokeWidth={2.3} color={colors.white} />
            <Text style={styles.primaryButtonText}>拍照</Text>
          </Pressable>
        </View>

        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>我们的功能</Text>
        </View>

        <View style={styles.featureGrid}>
          {features.map(({ title, meta, Icon }) => (
            <View key={title} style={styles.featureCard}>
              <View style={styles.featureIcon}>
                <Icon size={19} strokeWidth={2.1} color={colors.accent} />
              </View>
              <Text style={styles.featureTitle}>{title}</Text>
              <Text style={styles.featureMeta}>{meta}</Text>
            </View>
          ))}
        </View>

        <View style={styles.statusPanel}>
          <View>
            <Text style={styles.statusTitle}>反馈节奏</Text>
            <Text style={styles.statusMeta}>2 FPS · debounce 450ms</Text>
          </View>
          <View style={styles.statusPill}>
            <Text style={styles.statusPillText}>Ready</Text>
          </View>
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
    paddingTop: 22,
    paddingBottom: 118
  },
  hero: {
    minHeight: 260,
    justifyContent: "center",
    borderRadius: radii.md,
    borderWidth: 1,
    borderColor: colors.hairline,
    backgroundColor: colors.surface,
    padding: 24
  },
  heroTitle: {
    ...typography.title,
    color: colors.text
  },
  heroMeta: {
    marginTop: 8,
    ...typography.body,
    color: colors.textMuted
  },
  primaryButton: {
    alignSelf: "flex-start",
    minWidth: 122,
    height: 46,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    marginTop: 28,
    borderRadius: radii.md,
    backgroundColor: colors.text,
    paddingHorizontal: 18
  },
  primaryButtonText: {
    ...typography.body,
    color: colors.white,
    fontWeight: "800"
  },
  sectionHeader: {
    height: 50,
    flexDirection: "row",
    alignItems: "center",
    marginTop: 18
  },
  sectionTitle: {
    ...typography.section,
    color: colors.text
  },
  featureGrid: {
    flexDirection: "row",
    gap: 10
  },
  featureCard: {
    flex: 1,
    minHeight: 124,
    borderRadius: radii.md,
    borderWidth: 1,
    borderColor: colors.hairline,
    backgroundColor: colors.surface,
    padding: 12
  },
  featureIcon: {
    width: 34,
    height: 34,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: radii.sm,
    backgroundColor: colors.accentSoft
  },
  featureTitle: {
    marginTop: 14,
    ...typography.body,
    color: colors.text,
    fontWeight: "800"
  },
  featureMeta: {
    marginTop: 3,
    ...typography.caption,
    color: colors.textMuted
  },
  statusPanel: {
    minHeight: 74,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginTop: 16,
    borderRadius: radii.md,
    borderWidth: 1,
    borderColor: colors.hairline,
    backgroundColor: colors.surface,
    paddingHorizontal: 16
  },
  statusTitle: {
    ...typography.body,
    color: colors.text,
    fontWeight: "800"
  },
  statusMeta: {
    marginTop: 3,
    ...typography.caption,
    color: colors.textMuted
  },
  statusPill: {
    height: 28,
    justifyContent: "center",
    borderRadius: radii.round,
    backgroundColor: "#EAF7F2",
    paddingHorizontal: 10
  },
  statusPillText: {
    ...typography.caption,
    color: colors.success
  }
});
