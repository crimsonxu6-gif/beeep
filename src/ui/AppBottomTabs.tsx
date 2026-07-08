import { ComponentType } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { CheckCircle2, Home, LucideProps, UserRound } from "lucide-react-native";

import { AppRoute } from "@/application/navigation";
import { colors, radii, typography } from "@/theme/design";

interface TabItem {
  route: Exclude<AppRoute, "camera">;
  label: string;
  Icon: ComponentType<LucideProps>;
}

const tabs: TabItem[] = [
  { route: "home", label: "首页", Icon: Home },
  { route: "profile", label: "我", Icon: UserRound }
];

interface AppBottomTabsProps {
  activeRoute: AppRoute;
  onChange: (route: AppRoute) => void;
}

export function AppBottomTabs({ activeRoute, onChange }: AppBottomTabsProps) {
  return (
    <View style={styles.wrap}>
      {tabs.map(({ route, label, Icon }) => {
        const active = activeRoute === route;
        return (
          <Pressable
            key={route}
            accessibilityRole="button"
            accessibilityState={{ selected: active }}
            style={styles.item}
            onPress={() => onChange(route)}
          >
            <View style={[styles.iconWrap, active && styles.iconWrapActive]}>
              {route === "home" && active ? (
                <CheckCircle2 size={18} strokeWidth={2.4} color={colors.accent} />
              ) : (
                <Icon
                  size={20}
                  strokeWidth={2.2}
                  color={active ? colors.accent : colors.textMuted}
                />
              )}
            </View>
            <Text style={[styles.label, active && styles.labelActive]}>{label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    position: "absolute",
    left: 16,
    right: 16,
    bottom: 10,
    height: 68,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-around",
    borderRadius: radii.md,
    borderWidth: 1,
    borderColor: colors.hairline,
    backgroundColor: "rgba(255,255,255,0.94)",
    paddingHorizontal: 8
  },
  item: {
    width: "50%",
    height: 54,
    alignItems: "center",
    justifyContent: "center",
    gap: 3
  },
  iconWrap: {
    width: 30,
    height: 28,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: radii.sm
  },
  iconWrapActive: {
    backgroundColor: colors.accentSoft
  },
  label: {
    ...typography.caption,
    color: colors.textMuted
  },
  labelActive: {
    color: colors.accent
  }
});
