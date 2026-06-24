import { useState } from "react";
import { ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { StageDot } from "@/components/StageDot";
import { AvatarStack } from "@/components/AvatarStack";
import { Avatar } from "@/components/Avatar";
import { colors, radius, spacing } from "@/theme/tokens";
import { formatTimeLabel } from "@/utils/gridLayout";
import type { StageInfo } from "@/hooks/useScheduleData";
import type { MemberOut, PickSummary, SetDetail } from "@/types/api";

type FilterMode = "none" | "mine" | "group";

interface Props {
  sets: SetDetail[];
  picks: PickSummary[];
  members: MemberOut[];
  myMemberId: string | undefined;
  stageBySetId: Map<string, StageInfo>;
  activeDay: string;
  onNavigateToArtist: (set: SetDetail) => void;
  onRemovePick: (setId: string) => void;
  onOpenFilterSheet: () => void;
}

function goingMembersForSet(setId: string, picks: PickSummary[], members: MemberOut[]): MemberOut[] {
  const memberIds = new Set(picks.filter((p) => p.set_id === setId).map((p) => p.member_id));
  return members.filter((m) => memberIds.has(m.member_id));
}

function goingCountForSet(setId: string, picks: PickSummary[]): number {
  return new Set(picks.filter((p) => p.set_id === setId).map((p) => p.member_id)).size;
}

function goingLabel(count: number): string {
  if (count === 0) return "No one going";
  return count === 1 ? "1 going" : `${count} going`;
}

export function ScheduleTimeline({
  sets,
  picks,
  members,
  myMemberId,
  stageBySetId,
  activeDay,
  onNavigateToArtist,
  onRemovePick,
  onOpenFilterSheet,
}: Props) {
  const [filterMode, setFilterMode] = useState<FilterMode>("none");

  // All sets for this day, sorted by start time
  const daySets = sets
    .filter((s) => s.day_label === activeDay)
    .sort((a, b) => new Date(a.starts_at).getTime() - new Date(b.starts_at).getTime());

  // Mine: sets the current user has picked (all picks if no myMemberId resolved)
  const myPickedIds = new Set(
    myMemberId != null
      ? picks.filter((p) => p.member_id === myMemberId).map((p) => p.set_id)
      : picks.map((p) => p.set_id),
  );
  const mineSets = daySets.filter((s) => myPickedIds.has(s.set_id));

  // UP NEXT: the earliest upcoming set in my picks
  const now = Date.now();
  const upNext = mineSets.find((s) => new Date(s.starts_at).getTime() > now);

  // Group: all sets picked by anyone for this day (deduped)
  const groupPickedIds = new Set(
    picks
      .filter((p) => daySets.some((s) => s.set_id === p.set_id))
      .map((p) => p.set_id),
  );
  const groupSets = daySets.filter((s) => groupPickedIds.has(s.set_id));

  const handleMinePress = () => {
    setFilterMode((m) => (m === "mine" ? "none" : "mine"));
  };

  const handleGroupPress = () => {
    setFilterMode("group");
    onOpenFilterSheet();
  };

  const mineActive = filterMode === "mine";
  const groupActive = filterMode === "group";

  return (
    <View style={styles.root}>
      {/* Filter chips row — prototype l.346–349 */}
      <View style={styles.chipsRow}>
        <TouchableOpacity
          style={[styles.chip, groupActive && styles.chipActive]}
          onPress={handleGroupPress}
          testID="group-filter"
        >
          <Text style={[styles.chipText, groupActive && styles.chipTextActive]}>
            Group <Text style={styles.caret}>⌄</Text>
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.chip, mineActive && styles.chipActive]}
          onPress={handleMinePress}
          testID="mine-filter"
        >
          <Text style={[styles.chipText, mineActive && styles.chipTextActive]}>
            ★ Mine
          </Text>
        </TouchableOpacity>
      </View>

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {/* No filter selected — prototype l.354–360 */}
        {filterMode === "none" && (
          <View style={styles.emptyCenter}>
            <View style={styles.emptyIcon}>
              <Text style={styles.emptyIconGlyph}>☰</Text>
            </View>
            <Text style={styles.emptyHead}>No Filter Selected</Text>
            <Text style={styles.emptyBody}>Tap Mine or Group above{"\n"}to see sets</Text>
          </View>
        )}

        {/* Mine timeline — prototype l.362–396 */}
        {filterMode === "mine" && mineSets.length > 0 && (
          <>
            {/* UP NEXT card — prototype l.364–369 */}
            {upNext != null && (
              <UpNextCard set={upNext} stageBySetId={stageBySetId} />
            )}

            {/* GOING section header — prototype l.370 */}
            <View style={styles.goingSectionRow}>
              <View style={styles.goingBadgeIcon}>
                <Text style={styles.goingCheckGlyph}>✓</Text>
              </View>
              <Text style={styles.goingSectionLabel}>GOING</Text>
              <View style={styles.countBubble}>
                <Text style={styles.countBubbleText}>{mineSets.length}</Text>
              </View>
            </View>

            {/* Timeline items */}
            <View style={styles.timelineList}>
              {mineSets.map((set, i) => {
                const stage = stageBySetId.get(set.set_id);
                const goingCount = goingCountForSet(set.set_id, picks);
                const goingMembers = goingMembersForSet(set.set_id, picks, members);
                const isLast = i === mineSets.length - 1;
                return (
                  <TimelineItem
                    key={set.set_id}
                    set={set}
                    stageName={stage?.name ?? ""}
                    stageColor={stage?.color ?? colors.neon.violet}
                    goingCount={goingCount}
                    goingMembers={goingMembers}
                    isLast={isLast}
                    showRemove
                    onPress={() => onNavigateToArtist(set)}
                    onRemove={() => onRemovePick(set.set_id)}
                  />
                );
              })}
            </View>
          </>
        )}

        {/* Mine: no picks empty state — prototype l.389–395 */}
        {filterMode === "mine" && mineSets.length === 0 && (
          <View style={styles.emptyCenter}>
            <Text style={styles.emptyEmoji}>🎟️</Text>
            <Text style={styles.emptyHead}>Pick your first set</Text>
            <Text style={styles.emptyBody}>Head to All Stages and tap a set to mark you're going</Text>
          </View>
        )}

        {/* Group timeline — prototype l.398–421 */}
        {filterMode === "group" && groupSets.length > 0 && (
          <View style={styles.timelineList}>
            {groupSets.map((set, i) => {
              const stage = stageBySetId.get(set.set_id);
              const goingCount = goingCountForSet(set.set_id, picks);
              const goingMembers = goingMembersForSet(set.set_id, picks, members);
              const isLast = i === groupSets.length - 1;
              return (
                <TimelineItem
                  key={set.set_id}
                  set={set}
                  stageName={stage?.name ?? ""}
                  stageColor={stage?.color ?? colors.neon.violet}
                  goingCount={goingCount}
                  goingMembers={goingMembers}
                  isLast={isLast}
                  showRemove={false}
                  onPress={() => onNavigateToArtist(set)}
                  onRemove={() => undefined}
                />
              );
            })}
          </View>
        )}

        {/* Group: no sets empty state — prototype l.414–420 */}
        {filterMode === "group" && groupSets.length === 0 && (
          <View style={styles.emptyCenter}>
            <Text style={styles.emptyHead}>No Group Sets Yet</Text>
            <Text style={styles.emptyBody}>
              When group members mark sets,{"\n"}they'll appear here
            </Text>
          </View>
        )}
      </ScrollView>
    </View>
  );
}

