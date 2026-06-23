import { setTop, setHeight, groupByStage, timeToMinutes } from "@/utils/gridLayout";
import type { SetDetail, ArtistRef } from "@/types/api";

function makeSet(id: string, starts: string, ends: string, artistName?: string): SetDetail {
  const artist: ArtistRef = { artist_id: id, name: artistName ?? `Artist ${id}`, position: 1, spotify_artist_id: null };
  return {
    set_id: id,
    display_name: `Set ${id}`,
    day_label: "Friday",
    starts_at: starts,
    ends_at: ends,
    artists: [artist],
  };
}

test("time_to_minutes_converts_utc_hours", () => {
  const mins = timeToMinutes("2026-07-04T20:30:00Z");
  expect(mins).toBe(20 * 60 + 30);
});

test("set_top_returns_positive_for_after_noon", () => {
  // 14:00 UTC = 2 hours after DAY_START_HOUR (12)
  const top = setTop("2026-07-04T14:00:00Z");
  expect(top).toBeGreaterThan(0);
});

test("set_top_zero_for_noon_start", () => {
  const top = setTop("2026-07-04T12:00:00Z");
  expect(top).toBe(0);
});

test("set_height_returns_hour_height_for_one_hour_set", () => {
  const height = setHeight("2026-07-04T20:00:00Z", "2026-07-04T21:00:00Z");
  expect(height).toBe(64);
});

test("set_height_clamps_at_half_hour_minimum", () => {
  // 10-minute set → should be clamped to 0.5 hours
  const height = setHeight("2026-07-04T20:00:00Z", "2026-07-04T20:10:00Z");
  expect(height).toBe(32);
});

test("group_by_stage_maps_artist_name", () => {
  const sets = [
    makeSet("s1", "2026-07-04T20:00:00Z", "2026-07-04T21:00:00Z", "Main Stage"),
    makeSet("s2", "2026-07-04T21:00:00Z", "2026-07-04T22:00:00Z", "Main Stage"),
    makeSet("s3", "2026-07-04T20:00:00Z", "2026-07-04T21:00:00Z", "Second Stage"),
  ];
  const stageMap = groupByStage(sets);
  expect(stageMap.get("Main Stage")?.length).toBe(2);
  expect(stageMap.get("Second Stage")?.length).toBe(1);
});
