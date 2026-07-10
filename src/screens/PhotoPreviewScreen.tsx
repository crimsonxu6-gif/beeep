import { useState } from "react";
import { Image, Pressable, StyleSheet, Text, View } from "react-native";
import { Check, Images, RotateCcw, X } from "lucide-react-native";
import { CapturedPhoto } from "@/types/photo";
import { colors, radii, typography } from "@/theme/design";

export function PhotoPreviewScreen({ photo, onRetake, onSave, onBack, onGallery }: {
  photo: CapturedPhoto;
  onRetake: () => void;
  onSave: () => Promise<boolean>;
  onBack: () => void;
  onGallery: () => void;
}) {
  const [saved, setSaved] = useState(false);
  return (
    <View style={styles.root}>
      <Image source={{ uri: photo.uri }} style={styles.image} resizeMode="contain" />
      <Pressable style={styles.close} onPress={onBack}><X color={colors.white} size={23} /></Pressable>
      <View style={styles.actions}>
        <Pressable style={styles.action} onPress={onGallery}><Images color={colors.white} size={22} /><Text style={styles.label}>图库</Text></Pressable>
        <Pressable style={styles.action} onPress={onRetake}><RotateCcw color={colors.white} size={22} /><Text style={styles.label}>重拍</Text></Pressable>
        <Pressable style={styles.action} onPress={() => void onSave().then(setSaved)}><Check color={colors.white} size={22} /><Text style={styles.label}>{saved ? "已保存" : "保存"}</Text></Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: "#050506" },
  image: { flex: 1, width: "100%" },
  close: { position: "absolute", top: 54, left: 18, width: 42, height: 42, borderRadius: radii.round, alignItems: "center", justifyContent: "center", backgroundColor: "rgba(0,0,0,0.55)" },
  actions: { position: "absolute", left: 20, right: 20, bottom: 42, height: 76, flexDirection: "row", alignItems: "center", justifyContent: "space-around", borderRadius: radii.md, backgroundColor: "rgba(12,12,14,0.82)" },
  action: { width: 76, alignItems: "center", gap: 5 },
  label: { ...typography.caption, color: colors.white }
});