// ─── UP NEXT card ────────────────────────────────────────────────────────────
// Matches prototype l.364–369: left bar gradient, "UP NEXT" label, Playfair 30px artist name

interface UpNextCardProps {
  set: SetDetail;
  stageBySetId: Map<string, StageInfo>;
}

function UpNextCard({ set, stageBySetId }: UpNextCardProps) {
  const stage = stageBySetId.get(set.set_id);
  const stageColor = stage?.color ?? colors.neon.violet;
  const stageName = stage?.name ?? "";
  const artistName = set.artists[0]?.name ?? set.display_name;
  const sLabel = formatTimeLabel(set.starts_at);
  const eLabel = formatTimeLabel(set.ends_at);

  return (
    <View style={styles.upNextCard}>
      {/* Left gradient bar — gradient.timelineLwwBar */}
      <View style={styles.upNextBar} />
      <View style={styles.upNextContent}>
        {/* "UP NEXT" label — text.daySectionAccent, letter-spacing 0.10em */}
        <Text style={styles.upNextLabel}>UP NEXT</Text>
        {/* Artist name — text.section.serifLg: Playfair 30px 700 */}
        <Text style={styles.upNextArtist}>{artistName}</Text>
        {/* Stage + time row — text.iconAccent */}
        <View style={styles.upNextMeta}>
          <StageDot color={stageColor} size={8} />
          <Text style={styles.upNextMetaText}>
            {stageName} · {sLabel} – {eLabel}
          </Text>
        </View>
      </View>
    </View>
  );
}

// ─── Timeline item ────────────────────────────────────────────────────────────
// Matches prototype l.372–386: time col + dot/line col + card

