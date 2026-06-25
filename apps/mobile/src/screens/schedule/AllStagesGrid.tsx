import { useState } from "react";
import {
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { usePickToggle } from "@/hooks/usePickToggle";
import { useGroupSchedule } from "@/hooks/useGroupSchedule";
import { AvatarStack } from "@/components/AvatarStack";
import { GoingMembersSheet } from "@/components/GoingMembersSheet";
import { colors, radius, spacing } from "@/theme/tokens";
import type { MemberOut, PickSummary, SetDetail, StageDetail } from "@/types/api";
import type { StageInfo } from "@/hooks/useScheduleData";

// Grid sizing constants — DESIGN-TOKENS § 3.3
const COLUMN_W = 148;      // size.gridColumn
const COLUMN_GAP = 10;     // size.gridColumnGap
const AXIS_W = 48;         // size.gridLeftAxis
const PXH = 84;            // size.gridHourPx
const CARD_W = 138;        // column minus inner margin
const CARD_MIN_H = 46;

type CardPickState = "none" | "going" | "maybe";

interface Props {
  sets: SetDetail[];
  stages: StageDetail[];
  stageBySetId: Map<string, StageInfo>;
  picks: PickSummary[];
  members: MemberOut[];
  myMemberId: string | undefined;
  invite_code: string;
}

// Decimal UTC hours from ISO datetime (consistent with rest of app's UTC convention)
function toDecH(iso: string): number {
  const d = new Date(iso);
  return d.getUTCHours() + d.getUTCMinutes() / 60;
}

// 24-hour time label: "HH:MM" (matches prototype fmt() function exactly)
function fmt24(h: number): string {
  const hh = Math.floor(h);
  const mm = Math.floor((h % 1) * 60);
  return `${hh}:${String(mm).padStart(2, "0")}`;
}

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) return (parts[0][0]! + parts[1][0]!).toUpperCase();
  return name.slice(0, 2).toUpperCase();
}

