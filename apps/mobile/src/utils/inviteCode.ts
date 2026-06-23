// Crockford Base32 normalization: uppercase + I→1, L→1, O→0, clip to 8 chars.
export function normalizeCode(raw: string): string {
  return raw
    .toUpperCase()
    .replace(/I/g, "1")
    .replace(/L/g, "1")
    .replace(/O/g, "0")
    .slice(0, 8);
}
