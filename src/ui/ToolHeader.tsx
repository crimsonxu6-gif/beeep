import { ComponentType } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { Bell, ChevronLeft, LucideProps, MoreHorizontal } from "lucide-react-native";

import { colors, radii, typography } from "@/theme/design";

interface ToolHeaderProps {
  title: string;
  subtitle?: string;
  onBack?: () => void;
  rightIcon?: ComponentType<LucideProps>;
  onRightPress?: () => void;
}

export function ToolHeader({ title, subtitle, onBack, rightIcon: RightIcon = Bell, onRightPress }: ToolHeaderProps) {
  return (
    <View style={styles.wrap}>
      <View style={styles.left}>
        {onBack ? (
          <Pressable accessibilityRole="button" style={styles.iconButton} onPress={onBack}>
            <ChevronLeft size={22} strokeWidth={2.3} color={colors.text} />
          </Pressable>
        ) : null}
        <View>
          <Text numberOfLines={1} style={styles.title}>
            {title}
          </Text>
          {subtitle ? (
            <Text numberOfLines={1} style={styles.subtitle}>
              {subtitle}
            </Text>
          ) : null}
        </View>
      </View>
      <Pressable accessibilityRole="button" style={styles.iconButton} onPress={onRightPress}>
        <RightIcon size={20} strokeWidth={2.2} color={colors.text} />
      </Pressable>
    </View>
  );
}

export function HeaderMoreButton() {
  return <MoreHorizontal size={20} strokeWidth={2.2} color={colors.text} />;
}

const styles = StyleSheet.create({
  wrap: {
    minHeight: 54,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 14
  },
  left: {
    flex: 1,
    minWidth: 0,
    flexDirection: "row",
    alignItems: "center",
    gap: 10
  },
  title: {
    ...typography.section,
    color: colors.text
  },
  subtitle: {
    marginTop: 2,
    ...typography.caption,
    color: colors.textMuted
  },
  iconButton: {
    width: 38,
    height: 38,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: radii.round,
    backgroundColor: colors.surface
  }
});
