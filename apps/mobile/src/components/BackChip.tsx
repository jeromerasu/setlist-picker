import { StyleSheet, Text, TouchableOpacity } from "react-native";
import { colors } from "@/theme/tokens";

export interface BackChipProps {
  onPress: () => void;
}

export function BackChip({ onPress }: BackChipProps) {
  return (
    <TouchableOpacity style={styles.circle} onPress={onPress} accessibilityLabel="Go back">
      <Text style={styles.arrow}>‹</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  circle: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: colors.bg.surfaceStrong,
    borderWidth: 1,
    borderColor: colors.border.subtle,
    alignItems: "center",
    justifyContent: "center",
  },
  arrow: {
    color: colors.text.primary,
    fontSize: 22,
    lineHeight: 26,
  },
});
