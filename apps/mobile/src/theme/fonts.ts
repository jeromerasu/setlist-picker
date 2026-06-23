// Font manifest for expo-font. Actual .ttf files are not bundled until Wave-3;
// this module provides the hook API that screens will call.

// Font files are expected at apps/mobile/assets/fonts/*.ttf (add before Wave-3 screens ship).
// The family names below MUST match the filename stem (Expo font loading convention).
export const FONT_MAP = {
  "Orbitron-Medium": require("../../assets/fonts/Orbitron-Medium.ttf"),
  "Orbitron-Bold": require("../../assets/fonts/Orbitron-Bold.ttf"),
  "Orbitron-Black": require("../../assets/fonts/Orbitron-Black.ttf"),
  "PlayfairDisplay-SemiBold": require("../../assets/fonts/PlayfairDisplay-SemiBold.ttf"),
  "PlayfairDisplay-Bold": require("../../assets/fonts/PlayfairDisplay-Bold.ttf"),
  "PlayfairDisplay-ExtraBold": require("../../assets/fonts/PlayfairDisplay-ExtraBold.ttf"),
  "Manrope-Regular": require("../../assets/fonts/Manrope-Regular.ttf"),
  "Manrope-Medium": require("../../assets/fonts/Manrope-Medium.ttf"),
  "Manrope-SemiBold": require("../../assets/fonts/Manrope-SemiBold.ttf"),
  "Manrope-Bold": require("../../assets/fonts/Manrope-Bold.ttf"),
  "Manrope-ExtraBold": require("../../assets/fonts/Manrope-ExtraBold.ttf"),
  "SpaceMono-Regular": require("../../assets/fonts/SpaceMono-Regular.ttf"),
  "SpaceMono-Bold": require("../../assets/fonts/SpaceMono-Bold.ttf"),
  "VT323-Regular": require("../../assets/fonts/VT323-Regular.ttf"),
} as const;
