import type { SetDetail } from "@/types/api";

export function uniqueDays(sets: SetDetail[]): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const s of sets) {
    if (!seen.has(s.day_label)) {
      seen.add(s.day_label);
      result.push(s.day_label);
    }
  }
  return result;
}

export function setsForDay(sets: SetDetail[], dayLabel: string): SetDetail[] {
  return sets.filter((s) => s.day_label === dayLabel);
}
