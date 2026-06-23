// Exported TypeScript constants for non-NativeWind use (linear-gradient stops, animation timings, shadows)

// Gradient stop arrays for react-native-linear-gradient
export const gradients = {
  title: {
    colors: ["#ff2d9b", "#a64bff", "#28e0ff"] as const,
    start: { x: 0, y: 0 },
    end: { x: 1, y: 0 },
  },
  scheduleCta: {
    colors: ["#a64bff", "#28e0ff"] as const,
    start: { x: 0, y: 0 },
    end: { x: 1, y: 0 },
  },
  userAvatar: {
    colors: ["#a78bfa", "#7b5cff"] as const,
    start: { x: 0, y: 0 },
    end: { x: 1, y: 1 },
  },
  pickedCheck: {
    colors: ["#ff2d9b", "#28e0ff"] as const,
    start: { x: 0, y: 0 },
    end: { x: 1, y: 1 },
  },
  timelineLwwBar: {
    colors: ["#ff2d9b", "#a64bff"] as const,
    start: { x: 0, y: 0 },
    end: { x: 0, y: 1 },
  },
  hues: [
    { colors: ["#ff4f9a", "#7a1f6a"] as const },
    { colors: ["#36c6ff", "#1453d6"] as const },
    { colors: ["#a06bff", "#4b1fa8"] as const },
    { colors: ["#2dd4bf", "#0e7c66"] as const },
    { colors: ["#ffd23f", "#ff6a3d"] as const },
    { colors: ["#ff2d9b", "#5b1bd6"] as const },
  ],
} as const;

export const colors = {
  bg: {
    canvas: "#0a0712",
    deep: "#08060f",
    mid: "#150e34",
    high: "#1a1232",
    elevated: "#241a44",
    surfaceWeak: "rgba(255,255,255,0.05)",
    surfaceMed: "rgba(255,255,255,0.07)",
    surfaceStrong: "rgba(255,255,255,0.08)",
    surfaceTab: "rgba(255,255,255,0.06)",
    glassNav: "rgba(18,12,40,0.72)",
  },
  neon: {
    pink: "#ff2d9b",
    violet: "#a64bff",
    cyan: "#28e0ff",
    purple: "#a78bfa",
    purpleDeep: "#7b5cff",
    violetSat: "#5b1bd6",
    skyDeep: "#1453d6",
    lilac: "#cdb4fe",
    lavenderDim: "#b6acd8",
    violetText: "#9b8cff",
    violetAvatar: "#a78bfa",
  },
  text: {
    primary: "#ffffff",
    secondary: "#a99fce",
    tertiary: "#8a82b8",
    muted: "#7a7298",
    placeholder: "#6a6592",
    invertedDark: "#1a0c2e",
    error: "#ff6a8a",
    success: "#28e0ff",
  },
  border: {
    weak: "rgba(255,255,255,0.06)",
    subtle: "rgba(255,255,255,0.08)",
    default: "rgba(255,255,255,0.1)",
    mid: "rgba(255,255,255,0.12)",
    strong: "rgba(255,255,255,0.14)",
    input: "rgba(255,255,255,0.18)",
    disabled: "rgba(255,255,255,0.22)",
  },
} as const;

export const radius = {
  xs: 2,
  sm: 7,
  md: 12,
  lg: 14,
  xl: 15,
  "2xl": 18,
  "3xl": 20,
  "4xl": 22,
  full: 9999,
} as const;

export const spacing = {
  1: 4,
  2: 6,
  3: 8,
  4: 10,
  5: 12,
  6: 14,
  7: 16,
  8: 18,
  9: 22,
  10: 26,
  11: 30,
  12: 34,
  13: 46,
  screenPad: 22,
} as const;

export const sizes = {
  avatar: { lg: 40, md: 34, sm: 26, xs: 24, xxs: 18 },
  cta: 52,
  input: 54,
  search: 48,
  buttonSm: 38,
  bottomNav: 64,
  statusBarOffset: 44,
} as const;

export const motion = {
  pickCheckPop: 250,
  sheetUp: 250,
  fadeInScreen: 250,
  fadeInFast: 200,
  fadeInToast: 150,
  toastInvite: 2600,
  tapState: 180,
  cardState: 200,
} as const;
