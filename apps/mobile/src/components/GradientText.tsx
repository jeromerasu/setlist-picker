import { Text } from "react-native";

type GradientType = "title" | "schedule";

export interface GradientTextProps {
  children: string;
  gradient?: GradientType;
  font?: string;
  weight?: 700 | 800 | 900;
  size?: number;
  letterSpacing?: number;
}

export function GradientText({
  children,
  font = "Orbitron-Bold",
  weight = 700,
  size = 30,
  letterSpacing = 0,
}: GradientTextProps) {
  if (!children) return null;

  // In production, MaskedView + LinearGradient provide the gradient fill.
  // In test/no-gradient environment, render as white text.
  return (
    <Text
      style={{
        fontFamily: font,
        fontWeight: String(weight) as "700" | "800" | "900",
        fontSize: size,
        letterSpacing: letterSpacing * size,
        color: "#ffffff",
      }}
    >
      {children}
    </Text>
  );
}
