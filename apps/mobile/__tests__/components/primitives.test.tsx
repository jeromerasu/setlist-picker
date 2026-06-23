import React from "react";
import { Text } from "react-native";
import { render } from "@testing-library/react-native";

jest.mock("@/theme/fonts", () => ({ FONT_MAP: {} }));

import { GlassCard } from "@/components/GlassCard";
import { Avatar } from "@/components/Avatar";
import { AvatarStack } from "@/components/AvatarStack";
import { StageDot } from "@/components/StageDot";
import { NeonGradientButton } from "@/components/NeonGradientButton";
import { GradientText } from "@/components/GradientText";
import { GlassBottomNav } from "@/components/GlassBottomNav";
import { PillTab } from "@/components/PillTab";
import { OutlineButton } from "@/components/OutlineButton";
import { BackChip } from "@/components/BackChip";
import { SearchInput } from "@/components/SearchInput";
import { EmptyState } from "@/components/EmptyState";

// ─────────────────────────────────────────────────────────────────────────────
// GlassCard
// ─────────────────────────────────────────────────────────────────────────────

test("GlassCard_default_snapshot", () => {
  const { toJSON } = render(
    <GlassCard>
      <Text>content</Text>
    </GlassCard>
  );
  expect(toJSON()).toMatchSnapshot();
});

test("GlassCard_strong_variant_snapshot", () => {
  const { toJSON } = render(
    <GlassCard variant="strong" border="strong" withInsetHighlight>
      <Text>strong</Text>
    </GlassCard>
  );
  expect(toJSON()).toMatchSnapshot();
});

// ─────────────────────────────────────────────────────────────────────────────
// Avatar
// ─────────────────────────────────────────────────────────────────────────────

test("Avatar_default_snapshot", () => {
  const { toJSON } = render(<Avatar initials="JR" color="#a78bfa" />);
  expect(toJSON()).toMatchSnapshot();
});

test("Avatar_with_ring_snapshot", () => {
  const { toJSON } = render(
    <Avatar initials="AB" color="#ff2d9b" size={40} ringColor="#1a0c2e" />
  );
  expect(toJSON()).toMatchSnapshot();
});

// ─────────────────────────────────────────────────────────────────────────────
// AvatarStack
// ─────────────────────────────────────────────────────────────────────────────

const MEMBERS = [
  { initials: "A1", color: "#ff2d9b" },
  { initials: "B2", color: "#a64bff" },
  { initials: "C3", color: "#28e0ff" },
];

test("AvatarStack_three_members_snapshot", () => {
  const { toJSON } = render(<AvatarStack members={MEMBERS} />);
  expect(toJSON()).toMatchSnapshot();
});

test("AvatarStack_overflow_badge_snapshot", () => {
  const extra = [
    ...MEMBERS,
    { initials: "D4", color: "#7b5cff" },
    { initials: "E5", color: "#a78bfa" },
    { initials: "F6", color: "#28e0ff" },
  ];
  const { toJSON } = render(<AvatarStack members={extra} />);
  expect(toJSON()).toMatchSnapshot();
});

test("AvatarStack_empty_renders_nothing", () => {
  const { toJSON } = render(<AvatarStack members={[]} />);
  expect(toJSON()).toMatchSnapshot();
});

// ─────────────────────────────────────────────────────────────────────────────
// StageDot
// ─────────────────────────────────────────────────────────────────────────────

test("StageDot_no_glow_snapshot", () => {
  const { toJSON } = render(<StageDot color="#2d8a4e" />);
  expect(toJSON()).toMatchSnapshot();
});

test("StageDot_with_glow_snapshot", () => {
  const { toJSON } = render(<StageDot color="#e85d04" size={11} withGlow />);
  expect(toJSON()).toMatchSnapshot();
});

// ─────────────────────────────────────────────────────────────────────────────
// NeonGradientButton
// ─────────────────────────────────────────────────────────────────────────────

