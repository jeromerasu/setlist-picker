import { uniqueDays, setsForDay } from "@/utils/dayList";
import type { SetDetail, ArtistRef } from "@/types/api";

function makeSet(id: string, dayLabel: string): SetDetail {
  const artist: ArtistRef = { artist_id: id, name: `A${id}`, position: 1, spotify_artist_id: null };
  return {
    set_id: id,
    display_name: `Set ${id}`,
    day_label: dayLabel,
    starts_at: "2026-07-04T20:00:00Z",
    ends_at: "2026-07-04T21:00:00Z",
    artists: [artist],
  };
}

test("unique_days_preserves_insertion_order", () => {
  const sets = [makeSet("a", "Friday"), makeSet("b", "Saturday"), makeSet("c", "Friday")];
  expect(uniqueDays(sets)).toEqual(["Friday", "Saturday"]);
});

test("unique_days_empty", () => {
  expect(uniqueDays([])).toEqual([]);
});

test("sets_for_day_filters_correctly", () => {
  const sets = [makeSet("a", "Friday"), makeSet("b", "Saturday"), makeSet("c", "Friday")];
  const fri = setsForDay(sets, "Friday");
  expect(fri.length).toBe(2);
  expect(fri.every((s) => s.day_label === "Friday")).toBe(true);
});
