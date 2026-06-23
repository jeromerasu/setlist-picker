import type { SetDetail, PickSummary } from "@/types/api";

export interface DayBucket {
  label: string;
  sets: SetDetail[];
}

export function bucketByDay(sets: SetDetail[]): DayBucket[] {
  const map = new Map<string, SetDetail[]>();
  for (const s of sets) {
    const day = s.day_label;
    const bucket = map.get(day);
    if (bucket != null) {
      bucket.push(s);
    } else {
      map.set(day, [s]);
    }
  }
  const result: DayBucket[] = [];
  for (const [label, daySets] of map.entries()) {
    result.push({ label, sets: daySets });
  }
  return result;
}

export function pickedSetIds(picks: PickSummary[], myMemberId?: string): Set<string> {
  const relevant = myMemberId != null ? picks.filter((p) => p.member_id === myMemberId) : picks;
  return new Set(relevant.map((p) => p.set_id));
}
