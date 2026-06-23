import { StyleSheet, Text, TouchableOpacity } from "react-native";
import { colors, radius } from "@/theme/tokens";

export interface PillTabProps {
  label: string;
  active: boolean;
  onPress: () => void;
}

export function PillTab({ label, active, onPress }: PillTabProps) {
  return (
    <TouchableOpacity
      onPress={onPress}
      style={[styles.base, active ? styles.active : styles.inactive]}
    >
      <Text style={[styles.text, { color: active ? colors.text.invertedDark : colors.text.tertiary }]}>
        {label}
      </Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  base: {
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: radius.full,
  },
  active: {
    backgroundColor: colors.neon.purple,
  },
  inactive: {
    backgroundColor: colors.bg.surfaceTab,
    borderWidth: 1,
    borderColor: colors.border.subtle,
  },
  text: {
    fontSize: 13,
    fontWeight: "600",
  },
});
