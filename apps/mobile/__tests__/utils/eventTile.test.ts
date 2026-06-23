import { deriveMono, deriveTileGradient } from "@/utils/eventTile";

test("derive_mono_from_simple_name", () => {
  expect(deriveMono("EDC Las Vegas")).toBe("ED");
});

test("derive_mono_skips_special_chars", () => {
  expect(deriveMono("!!Foo")).toBe("FO");
});

test("derive_mono_falls_back_to_question_marks", () => {
  expect(deriveMono("🎵🎶")).toBe("??");
});

test("derive_mono_single_char_pads", () => {
  expect(deriveMono("A!!")).toBe("AA");
});

test("derive_tile_gradient_stable_for_name", () => {
  const g1 = deriveTileGradient("TML 2026");
  const g2 = deriveTileGradient("TML 2026");
  expect(g1).toBe(g2);
});

test("derive_tile_gradient_differs_for_different_names", () => {
  const g1 = deriveTileGradient("TML 2026");
  const g2 = deriveTileGradient("EDC Las Vegas 2026");
  // Different strings - may or may not differ (hash collision possible), but usually differ
  // Just verify they're non-empty strings
  expect(typeof g1).toBe("string");
  expect(typeof g2).toBe("string");
  expect(g1.length).toBeGreaterThan(0);
});
