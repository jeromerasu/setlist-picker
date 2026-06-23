import { useMemo } from "react";
import type { SetDetail } from "@/types/api";

export function useUpNext(sets: SetDetail[], nowIso?: string): SetDetail | undefined {
  const now = nowIso != null ? new Date(nowIso).getTime() : Date.now();

  return useMemo(() => {
    const upcoming = sets.filter((s) => new Date(s.starts_at).getTime() > now);
    if (upcoming.length === 0) return undefined;
    return upcoming.reduce((closest, s) => {
      const tClose = new Date(closest.starts_at).getTime();
      const tS = new Date(s.starts_at).getTime();
      return tS < tClose ? s : closest;
    });
  }, [sets, now]);
}
