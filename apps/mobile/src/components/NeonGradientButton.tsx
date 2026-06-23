import { StyleSheet, Text, TouchableOpacity } from "react-native";
import { colors, radius } from "@/theme/tokens";

type Size = "md" | "lg";

export interface NeonGradientButtonProps {
  label: string;
  onPress: () => void;
  disabled?: boolean;
  size?: Size;
  testID?: string;
}

const HEIGHT: Record<Size, number> = { md: 48, lg: 52 };

export function NeonGradientButton({
  label,
  onPress,
  disabled = false,
  size = "lg",
  testID,
}: NeonGradientButtonProps) {
  return (
    <TouchableOpacity
      onPress={disabled ? undefined : onPress}
      activeOpacity={disabled ? 1 : 0.75}
      disabled={disabled}
      testID={testID}
      style={[
        styles.base,
        { height: HEIGHT[size] },
        disabled ? styles.disabled : styles.enabled,
      ]}
    >
      <Text
        style={[
          styles.label,
          { color: disabled ? colors.text.placeholder : colors.text.primary },
        ]}
      >
        {label}
      </Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  base: {
    borderRadius: radius.xl,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 24,
  },
  enabled: {
    // gradient handled by LinearGradient in real app; fallback color for tests
    backgroundColor: "#a64bff",
  },
  disabled: {
    backgroundColor: colors.bg.surfaceWeak,
    borderWidth: 1,
    borderColor: colors.border.disabled,
  },
  label: {
    fontWeight: "700",
    fontSize: 14,
    letterSpacing: 0.05 * 14,
  },
});
