// Stage color palette — 6 hues, rotated deterministically by display_order.
// Seed values from DESIGN-TOKENS § 1.3 (first 4) + § 1.7 HUES[4–5].
// When REALIGN-001 ships stage.color_hex, this fallback is no longer used.

const STAGE_PALETTE = [
  "#ff4f9a", // stage.sherwood
  "#36c6ff", // stage.tripolee
  "#a06bff", // stage.ranch
  "#2dd4bf", // stage.cosmic
  "#ffd23f", // HUES[4] amber
  "#ff2d9b", // HUES[5] hot pink (neon.pink)
] as const;

export function stageColorByIndex(displayOrder: number): string {
  return STAGE_PALETTE[Math.abs(displayOrder) % STAGE_PALETTE.length];
}

/** Prefer color_hex from the API; fall back to deterministic palette rotation. */
export function resolveStageColor(colorHex: string | null | undefined, displayOrder: number): string {
  return colorHex != null && colorHex.length > 0 ? colorHex : stageColorByIndex(displayOrder);
}
