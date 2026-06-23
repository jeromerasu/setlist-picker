import { StyleSheet, Text, TouchableOpacity } from "react-native";
import { colors, radius } from "@/theme/tokens";

export interface OutlineButtonProps {
  label: string;
  onPress: () => void;
  testID?: string;
}

export function OutlineButton({ label, onPress, testID }: OutlineButtonProps) {
  return (
    <TouchableOpacity style={styles.base} onPress={onPress} testID={testID}>
      <Text style={styles.text}>{label}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  base: {
    height: 48,
    borderRadius: radius.xl,
    borderWidth: 1,
    borderColor: colors.border.strong,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 24,
  },
  text: {
    color: colors.text.secondary,
    fontSize: 14,
    fontWeight: "600",
  },
});
