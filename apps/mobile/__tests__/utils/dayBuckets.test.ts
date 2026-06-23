import { bucketByDay, pickedSetIds } from "@/utils/dayBuckets";
import type { SetDetail, PickSummary, ArtistRef } from "@/types/api";

function makeSet(id: string, dayLabel: string): SetDetail {
  const artist: ArtistRef = { artist_id: `a-${id}`, name: `Artist ${id}`, position: 1, spotify_artist_id: null };
  return {
    set_id: id,
    display_name: `Display ${id}`,
    day_label: dayLabel,
    starts_at: "2026-07-04T20:00:00Z",
    ends_at: "2026-07-04T21:00:00Z",
    artists: [artist],
  };
}

function makePick(setId: string): PickSummary {
  return {
    set_id: setId,
    member_id: "m1",
    state: "picked",
    state_clock_ms: 0,
  };
}

test("buckets_group_sets_by_day_label", () => {
  const sets = [makeSet("s1", "Friday"), makeSet("s2", "Friday"), makeSet("s3", "Saturday")];
  const buckets = bucketByDay(sets);
  const friday = buckets.find((b) => b.label === "Friday");
  const saturday = buckets.find((b) => b.label === "Saturday");
  expect(friday?.sets.length).toBe(2);
  expect(saturday?.sets.length).toBe(1);
});

test("buckets_empty_array_returns_empty", () => {
  expect(bucketByDay([])).toEqual([]);
});

test("picked_set_ids_returns_set_of_ids", () => {
  const picks = [makePick("s1"), makePick("s2")];
  const ids = pickedSetIds(picks);
  expect(ids.has("s1")).toBe(true);
  expect(ids.has("s2")).toBe(true);
  expect(ids.has("s3")).toBe(false);
});
