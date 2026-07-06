import { Platform } from "react-native";

export const colors = {
  background: "#F6F7F9",
  surface: "#FFFFFF",
  surfaceMuted: "#EEF1F5",
  text: "#101318",
  textMuted: "#7D838D",
  hairline: "#DDE2EA",
  accent: "#5E63F4",
  accentSoft: "#ECEEFF",
  success: "#14A67A",
  warning: "#D79A12",
  cameraInk: "#05070A",
  cameraPanel: "rgba(8,10,14,0.72)",
  white: "#FFFFFF"
} as const;

export const radii = {
  sm: 6,
  md: 8,
  round: 999
} as const;

export const typography = {
  family: Platform.select({
    ios: "System",
    android: "Roboto",
    default: undefined
  }),
  title: {
    fontSize: 28,
    lineHeight: 34,
    fontWeight: "800" as const
  },
  section: {
    fontSize: 17,
    lineHeight: 22,
    fontWeight: "700" as const
  },
  body: {
    fontSize: 15,
    lineHeight: 20,
    fontWeight: "500" as const
  },
  caption: {
    fontSize: 12,
    lineHeight: 16,
    fontWeight: "600" as const
  }
} as const;