interface TimelineItemProps {
  set: SetDetail;
  stageName: string;
  stageColor: string;
  goingCount: number;
  goingMembers: MemberOut[];
  isLast: boolean;
  showRemove: boolean;
  onPress: () => void;
  onRemove: () => void;
}

const LINE_HEIGHT = 96; // Approximate card + gap height for the connector line

function TimelineItem({
  set,
  stageName,
  stageColor,
  goingCount,
  goingMembers,
  isLast,
  showRemove,
  onPress,
  onRemove,
}: TimelineItemProps) {
  const artistName = set.artists[0]?.name ?? set.display_name;
  const sLabel = formatTimeLabel(set.starts_at);
  const eLabel = formatTimeLabel(set.ends_at);
  const label = goingLabel(goingCount);

  const avatarMembers = goingMembers.slice(0, 4).map((m) => {
    const name = m.display_name_override ?? m.display_name;
    return {
      initials: name.trim().slice(0, 2).toUpperCase() || "??",
      color: m.avatar_color,
      textColor: colors.text.invertedDark,
    };
  });

  return (
    <View style={styles.timelineRow}>
      {/* Time column — prototype l.374–376 */}
      <View style={styles.timeCol}>
        <Text style={styles.timeStart}>{sLabel}</Text>
        <Text style={styles.timeEnd}>{eLabel}</Text>
      </View>

      {/* Dot + connector line column — prototype l.378 */}
      <View style={styles.dotCol}>
        <StageDot color={stageColor} size={11} withGlow />
        {!isLast && <View style={[styles.connectorLine, { height: LINE_HEIGHT }]} />}
      </View>

      {/* Card — prototype l.379–385 */}
      <View style={styles.card}>
        {showRemove && (
          <TouchableOpacity
            style={styles.removeBtn}
            onPress={onRemove}
            testID={`remove-pick-${set.set_id}`}
          >
            <Text style={styles.removeBtnText}>✕</Text>
          </TouchableOpacity>
        )}
        {/* Artist name — text.section.serifSm: Playfair 18px 700 */}
        <TouchableOpacity onPress={onPress} testID={`timeline-set-${set.set_id}`}>
          <Text style={styles.cardArtist}>{artistName}</Text>
        </TouchableOpacity>
        {/* Stage row */}
        <View style={styles.cardStageRow}>
          <StageDot color={stageColor} size={8} />
          <Text style={styles.cardStageName}>{stageName}</Text>
        </View>
        {/* Going row */}
        <View style={styles.cardGoingRow}>
          {goingMembers.length > 0 ? (
            <AvatarStack
              members={avatarMembers}
              size={26}
              ringColor="#1c143a"
              testID={`going-avatars-${set.set_id}`}
            />
          ) : (
            <View style={styles.goingPlaceholderDot} />
          )}
          <Text style={styles.cardGoingLabel}>{label}</Text>
        </View>
      </View>
    </View>
  );
}

