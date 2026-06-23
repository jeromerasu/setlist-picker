import { normalizeCode } from "@/utils/inviteCode";

test("uppercases_raw_input", () => {
  expect(normalizeCode("abc12345")).toBe("ABC12345");
});

test("replaces_I_with_1", () => {
  expect(normalizeCode("IIII1234")).toBe("11111234");
});

test("replaces_L_with_1", () => {
  expect(normalizeCode("LLLL1234")).toBe("11111234");
});

test("replaces_O_with_0", () => {
  expect(normalizeCode("OOOO1234")).toBe("00001234");
});

test("clips_to_8_chars", () => {
  expect(normalizeCode("ABCDEFGHIJ")).toBe("ABCDEFGH");
});
