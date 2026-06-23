import { HUES } from "@/theme/heroes";

export function deriveMono(name: string): string {
  const alphaNums = name.replace(/[^a-zA-Z0-9]/g, "").toUpperCase();
  if (alphaNums.length === 0) return "??";
  return alphaNums.slice(0, 2).padEnd(2, alphaNums[0] ?? "?");
}

function _djb2(s: string): number {
  let h = 5381;
  for (let i = 0; i < s.length; i++) {
    h = ((h << 5) + h) ^ s.charCodeAt(i);
    h = h >>> 0;
  }
  return h;
}

export function deriveTileGradient(name: string): string {
  const hue = HUES[_djb2(name) % HUES.length];
  return `linear-gradient(135deg, ${hue.from}, ${hue.to})`;
}