export function AllStagesGrid({
  sets,
  stages,
  stageBySetId,
  picks,
  members,
  myMemberId,
  invite_code,
}: Props) {
  const [searchQuery, setSearchQuery] = useState("");
  const [maybeSetIds, setMaybeSetIds] = useState(new Set<string>());
  const [openSheetSetId, setOpenSheetSetId] = useState<string | null>(null);
  const { mutate: togglePick } = usePickToggle();

  const dayLabel = sets[0]?.day_label ?? "";
  const { data: groupSchedule } = useGroupSchedule(invite_code, dayLabel);
  const groupScheduleBySetId = new Map(
    (groupSchedule?.sets ?? []).map((gs) => [gs.set_id, gs]),
  );

  // Sorted stage list drives column ordering
  const sortedStages = [...stages].sort((a, b) => a.display_order - b.display_order);

  // My active picks: filter by member + state="active"
  const myPickedSetIds = new Set(
    myMemberId != null
      ? picks.filter((p) => p.member_id === myMemberId && p.state === "active").map((p) => p.set_id)
      : picks.filter((p) => p.state === "active").map((p) => p.set_id),
  );

  function cardState(setId: string): CardPickState {
    if (!myPickedSetIds.has(setId)) return "none";
    if (maybeSetIds.has(setId)) return "maybe";
    return "going";
  }

  function handleTap(setId: string): void {
    const current = cardState(setId);
    if (current === "none") {
      togglePick({ invite_code, set_id: setId, is_picked: false, member_id: myMemberId ?? "" });
    } else if (current === "going") {
      setMaybeSetIds((prev) => new Set([...prev, setId]));
    } else {
      setMaybeSetIds((prev) => { const n = new Set(prev); n.delete(setId); return n; });
      togglePick({ invite_code, set_id: setId, is_picked: true, member_id: myMemberId ?? "" });
    }
  }

  // Grid dimension math — prototype lines 322-325
  const startHours = sets.map((s) => toDecH(s.starts_at));
  const endHours = sets.map((s) => toDecH(s.ends_at));
  const AX = sets.length > 0 ? Math.floor(Math.min(...startHours) - 0.5) : 12;
  const maxEnd = sets.length > 0 ? Math.max(...endHours, 24.5) : 24.5;
  const gridHeight = Math.ceil((maxEnd - AX) * PXH) + 20;
  const gridWidth = AXIS_W + sortedStages.length * (COLUMN_W + COLUMN_GAP);

  // set_id → column index
  const setColumnIndex = new Map<string, number>();
  sortedStages.forEach((stage, idx) => {
    stage.sets.forEach((s) => setColumnIndex.set(s.set_id, idx));
  });

  // Stage color from stageBySetId (any set in that stage shares the same color)
  function stageColor(stage: StageDetail): string {
    return stageBySetId.get(stage.sets[0]?.set_id ?? "")?.color ?? "#888";
  }

  // Hour lines
  const hourLines: Array<{ h: number; top: number; label: string }> = [];
  for (let h = AX; h <= Math.ceil(maxEnd); h++) {
    hourLines.push({ h, top: (h - AX) * PXH, label: fmt24(h) });
  }

  const q = searchQuery.trim().toLowerCase();
  const myMember = members.find((m) => m.member_id === myMemberId);

  const sheetSet = openSheetSetId != null ? sets.find((s) => s.set_id === openSheetSetId) : undefined;
  const sheetMembers = openSheetSetId != null
    ? (groupScheduleBySetId.get(openSheetSetId)?.going_members ?? [])
    : [];

  return (
    <View style={styles.root}>
      {/* Going members sheet overlay */}
      {openSheetSetId != null && (
        <GoingMembersSheet
          artistName={sheetSet?.artists[0]?.name ?? sheetSet?.display_name ?? ""}
          members={sheetMembers}
          onClose={() => setOpenSheetSetId(null)}
        />
      )}

      {/* Instruction + legend + search — prototype lines 301-311 */}
      <View style={styles.headerSection}>
        <View style={styles.instructionRow}>
          <Text style={styles.instructionEmoji}>👆</Text>
          <Text style={styles.instructionText}>Tap once for going, tap again for maybe</Text>
        </View>
        <View style={styles.legendRow}>
          <View style={styles.legendItem}>
            <View style={styles.legendChipMaybe} />
            <Text style={styles.legendLabel}>Maybe</Text>
          </View>
          <View style={styles.legendItem}>
            <View style={styles.legendChipGoing} />
            <Text style={styles.legendLabel}>Going</Text>
          </View>
        </View>
        <View style={styles.searchBox}>
          <View style={styles.searchIconCircle} />
          <TextInput
            style={styles.searchInput}
            value={searchQuery}
            onChangeText={setSearchQuery}
            placeholder="Search artist or set…"
            placeholderTextColor={colors.text.placeholder}
            autoCorrect={false}
            autoCapitalize="none"
            testID="grid-search"
          />
        </View>
      </View>

      {/* Scrollable grid — prototype lines 313-337 */}
      <View style={styles.gridArea}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false}>
          <View style={{ width: Math.max(gridWidth, AXIS_W) }}>
            {/* Stage headers — sticky (outside the vertical ScrollView) */}
            <View style={styles.stageHeaderRow}>
              <View style={{ width: AXIS_W }} />
              {sortedStages.map((stage) => (
                <View key={stage.stage_id} style={styles.stageHeaderTile}>
                  <View style={[styles.stageDot, { backgroundColor: stageColor(stage) }]} />
                  <Text style={styles.stageHeaderText} numberOfLines={1}>
                    {stage.name}
                  </Text>
                </View>
              ))}
            </View>

            {/* Vertically scrollable time grid */}
            <ScrollView showsVerticalScrollIndicator={false}>
              <View style={[styles.timeGrid, { height: gridHeight }]}>
                {/* Hour lines + labels */}
                {hourLines.map(({ h, top, label }) => (
                  <View key={h} style={[styles.hourLine, { top }]}>
                    <Text style={styles.hourLabel}>{label}</Text>
                  </View>
                ))}

                {/* Set cards */}
                {sets.map((set) => {
                  const colIdx = setColumnIndex.get(set.set_id) ?? 0;
                  const color = stageBySetId.get(set.set_id)?.color ?? "#888";
                  const startH = toDecH(set.starts_at);
                  const endH = toDecH(set.ends_at);
                  const cardTop = (startH - AX) * PXH;
                  const cardHeight = Math.max((endH - startH) * PXH - 8, CARD_MIN_H);
                  const cardLeft = AXIS_W + colIdx * (COLUMN_W + COLUMN_GAP);
                  const state = cardState(set.set_id);
                  const artistName = set.artists[0]?.name ?? set.display_name;
                  const dimmed = q.length > 0 && !artistName.toLowerCase().includes(q);

                  const cardBg =
                    state === "going"
                      ? color
                      : state === "maybe"
                        ? "transparent"
                        : "rgba(255,255,255,0.05)";
                  const cardBorder =
                    state === "none" ? "rgba(255,255,255,0.1)" : color;
                  const titleColor = state === "going" ? "#0d0818" : "#ffffff";
                  const timeColor =
                    state === "going" ? "rgba(13,8,24,0.7)" : "#9a8fc4";

                  // Group going avatars: prefer BE data; fall back to user's own avatar
                  const gsItem = groupScheduleBySetId.get(set.set_id);
                  const goingAvatars =
                    gsItem != null
                      ? gsItem.going_members.map((m) => ({
                          initials: m.display_name.trim().slice(0, 2).toUpperCase() || "??",
                          color: m.avatar_color,
                        }))
                      : state === "going" && myMember != null
                        ? [{ initials: getInitials(myMember.display_name), color: myMember.avatar_color }]
                        : [];

                  return (
                    <TouchableOpacity
                      key={set.set_id}
                      testID={`grid-set-${set.set_id}`}
                      activeOpacity={0.82}
                      onPress={() => handleTap(set.set_id)}
                      style={[
                        styles.card,
                        {
                          left: cardLeft,
                          top: cardTop,
                          height: cardHeight,
                          backgroundColor: cardBg,
                          borderColor: cardBorder,
                          opacity: dimmed ? 0.25 : 1,
                        },
                      ]}
                    >
                      <Text
                        style={[styles.cardTitle, { color: titleColor }]}
                        numberOfLines={2}
                      >
                        {artistName}
                      </Text>
                      <Text style={[styles.cardTime, { color: timeColor }]}>
                        {fmt24(startH)}
                      </Text>
                      {goingAvatars.length > 0 && (
                        <View style={styles.goingStack}>
                          <AvatarStack
                            members={goingAvatars}
                            size={18}
                            maxVisible={9}
                            ringColor="#140e34"
                            overlap={-6}
                            testID={`going-stack-${set.set_id}`}
                            onPress={() => setOpenSheetSetId(set.set_id)}
                          />
                        </View>
                      )}
                    </TouchableOpacity>
                  );
                })}
              </View>
            </ScrollView>
          </View>
        </ScrollView>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
  // Header section — prototype lines 300-311
  headerSection: {
    paddingHorizontal: spacing.screenPad,
    paddingTop: 12,
    paddingBottom: 4,
  },
  instructionRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  instructionEmoji: {
    fontSize: 14,
  },
  instructionText: {
    fontFamily: "Manrope-Medium",
    fontSize: 13,
    color: colors.neon.lavenderDim,
  },
  legendRow: {
    flexDirection: "row",
    gap: 16,
    marginTop: 9,
  },
  legendItem: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  legendChipMaybe: {
    width: 18,
    height: 13,
    borderRadius: radius.xs,
    borderWidth: 1.5,
    borderColor: colors.neon.purple,
  },
  legendChipGoing: {
    width: 18,
    height: 13,
    borderRadius: radius.xs,
    backgroundColor: colors.neon.purple,
  },
  legendLabel: {
    fontFamily: "Manrope-Medium",
    fontSize: 11,
    color: colors.text.secondary,
  },
  searchBox: {
    flexDirection: "row",
    alignItems: "center",
    height: 42,
    borderRadius: 11,
    backgroundColor: "rgba(255,255,255,0.07)",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.12)",
    paddingHorizontal: 13,
    marginTop: 11,
    gap: 9,
  },
  searchIconCircle: {
    width: 15,
    height: 15,
    borderRadius: 8,
    borderWidth: 1.5,
    borderColor: colors.text.tertiary,
  },
  searchInput: {
    flex: 1,
    fontFamily: "Manrope-Medium",
    fontSize: 14,
    color: colors.text.primary,
    padding: 0,
  },
  // Grid area
  gridArea: {
    flex: 1,
  },
  // Stage headers — prototype lines 316-320
  stageHeaderRow: {
    flexDirection: "row",
    paddingBottom: 0,
    backgroundColor: colors.bg.mid,
    zIndex: 6,
  },
  stageHeaderTile: {
    width: COLUMN_W,
    marginRight: COLUMN_GAP,
    height: 54,
    borderRadius: radius.md,
    backgroundColor: colors.bg.surfaceWeak,
    borderWidth: 1,
    borderColor: colors.border.default,
    alignItems: "center",
    justifyContent: "center",
  },
  stageDot: {
    width: 9,
    height: 9,
    borderRadius: 5,
    marginBottom: 5,
  },
  stageHeaderText: {
    fontFamily: "Manrope-Bold",
    fontSize: 13,
    color: colors.text.primary,
  },
  // Time grid — prototype lines 322-336
  timeGrid: {
    position: "relative",
    marginTop: 6,
  },
  hourLine: {
    position: "absolute",
    left: 0,
    right: 0,
    borderTopWidth: 1,
    borderTopColor: colors.border.weak,
  },
  hourLabel: {
    position: "absolute",
    left: 8,
    top: -8,
    fontFamily: "Manrope-SemiBold",
    fontSize: 11,
    color: colors.text.muted,
  },
  // Set card — prototype lines 326-334
  card: {
    position: "absolute",
    width: CARD_W,
    borderRadius: 13,
    borderWidth: 1.5,
    padding: 10,
    overflow: "hidden",
  },
  cardTitle: {
    fontFamily: "Manrope-Bold",
    fontSize: 14,
    lineHeight: 14 * 1.05,
  },
  cardTime: {
    fontFamily: "SpaceMono-Regular",
    fontSize: 11,
    marginTop: 3,
  },
  // Going member avatar stack — absolute at card bottom-left
  goingStack: {
    position: "absolute",
    bottom: 8,
    left: 8,
  },
});
