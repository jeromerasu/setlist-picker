// HUES[] — 6 gradient stop-pairs for group hero backgrounds.
// Sourced from DESIGN-TOKENS § 1.7 hue palette (gradients.hues).
// Use modulo 6 on group list index to rotate.

export const HUES = [
  { from: "#ff4f9a", to: "#7a1f6a" },
  { from: "#36c6ff", to: "#1453d6" },
  { from: "#a06bff", to: "#4b1fa8" },
  { from: "#2dd4bf", to: "#0e7c66" },
  { from: "#ffd23f", to: "#ff6a3d" },
  { from: "#ff2d9b", to: "#5b1bd6" },
] as const;

export type HueEntry = (typeof HUES)[number];

export function getHue(index: number): HueEntry {
  return HUES[((index % HUES.length) + HUES.length) % HUES.length];
}
