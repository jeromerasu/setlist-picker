import { StyleSheet, TouchableOpacity, View } from "react-native";
import { radius } from "@/theme/tokens";

const PALETTE = [
  "#a64bff", "#ff2d9b", "#28e0ff", "#7b5cff", "#1453d6",
  "#ff6a8a", "#39ff14", "#ffaa00", "#e040fb", "#00e5cc",
];

interface Props {
  selected: string;
  onSelect: (color: string) => void;
}

export function AvatarColorPicker({ selected, onSelect }: Props) {
  return (
    <View style={styles.grid}>
      {PALETTE.map((c) => (
        <TouchableOpacity
          key={c}
          style={[styles.swatch, { backgroundColor: c }, selected === c && styles.swatchSelected]}
          onPress={() => onSelect(c)}
          testID={`swatch-${c}`}
        />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  grid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 10,
  },
  swatch: {
    width: 36,
    height: 36,
    borderRadius: radius.full,
    borderWidth: 2,
    borderColor: "transparent",
  },
  swatchSelected: {
    borderColor: "#ffffff",
  },
});
