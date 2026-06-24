import React from "react";
import { render, fireEvent } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// ─── Hook mocks ──────────────────────────────────────────────────────────────

const mockMutatePick = jest.fn();

jest.mock("@/hooks/usePickToggle", () => ({
  usePickToggle: () => ({ mutate: mockMutatePick }),
}));

jest.mock("expo-secure-store", () => ({
  getItemAsync: jest.fn(async () => null),
  setItemAsync: jest.fn(async () => undefined),
  deleteItemAsync: jest.fn(async () => undefined),
}));

// ─── Test data ───────────────────────────────────────────────────────────────

import { AllStagesGrid } from "@/screens/schedule/AllStagesGrid";
import type { SetDetail, StageDetail, ArtistRef, MemberOut } from "@/types/api";

function makeArtist(id: string, name: string): ArtistRef {
  return { artist_id: id, name, position: 1, spotify_artist_id: null };
}

function makeSet(
  id: string,
  dayLabel: string,
  startsAt = "2026-07-05T20:00:00Z",
  endsAt = "2026-07-05T21:00:00Z",
  artistName = `Artist ${id}`,
): SetDetail {
  return {
    set_id: id,
    display_name: `Set ${id}`,
    day_label: dayLabel,
    starts_at: startsAt,
    ends_at: endsAt,
    artists: [makeArtist(id, artistName)],
  };
}

function makeStage(id: string, name: string, order: number, sets: SetDetail[]): StageDetail {
  return { stage_id: id, name, display_order: order, color_hex: null, sets };
}

function makeMember(id: string, name: string): MemberOut {
  return {
    member_id: id,
    user_id: `user-${id}`,
    group_id: "grp1",
    display_name: name,
    avatar_color: "#a78bfa",
    display_name_override: null,
    joined_at: "2026-01-01T00:00:00Z",
  };
}

const SET_S1 = makeSet("s1", "Friday", "2026-07-05T20:00:00Z", "2026-07-05T21:00:00Z", "Deadmau5");
const SET_S2 = makeSet("s2", "Friday", "2026-07-05T22:00:00Z", "2026-07-05T23:00:00Z", "Eric Prydz");
const STAGE_A = makeStage("stg1", "Mainstage", 0, [SET_S1]);
const STAGE_B = makeStage("stg2", "Freedom", 1, [SET_S2]);

const STAGE_BY_SET = new Map([
  ["s1", { name: "Mainstage", color: "#ff4f9a" }],
  ["s2", { name: "Freedom", color: "#36c6ff" }],
]);

const MEMBER = makeMember("m1", "Diego F");

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return React.createElement(QueryClientProvider, { client: qc }, children);
}

const DEFAULT_PROPS = {
  sets: [SET_S1, SET_S2],
  stages: [STAGE_A, STAGE_B],
  stageBySetId: STAGE_BY_SET,
  picks: [],
  members: [MEMBER],
  myMemberId: "m1",
  invite_code: "TESTCODE",
};

beforeEach(() => {
  mockMutatePick.mockReset();
});

test("renders_instruction_text", () => {
  const { getByText } = render(<AllStagesGrid {...DEFAULT_PROPS} />, { wrapper });
  expect(getByText("Tap once for going, tap again for maybe")).toBeTruthy();
});

test("renders_legend_labels", () => {
  const { getAllByText } = render(<AllStagesGrid {...DEFAULT_PROPS} />, { wrapper });
  expect(getAllByText("Maybe").length).toBeGreaterThan(0);
  expect(getAllByText("Going").length).toBeGreaterThan(0);
});

test("renders_search_input", () => {
  const { getByTestId } = render(<AllStagesGrid {...DEFAULT_PROPS} />, { wrapper });
  expect(getByTestId("grid-search")).toBeTruthy();
});

test("renders_stage_header_names", () => {
  const { getByText } = render(<AllStagesGrid {...DEFAULT_PROPS} />, { wrapper });
  expect(getByText("Mainstage")).toBeTruthy();
  expect(getByText("Freedom")).toBeTruthy();
});

test("renders_set_cards", () => {
  const { getByTestId } = render(<AllStagesGrid {...DEFAULT_PROPS} />, { wrapper });
  expect(getByTestId("grid-set-s1")).toBeTruthy();
  expect(getByTestId("grid-set-s2")).toBeTruthy();
});

test("renders_artist_names_on_cards", () => {
  const { getByText } = render(<AllStagesGrid {...DEFAULT_PROPS} />, { wrapper });
  expect(getByText("Deadmau5")).toBeTruthy();
  expect(getByText("Eric Prydz")).toBeTruthy();
});

test("tap_none_card_posts_going_pick", () => {
  const { getByTestId } = render(<AllStagesGrid {...DEFAULT_PROPS} />, { wrapper });
  fireEvent.press(getByTestId("grid-set-s1"));
  expect(mockMutatePick).toHaveBeenCalledTimes(1);
  expect(mockMutatePick).toHaveBeenCalledWith(
    expect.objectContaining({ invite_code: "TESTCODE", set_id: "s1", is_picked: false }),
  );
});

test("tap_going_card_cycles_to_maybe_without_api_call", () => {
  // Pre-populate as "active" pick for myMemberId
  const props = {
    ...DEFAULT_PROPS,
    picks: [{ member_id: "m1", set_id: "s1", state: "active", state_clock_ms: 1000 }],
  };
  const { getByTestId } = render(<AllStagesGrid {...props} />, { wrapper });
  fireEvent.press(getByTestId("grid-set-s1"));
  // going → maybe is local only — no mutate call
  expect(mockMutatePick).not.toHaveBeenCalled();
});

test("tap_maybe_card_removes_pick", () => {
  const props = {
    ...DEFAULT_PROPS,
    picks: [{ member_id: "m1", set_id: "s1", state: "active", state_clock_ms: 1000 }],
  };
  const { getByTestId } = render(<AllStagesGrid {...props} />, { wrapper });
  // Tap once: going → maybe (no API)
  fireEvent.press(getByTestId("grid-set-s1"));
  expect(mockMutatePick).not.toHaveBeenCalled();
  // Tap twice: maybe → none (DELETE)
  fireEvent.press(getByTestId("grid-set-s1"));
  expect(mockMutatePick).toHaveBeenCalledTimes(1);
  expect(mockMutatePick).toHaveBeenCalledWith(
    expect.objectContaining({ invite_code: "TESTCODE", set_id: "s1", is_picked: true }),
  );
});

test("empty_sets_renders_without_crash", () => {
  const props = { ...DEFAULT_PROPS, sets: [], stages: [], stageBySetId: new Map() };
  const { getByText } = render(<AllStagesGrid {...props} />, { wrapper });
  expect(getByText("Tap once for going, tap again for maybe")).toBeTruthy();
});

test("search_input_is_editable", () => {
  const { getByTestId } = render(<AllStagesGrid {...DEFAULT_PROPS} />, { wrapper });
  const input = getByTestId("grid-search");
  fireEvent.changeText(input, "Deadmau5");
  // input accepts text without crash
  expect(input).toBeTruthy();
});
