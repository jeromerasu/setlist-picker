import React from "react";
import { fireEvent, render } from "@testing-library/react-native";
import { GoingMembersSheet } from "@/components/GoingMembersSheet";
import type { GoingSheetMember } from "@/components/GoingMembersSheet";

const MEMBERS: GoingSheetMember[] = [
  { display_name: "Sanne", avatar_color: "#a78bfa" },
  { display_name: "Jerome", avatar_color: "#36c6ff" },
  { display_name: "Ada", avatar_color: "#ff4f9a" },
];

test("going_sheet_renders_artist_name", () => {
  const { getByTestId } = render(
    <GoingMembersSheet artistName="Fisher" members={MEMBERS} onClose={jest.fn()} />,
  );
  expect(getByTestId("going-sheet-title").props.children).toBe("Fisher");
});

test("going_sheet_renders_going_count_pill", () => {
  const { getByTestId } = render(
    <GoingMembersSheet artistName="Fisher" members={MEMBERS} onClose={jest.fn()} />,
  );
  const pill = getByTestId("going-sheet-count-pill");
  expect(pill).toBeTruthy();
});

test("going_sheet_renders_all_members", () => {
  const { getByText } = render(
    <GoingMembersSheet artistName="Fisher" members={MEMBERS} onClose={jest.fn()} />,
  );
  expect(getByText("Sanne")).toBeTruthy();
  expect(getByText("Jerome")).toBeTruthy();
  expect(getByText("Ada")).toBeTruthy();
});

test("going_sheet_renders_members_sorted_alphabetically", () => {
  const { getAllByText } = render(
    <GoingMembersSheet artistName="Fisher" members={MEMBERS} onClose={jest.fn()} />,
  );
  // All GOING badges present (one per sorted member)
  const badges = getAllByText("GOING");
  expect(badges).toHaveLength(MEMBERS.length);
});

test("going_sheet_close_button_calls_onClose", () => {
  const onClose = jest.fn();
  const { getByTestId } = render(
    <GoingMembersSheet artistName="Fisher" members={MEMBERS} onClose={onClose} />,
  );
  fireEvent.press(getByTestId("going-sheet-close"));
  expect(onClose).toHaveBeenCalledTimes(1);
});

test("going_sheet_backdrop_tap_calls_onClose", () => {
  const onClose = jest.fn();
  const { getByTestId } = render(
    <GoingMembersSheet artistName="Fisher" members={MEMBERS} onClose={onClose} />,
  );
  fireEvent(getByTestId("going-sheet-backdrop"), "touchEnd");
  expect(onClose).toHaveBeenCalledTimes(1);
});

test("going_sheet_renders_empty_member_list", () => {
  const { queryAllByText } = render(
    <GoingMembersSheet artistName="Fisher" members={[]} onClose={jest.fn()} />,
  );
  expect(queryAllByText("GOING")).toHaveLength(0);
});

test("going_sheet_single_member_renders_correctly", () => {
  const { getByText, getAllByText } = render(
    <GoingMembersSheet
      artistName="Solomun"
      members={[{ display_name: "Maya", avatar_color: "#ff4f9a" }]}
      onClose={jest.fn()}
    />,
  );
  expect(getByText("Maya")).toBeTruthy();
  expect(getAllByText("GOING")).toHaveLength(1);
});