// ─── Styles ──────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
  // Filter chips row — prototype l.346–349
  chipsRow: {
    flexDirection: "row",
    gap: 10,
    paddingHorizontal: spacing[9],
    paddingTop: 12,
    paddingBottom: 4,
  },
  chip: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 9,
    paddingHorizontal: spacing[6],
    borderRadius: radius.full,
    borderWidth: 1,
    backgroundColor: colors.bg.surfaceWeak,
    borderColor: colors.border.default,
  },
  chipActive: {
    backgroundColor: colors.neon.lilac,
    borderColor: colors.neon.lilac,
  },
  chipText: {
    color: colors.text.secondary,
    fontSize: 14,
    fontWeight: "700",
  },
  chipTextActive: {
    color: colors.text.invertedDark,
  },
  caret: {
    fontSize: 11,
  },
  // Scroll area
  scroll: {
    flex: 1,
  },
  scrollContent: {
    paddingHorizontal: spacing[9],
    paddingTop: 6,
    paddingBottom: 30,
  },
  // Empty states
  emptyCenter: {
    alignItems: "center",
    paddingTop: 90,
    paddingHorizontal: 30,
  },
  emptyIcon: {
    width: 64,
    height: 64,
    borderRadius: 32,
    borderWidth: 2,
    borderColor: colors.border.input,
    alignItems: "center",
    justifyContent: "center",
  },
  emptyIconGlyph: {
    fontSize: 26,
    color: colors.text.tertiary,
  },
  emptyEmoji: {
    fontSize: 40,
  },
  emptyHead: {
    fontSize: 22,
    fontWeight: "700",
    color: colors.text.eventName,
    marginTop: 18,
    textAlign: "center",
  },
  emptyBody: {
    fontSize: 14,
    fontWeight: "500",
    color: colors.text.tertiary,
    marginTop: 8,
    lineHeight: 22,
    textAlign: "center",
  },
  // UP NEXT card — prototype l.364–369
  upNextCard: {
    borderRadius: radius["2xl"],
    backgroundColor: colors.bg.surfaceWeak,
    borderWidth: 1,
    borderColor: colors.border.default,
    overflow: "hidden",
    flexDirection: "row",
    marginBottom: 18,
  },
  upNextBar: {
    width: 4,
    backgroundColor: colors.neon.pink,
  },
  upNextContent: {
    flex: 1,
    padding: 15,
    gap: 4,
  },
  // "UP NEXT" label — text.daySectionAccent, letter-spacing ~0.10em
  upNextLabel: {
    fontSize: 11,
    fontWeight: "700",
    color: colors.text.daySectionAccent,
    letterSpacing: 1.2,
    textTransform: "uppercase",
  },
  // Artist name — text.section.serifLg: Playfair 30px 700 (closest: fontFamily Playfair Bold)
  upNextArtist: {
    fontSize: 30,
    fontWeight: "700",
    color: colors.text.primary,
  },
  upNextMeta: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginTop: 4,
  },
  upNextMetaText: {
    fontSize: 13,
    fontWeight: "500",
    color: colors.text.iconAccent,
  },
  // GOING section header — prototype l.370
  goingSectionRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginBottom: 14,
  },
  goingBadgeIcon: {
    width: 18,
    height: 18,
    borderRadius: 9,
    backgroundColor: colors.neon.purple,
    alignItems: "center",
    justifyContent: "center",
  },
  goingCheckGlyph: {
    fontSize: 10,
    color: colors.text.invertedDark,
    fontWeight: "800",
  },
  goingSectionLabel: {
    flex: 1,
    fontSize: 13,
    fontWeight: "800",
    color: colors.text.mineSection,
    letterSpacing: 0.8,
    textTransform: "uppercase",
  },
  countBubble: {
    width: 26,
    height: 26,
    borderRadius: 13,
    backgroundColor: colors.bg.surfaceStrong,
    alignItems: "center",
    justifyContent: "center",
  },
  countBubbleText: {
    fontSize: 12,
    fontWeight: "700",
    color: colors.text.secondary,
  },
  // Timeline list
  timelineList: {
    position: "relative",
    paddingLeft: 8,
  },
  // Timeline row — prototype l.372–386
  timelineRow: {
    flexDirection: "row",
    gap: 14,
    marginBottom: 16,
  },
  // Time column — prototype l.374–376
  timeCol: {
    width: 52,
    flexShrink: 0,
    paddingTop: 2,
  },
  timeStart: {
    fontSize: 15,
    fontWeight: "700",
    color: colors.text.primary,
  },
  timeEnd: {
    fontSize: 12,
    fontWeight: "500",
    color: colors.text.tertiary,
  },
  // Dot + connector column — prototype l.378
  dotCol: {
    width: 14,
    flexShrink: 0,
    alignItems: "center",
    overflow: "visible",
  },
  connectorLine: {
    width: 1,
    backgroundColor: colors.border.default,
    marginTop: 4,
  },
  // Card — prototype l.379–385
  card: {
    flex: 1,
    borderRadius: 16,
    padding: 13,
    paddingHorizontal: 14,
    backgroundColor: colors.bg.surfaceWeak,
    borderWidth: 1,
    borderColor: colors.border.default,
    position: "relative",
    overflow: "hidden",
  },
  removeBtn: {
    position: "absolute",
    top: 11,
    right: 11,
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: colors.bg.surfaceStrong,
    alignItems: "center",
    justifyContent: "center",
    zIndex: 1,
  },
  removeBtnText: {
    fontSize: 13,
    color: colors.text.secondary,
  },
  // Artist name — text.section.serifSm: Playfair 18px 700
  cardArtist: {
    fontSize: 18,
    fontWeight: "700",
    color: colors.text.primary,
    paddingRight: 30, // avoid overlap with remove button
  },
  // Stage row
  cardStageRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 7,
    marginTop: 7,
  },
  cardStageName: {
    fontSize: 13,
    fontWeight: "500",
    color: colors.neon.lavenderDim,
  },
  // Going row
  cardGoingRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginTop: 10,
  },
  goingPlaceholderDot: {
    width: 26,
    height: 26,
    borderRadius: 13,
    backgroundColor: colors.bg.surfaceMed,
  },
  cardGoingLabel: {
    fontSize: 12,
    fontWeight: "500",
    color: colors.text.secondary,
  },
});
