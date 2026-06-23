import type { SetDetail } from "@/types/api";

const HOUR_HEIGHT = 64;
const DAY_START_HOUR = 12;

export function timeToMinutes(isoStr: string): number {
  const date = new Date(isoStr);
  const h = date.getUTCHours();
  const m = date.getUTCMinutes();
  return h * 60 + m;
}

export function setTop(startsAt: string): number {
  const minutes = timeToMinutes(startsAt);
  const dayStartMinutes = DAY_START_HOUR * 60;
  return ((minutes - dayStartMinutes) / 60) * HOUR_HEIGHT;
}

export function setHeight(startsAt: string, endsAt: string): number {
  const startMin = timeToMinutes(startsAt);
  const endMin = timeToMinutes(endsAt);
  const durationHours = Math.max(0.5, (endMin - startMin) / 60);
  return durationHours * HOUR_HEIGHT;
}

export function groupByStage(sets: SetDetail[]): Map<string, SetDetail[]> {
  const map = new Map<string, SetDetail[]>();
  for (const s of sets) {
    const stageName = s.artists[0]?.name ?? s.display_name;
    const bucket = map.get(stageName);
    if (bucket != null) {
      bucket.push(s);
    } else {
      map.set(stageName, [s]);
    }
  }
  return map;
}

export const HOUR_HEIGHT_PX = HOUR_HEIGHT;
export const DAY_START_HOUR_CONST = DAY_START_HOUR;
