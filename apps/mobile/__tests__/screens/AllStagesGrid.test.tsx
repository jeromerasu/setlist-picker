import React from "react";
import { render, fireEvent } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// ─── Hook mocks ──────────────────────────────────────────────────────────────

const mockMutatePick = jest.fn();
const mockUseGroupSchedule = jest.fn();

jest.mock("@/hooks/usePickToggle", () => ({
  usePickToggle: () => ({ mutate: mockMutatePick }),
}));
jest.mock("@/hooks/useGroupSchedule", () => ({
  useGroupSchedule: (ic: string, day: string) => mockUseGroupSchedule(ic, day),
}));

jest.mock("expo-secure-store", () => ({
  getItemAsync: jest.fn(async () => null),
  setItemAsync: jest.fn(async () => undefined),
  deleteItemAsync: jest.fn(async () => undefined),
}));

// ─── Test data ───────────────────────────────────────────────────────────────

import { AllStagesGrid } from "@/screens/schedule/AllStagesGrid";
import type { GroupSetItem, MemberPickInfo, SetDetail, StageDetail, ArtistRef, MemberOut } from "@/types/api";

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

function makeGroupSetItem(setId: string, goingMembers: MemberPickInfo[]): GroupSetItem {
  return {
    set_id: setId,
    display_name: `Set ${setId}`,
    stage_name: "Mainstage",
    stage_color_hex: "#ff4f9a",
    day_label: "Friday",
    starts_at: "2026-07-05T20:00:00Z",
    ends_at: "2026-07-05T21:00:00Z",
    going_members: goingMembers,
  };
}

function makePick(memberId: string, setId: string): MemberPickInfo {
  return { member_id: memberId, display_name: `Member ${memberId}`, avatar_color: "#a78bfa" };
}

const GROUP_SCHEDULE_EMPTY = { data: { group_id: "g1", event_id: "e1", day_label: "Friday", sets: [] } };