test("NeonGradientButton_enabled_snapshot", () => {
  const { toJSON } = render(
    <NeonGradientButton label="Let's go" onPress={() => undefined} />
  );
  expect(toJSON()).toMatchSnapshot();
});

test("NeonGradientButton_disabled_snapshot", () => {
  const { toJSON } = render(
    <NeonGradientButton label="Let's go" onPress={() => undefined} disabled />
  );
  expect(toJSON()).toMatchSnapshot();
});

// ─────────────────────────────────────────────────────────────────────────────
// GradientText
// ─────────────────────────────────────────────────────────────────────────────

test("GradientText_snapshot", () => {
  const { toJSON } = render(
    <GradientText size={30} weight={700}>
      TML 2026
    </GradientText>
  );
  expect(toJSON()).toMatchSnapshot();
});

// ─────────────────────────────────────────────────────────────────────────────
// GlassBottomNav
// ─────────────────────────────────────────────────────────────────────────────

test("GlassBottomNav_three_items_snapshot", () => {
  const items = [
    { label: "Home", icon: <Text>H</Text>, onPress: () => undefined, isActive: true },
    { label: "Search", icon: <Text>S</Text>, onPress: () => undefined, isActive: false },
    { label: "You", icon: <Text>Y</Text>, onPress: () => undefined, isActive: false },
  ];
  const { toJSON } = render(<GlassBottomNav items={items} />);
  expect(toJSON()).toMatchSnapshot();
});

// ─────────────────────────────────────────────────────────────────────────────
// PillTab
// ─────────────────────────────────────────────────────────────────────────────

test("PillTab_active_snapshot", () => {
  const { toJSON } = render(<PillTab label="All" active onPress={() => undefined} />);
  expect(toJSON()).toMatchSnapshot();
});

test("PillTab_inactive_snapshot", () => {
  const { toJSON } = render(<PillTab label="Upcoming" active={false} onPress={() => undefined} />);
  expect(toJSON()).toMatchSnapshot();
});

// ─────────────────────────────────────────────────────────────────────────────
// OutlineButton
// ─────────────────────────────────────────────────────────────────────────────

test("OutlineButton_snapshot", () => {
  const { toJSON } = render(<OutlineButton label="Cancel" onPress={() => undefined} />);
  expect(toJSON()).toMatchSnapshot();
});

// ─────────────────────────────────────────────────────────────────────────────
// BackChip
// ─────────────────────────────────────────────────────────────────────────────

test("BackChip_snapshot", () => {
  const { toJSON } = render(<BackChip onPress={() => undefined} />);
  expect(toJSON()).toMatchSnapshot();
});

// ─────────────────────────────────────────────────────────────────────────────
// SearchInput
// ─────────────────────────────────────────────────────────────────────────────

test("SearchInput_snapshot", () => {
  const { toJSON } = render(
    <SearchInput value="" onChangeText={() => undefined} placeholder="Search artists" />
  );
  expect(toJSON()).toMatchSnapshot();
});

test("SearchInput_with_value_snapshot", () => {
  const { toJSON } = render(
    <SearchInput value="Flume" onChangeText={() => undefined} />
  );
  expect(toJSON()).toMatchSnapshot();
});

// ─────────────────────────────────────────────────────────────────────────────
// EmptyState
// ─────────────────────────────────────────────────────────────────────────────

test("EmptyState_no_cta_snapshot", () => {
  const { toJSON } = render(
    <EmptyState
      icon={<Text>🎵</Text>}
      title="Nothing here yet"
      body="Join a group to start picking sets."
    />
  );
  expect(toJSON()).toMatchSnapshot();
});

test("EmptyState_with_cta_snapshot", () => {
  const { toJSON } = render(
    <EmptyState
      icon={<Text>🎵</Text>}
      title="Nothing here yet"
      body="Join a group to start picking sets."
      cta={{ label: "Join group", onPress: () => undefined }}
    />
  );
  expect(toJSON()).toMatchSnapshot();
});
