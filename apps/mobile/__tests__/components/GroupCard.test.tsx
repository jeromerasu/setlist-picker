import React from "react";
import { render, fireEvent } from "@testing-library/react-native";
import { GroupCard } from "@/screens/groups/GroupCard";
import { HUES } from "@/theme/heroes";
import type { MyGroupListItem } from "@/types/api";

const BASE_GROUP: MyGroupListItem = {
  group_id: "g1",
  name: "Ravefam",
  invite_code: "ABCD1234",
  event_id: "e1",
  created_by_user_id: "u1",
  last_active_at: "2026-06-20T10:00:00Z",
  archived_at: null,
  member_id: "m1",
  joined_at: "2026-06-01T10:00:00Z",
};

test("renders_name_event_date_members", () => {
  const { getByText } = render(
    <GroupCard group={BASE_GROUP} hue={HUES[0]} onPress={() => undefined} />
  );
  expect(getByText("Ravefam")).toBeTruthy();
});

test("tap_invokes_onPress", () => {
  const onPress = jest.fn();
  const { getByTestId } = render(
    <GroupCard group={BASE_GROUP} hue={HUES[0]} onPress={onPress} testID="card" />
  );
  fireEvent.press(getByTestId("card"));
  expect(onPress).toHaveBeenCalledTimes(1);
});

test("truncates_long_event_name", () => {
  const longName = "A".repeat(60);
  const group: MyGroupListItem = { ...BASE_GROUP, name: longName };
  const { getByText } = render(
    <GroupCard group={group} hue={HUES[0]} onPress={() => undefined} />
  );
  const el = getByText(longName);
  expect(el.props.numberOfLines).toBe(1);
});

test("archived_shows_pill", () => {
  const archived: MyGroupListItem = { ...BASE_GROUP, archived_at: "2026-06-10T00:00:00Z" };
  const { getByText } = render(
    <GroupCard group={archived} hue={HUES[0]} onPress={() => undefined} />
  );
  expect(getByText("ARCHIVED")).toBeTruthy();
});