beforeEach(() => {
  mockMutatePick.mockReset();
  mockUseGroupSchedule.mockReturnValue(GROUP_SCHEDULE_EMPTY);
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
    expect.objectContaining({ invite_code: "TESTCODE", set_id: "s1", is_picked: false, member_id: "m1" }),
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
    expect.objectContaining({ invite_code: "TESTCODE", set_id: "s1", is_picked: true, member_id: "m1" }),
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

// ─── REALIGN-007 / FIX-ALL-STAGES-GROUP-AVATARS: group avatar stack tests ────

test("going_stack_not_rendered_when_zero_going_members", () => {
  mockUseGroupSchedule.mockReturnValue({
    data: { group_id: "g1", event_id: "e1", day_label: "Friday", sets: [] },
  });
  const { queryByTestId } = render(<AllStagesGrid {...DEFAULT_PROPS} />, { wrapper });
  expect(queryByTestId("going-stack-s1")).toBeNull();
});

test("going_stack_rendered_for_single_going_member", () => {
  mockUseGroupSchedule.mockReturnValue({
    data: {
      group_id: "g1",
      event_id: "e1",
      day_label: "Friday",
      sets: [makeGroupSetItem("s1", [makePick("m2", "s1")])],
    },
  });
  const { getByTestId } = render(<AllStagesGrid {...DEFAULT_PROPS} />, { wrapper });
  expect(getByTestId("going-stack-s1")).toBeTruthy();
});

test("going_stack_rendered_for_five_going_members", () => {
  const members = Array.from({ length: 5 }, (_, i) => makePick(`m${i + 1}`, "s1"));
  mockUseGroupSchedule.mockReturnValue({
    data: {
      group_id: "g1",
      event_id: "e1",
      day_label: "Friday",
      sets: [makeGroupSetItem("s1", members)],
    },
  });
  const { getByTestId } = render(<AllStagesGrid {...DEFAULT_PROPS} />, { wrapper });
  expect(getByTestId("going-stack-s1")).toBeTruthy();
});

test("going_stack_shows_overflow_pill_when_10_going", () => {
  const members = Array.from({ length: 10 }, (_, i) => makePick(`m${i + 1}`, "s1"));
  mockUseGroupSchedule.mockReturnValue({
    data: {
      group_id: "g1",
      event_id: "e1",
      day_label: "Friday",
      sets: [makeGroupSetItem("s1", members)],
    },
  });
  // maxVisible=9, so 10 members → 9 shown + "+1" pill
  const { getByTestId, getByText } = render(<AllStagesGrid {...DEFAULT_PROPS} />, { wrapper });
  expect(getByTestId("going-stack-s1")).toBeTruthy();
  expect(getByText("+1")).toBeTruthy();
});

test("going_stack_shows_overflow_pill_when_11_going", () => {
  const members = Array.from({ length: 11 }, (_, i) => makePick(`m${i + 1}`, "s1"));
  mockUseGroupSchedule.mockReturnValue({
    data: {
      group_id: "g1",
      event_id: "e1",
      day_label: "Friday",
      sets: [makeGroupSetItem("s1", members)],
    },
  });
  // 11 members → 9 shown + "+2" pill
  const { getByTestId, getByText } = render(<AllStagesGrid {...DEFAULT_PROPS} />, { wrapper });
  expect(getByTestId("going-stack-s1")).toBeTruthy();
  expect(getByText("+2")).toBeTruthy();
});

test("going_stack_falls_back_to_user_avatar_when_group_schedule_not_loaded", () => {
  mockUseGroupSchedule.mockReturnValue({ data: null });
  const props = {
    ...DEFAULT_PROPS,
    picks: [{ member_id: "m1", set_id: "s1", state: "active", state_clock_ms: 1 }],
  };
  const { getByTestId } = render(<AllStagesGrid {...props} />, { wrapper });
  // User has "going" state → fallback single avatar rendered
  expect(getByTestId("going-stack-s1")).toBeTruthy();
});

test("tap_cycle_still_works_with_group_schedule_data", () => {
  mockUseGroupSchedule.mockReturnValue({
    data: {
      group_id: "g1",
      event_id: "e1",
      day_label: "Friday",
      sets: [makeGroupSetItem("s1", [makePick("m2", "s1")])],
    },
  });
  const { getByTestId } = render(<AllStagesGrid {...DEFAULT_PROPS} />, { wrapper });
  // Tap once on none card → POST going
  fireEvent.press(getByTestId("grid-set-s1"));
  expect(mockMutatePick).toHaveBeenCalledWith(
    expect.objectContaining({ set_id: "s1", is_picked: false, member_id: "m1" }),
  );
});

// ─── GoingMembersSheet integration: avatar stack → sheet ─────────────────────

test("tapping_going_stack_opens_going_members_sheet", () => {
  const member: MemberPickInfo = { member_id: "m2", display_name: "Sanne", avatar_color: "#a78bfa" };
  mockUseGroupSchedule.mockReturnValue({
    data: {
      group_id: "g1",
      event_id: "e1",
      day_label: "Friday",
      sets: [makeGroupSetItem("s1", [member])],
    },
  });
  const { getByTestId, getByText } = render(<AllStagesGrid {...DEFAULT_PROPS} />, { wrapper });
  fireEvent.press(getByTestId("going-stack-s1"));
  expect(getByTestId("going-sheet")).toBeTruthy();
  expect(getByText("Sanne")).toBeTruthy();
});

test("going_sheet_closes_on_done_button", () => {
  const member: MemberPickInfo = { member_id: "m2", display_name: "Sanne", avatar_color: "#a78bfa" };
  mockUseGroupSchedule.mockReturnValue({
    data: {
      group_id: "g1",
      event_id: "e1",
      day_label: "Friday",
      sets: [makeGroupSetItem("s1", [member])],
    },
  });
  const { getByTestId, queryByTestId } = render(<AllStagesGrid {...DEFAULT_PROPS} />, { wrapper });
  fireEvent.press(getByTestId("going-stack-s1"));
  expect(getByTestId("going-sheet")).toBeTruthy();
  fireEvent.press(getByTestId("going-sheet-close"));
  expect(queryByTestId("going-sheet")).toBeNull();
});

test("going_sheet_shows_correct_artist_name", () => {
  const member: MemberPickInfo = { member_id: "m2", display_name: "Sanne", avatar_color: "#a78bfa" };
  mockUseGroupSchedule.mockReturnValue({
    data: {
      group_id: "g1",
      event_id: "e1",
      day_label: "Friday",
      sets: [makeGroupSetItem("s1", [member])],
    },
  });
  const { getByTestId, getByText } = render(<AllStagesGrid {...DEFAULT_PROPS} />, { wrapper });
  fireEvent.press(getByTestId("going-stack-s1"));
  // Sheet title shows artist name — use testID to disambiguate from card
  const sheetTitle = getByTestId("going-sheet-title");
  expect(sheetTitle.props.children).toBe("Deadmau5");
});
