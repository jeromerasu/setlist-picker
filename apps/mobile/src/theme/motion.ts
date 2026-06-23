export { motion } from "./tokens";

// Shared Easing presets for react-native-reanimated / Animated
export const easing = {
  standard: { duration: 250 },
  fast: { duration: 200 },
} as const;
