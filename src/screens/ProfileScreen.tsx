import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { Bell, ChevronRight, CreditCard, Image, Settings, ShieldCheck, UserRound } from "lucide-react-native";

import { colors, radii, typography } from "@/theme/design";
import { ToolHeader } from "@/ui/ToolHeader";

const services = [
  { title: "作品库", meta: "24 张", Icon: Image },
  { title: "订阅", meta: "Free", Icon: CreditCard },
  { title: "隐私", meta: "本地优先", Icon: ShieldCheck },
  { title: "设置", meta: "相机 / 模型", Icon: Settings }
];

export function ProfileScreen() {
  return (
    <View style={styles.root}>
      <ToolHeader title="我" subtitle="账户与服务" rightIcon={Bell} />
      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.content}>
        <View style={styles.profilePanel}>
          <View style={styles.avatar}>
            <UserRound size={30} strokeWidth={2.2} color={colors.accent} />
          </View>
          <View style={styles.profileText}>
            <Text numberOfLines={1} style={styles.name}>
              Crimson
            </Text>
            <Text numberOfLines={1} style={styles.handle}>
              @photo-coach
            </Text>
          </View>
          <Pressable style={styles.editButton}>
            <Text style={styles.editText}>编辑</Text>
          </Pressable>
        </View>

        <Text style={styles.sectionTitle}>各类服务</Text>
        <View style={styles.serviceList}>
          {services.map(({ title, meta, Icon }) => (
            <Pressable key={title} style={styles.serviceRow}>
              <View style={styles.serviceIcon}>
                <Icon size={19} strokeWidth={2.1} color={colors.text} />
              </View>
              <View style={styles.serviceText}>
                <Text style={styles.serviceTitle}>{title}</Text>
                <Text style={styles.serviceMeta}>{meta}</Text>
              </View>
              <ChevronRight size={18} strokeWidth={2.1} color={colors.textMuted} />
            </Pressable>
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
    paddingTop: 22,
    paddingBottom: 118
  },
  profilePanel: {
    minHeight: 96,
    flexDirection: "row",
    alignItems: "center",
    borderRadius: radii.md,
    borderWidth: 1,
    borderColor: colors.hairline,
    backgroundColor: colors.surface,
    padding: 16
  },
  avatar: {
    width: 58,
    height: 58,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: radii.round,
    backgroundColor: colors.accentSoft
  },
  profileText: {
    flex: 1,
    minWidth: 0,
    marginLeft: 14
  },
  name: {
    ...typography.section,
    color: colors.text
  },
  handle: {
    marginTop: 3,
    ...typography.caption,
    color: colors.textMuted
  },
  editButton: {
    height: 34,
    justifyContent: "center",
    borderRadius: radii.sm,
    backgroundColor: colors.surfaceMuted,
    paddingHorizontal: 12
  },
  editText: {
    ...typography.caption,
    color: colors.text
  },
  sectionTitle: {
    marginTop: 26,
    marginBottom: 10,
    ...typography.section,
    color: colors.text
  },
  serviceList: {
    borderRadius: radii.md,
    borderWidth: 1,
    borderColor: colors.hairline,
    backgroundColor: colors.surface,
    overflow: "hidden"
  },
  serviceRow: {
    minHeight: 66,
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    borderBottomWidth: 1,
    borderBottomColor: colors.hairline,
    paddingHorizontal: 14
  },
  serviceIcon: {
    width: 36,
    height: 36,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: radii.sm,
    backgroundColor: colors.surfaceMuted
  },
  serviceText: {
    flex: 1,
    minWidth: 0
  },
  serviceTitle: {
    ...typography.body,
    color: colors.text,
    fontWeight: "800"
  },
  serviceMeta: {
    marginTop: 2,
    ...typography.caption,
    color: colors.textMuted
  }
});
