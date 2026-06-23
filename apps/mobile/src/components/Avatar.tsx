import { StyleSheet, Text, View } from "react-native";

export interface AvatarProps {
  initials: string;
  color: string;
  textColor?: string;
  size?: 18 | 24 | 26 | 34 | 40;
  ringColor?: string;
}

export function Avatar({
  initials,
  color,
  textColor = "#ffffff",
  size = 34,
  ringColor,
}: AvatarProps) {
  const display = initials.slice(0, 2);
  const fontSize = Math.round(size * 0.4);
  return (
    <View
      style={[
        styles.circle,
        {
          width: size,
          height: size,
          borderRadius: size / 2,
          backgroundColor: color,
          borderColor: ringColor ?? "transparent",
          borderWidth: ringColor ? 2 : 0,
        },
      ]}
    >
      <Text style={[styles.text, { fontSize, color: textColor }]}>{display}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  circle: {
    alignItems: "center",
    justifyContent: "center",
    overflow: "hidden",
  },
  text: {
    fontWeight: "700",
  },
});
