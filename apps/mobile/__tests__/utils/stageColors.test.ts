import { stageColorByIndex, resolveStageColor } from "@/utils/stageColors";

test("stageColorByIndex_wraps_at_6", () => {
  const c0 = stageColorByIndex(0);
  const c6 = stageColorByIndex(6);
  expect(c0).toBe(c6);
});

test("resolveStageColor_prefers_color_hex_when_present", () => {
  const result = resolveStageColor("#aabbcc", 0);
  expect(result).toBe("#aabbcc");
});

test("resolveStageColor_falls_back_when_null", () => {
  const result = resolveStageColor(null, 0);
  expect(result).toBe(stageColorByIndex(0));
});

test("resolveStageColor_falls_back_when_undefined", () => {
  const result = resolveStageColor(undefined, 2);
  expect(result).toBe(stageColorByIndex(2));
});

test("resolveStageColor_falls_back_when_empty_string", () => {
  const result = resolveStageColor("", 1);
  expect(result).toBe(stageColorByIndex(1));
});
