import { StyleSheet, View, type ViewProps } from "react-native";
import { colors, radius } from "@/theme/tokens";

type Variant = "weak" | "med" | "strong";
type BorderType = "default" | "subtle" | "strong";

const BG: Record<Variant, string> = {
  weak: colors.bg.surfaceWeak,
  med: colors.bg.surfaceMed,
  strong: colors.bg.surfaceStrong,
};

const BORDER: Record<BorderType, string> = {
  subtle: colors.border.subtle,
  default: colors.border.default,
  strong: colors.border.strong,
};

interface GlassCardProps extends ViewProps {
  variant?: Variant;
  border?: BorderType;
  withInsetHighlight?: boolean;
  children: React.ReactNode;
}

export function GlassCard({
  variant = "med",
  border = "default",
  withInsetHighlight = false,
  children,
  style,
  ...rest
}: GlassCardProps) {
  return (
    <View
      style={[
        styles.base,
        { backgroundColor: BG[variant], borderColor: BORDER[border] },
        withInsetHighlight && styles.insetHighlight,
        style,
      ]}
      {...rest}
    >
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  base: {
    borderRadius: radius["3xl"],
    borderWidth: 1,
    overflow: "hidden",
  },
  insetHighlight: {
    shadowColor: "rgba(255,255,255,0.06)",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 1,
    shadowRadius: 0,
  },
});
