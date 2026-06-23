import { renderHook } from "@testing-library/react-native";
import { useUpNext } from "@/hooks/useUpNext";
import type { SetDetail, ArtistRef } from "@/types/api";

function makeSet(id: string, startsAt: string): SetDetail {
  const artist: ArtistRef = { artist_id: id, name: `A${id}`, position: 1, spotify_artist_id: null };
  return {
    set_id: id,
    display_name: `Set ${id}`,
    day_label: "Friday",
    starts_at: startsAt,
    ends_at: startsAt,
    artists: [artist],
  };
}

const NOW = "2026-07-04T20:00:00Z";

test("returns_nearest_upcoming_set", () => {
  const sets = [
    makeSet("far", "2026-07-04T23:00:00Z"),
    makeSet("near", "2026-07-04T21:00:00Z"),
    makeSet("past", "2026-07-04T19:00:00Z"),
  ];
  const { result } = renderHook(() => useUpNext(sets, NOW));
  expect(result.current?.set_id).toBe("near");
});

test("returns_undefined_when_all_past", () => {
  const sets = [makeSet("a", "2026-07-04T18:00:00Z"), makeSet("b", "2026-07-04T19:00:00Z")];
  const { result } = renderHook(() => useUpNext(sets, NOW));
  expect(result.current).toBeUndefined();
});

test("returns_undefined_for_empty_sets", () => {
  const { result } = renderHook(() => useUpNext([], NOW));
  expect(result.current).toBeUndefined();
});
