import { useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  ScrollView,
  Share,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { useRoute, useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp, NativeStackScreenProps } from "@react-navigation/native-stack";
import { useQueryClient } from "@tanstack/react-query";
import { GroupDetailHeader } from "./GroupDetailHeader";
import { useGroupState } from "@/hooks/useGroupState";
import { useScheduleData } from "@/hooks/useScheduleData";
import { useMyGroups } from "@/hooks/useMyGroups";
import { usePickToggle } from "@/hooks/usePickToggle";
import { uniqueDays, setsForDay } from "@/utils/dayList";
import { getHue } from "@/theme/heroes";
import { ScreenContainer } from "@/components/ScreenContainer";
import { colors } from "@/theme/tokens";
import type { HomeStackParamList } from "@/navigation/types";
import type { MemberOut, SetDetail, PickSummary, StageDetail } from "@/types/api";
import type { StageInfo } from "@/hooks/useScheduleData";

type Props = NativeStackScreenProps<HomeStackParamList, "GroupDetail">;
type Nav = NativeStackNavigationProp<HomeStackParamList, "GroupDetail">;

// Decimal UTC hours from ISO datetime string
function toDecH(iso: string): number {
  const d = new Date(iso);
  return d.getUTCHours() + d.getUTCMinutes() / 60;
}

// "HH:MM" 24-hour label — matches prototype fmt()
function fmt24(h: number): string {
  const hh = Math.floor(h);
  const mm = Math.floor((h % 1) * 60);
  return `${hh}:${String(mm).padStart(2, "0")}`;
}

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) return (parts[0]![0]! + parts[1]![0]!).toUpperCase();
  return name.slice(0, 2).toUpperCase();
}

interface DayStageViewProps {
  dayLabel: string;
  sets: SetDetail[];
  stages: StageDetail[];
  stageBySetId: Map<string, StageInfo>;
  picks: PickSummary[];
  members: MemberOut[];
  myMemberId: string | undefined;
  invite_code: string;
}

function DayStageView({
  dayLabel,
  sets,
  stages,
  stageBySetId,
  picks,
  members,
  myMemberId,
  invite_code,
}: DayStageViewProps) {
  const { mutate: togglePick } = usePickToggle();
  const daySets = setsForDay(sets, dayLabel);

  // Group by stage in display_order
  const sortedStages = [...stages].sort((a, b) => a.display_order - b.display_order);
  const stageGroups = sortedStages
    .map((stage) => {
      const stageSets = daySets
        .filter((s) => stage.sets.some((ss) => ss.set_id === s.set_id))
        .sort((a, b) => new Date(a.starts_at).getTime() - new Date(b.starts_at).getTime());
      return { stage, sets: stageSets };
    })
    .filter((g) => g.sets.length > 0);

  const myPickedSetIds = new Set(
    myMemberId != null
      ? picks.filter((p) => p.member_id === myMemberId && p.state === "active").map((p) => p.set_id)
      : [],
  );

  function goingMembers(setId: string): MemberOut[] {
    const goingIds = new Set(
      picks.filter((p) => p.set_id === setId && p.state === "active").map((p) => p.member_id),
    );
    return members.filter((m) => goingIds.has(m.member_id));
  }

  if (stageGroups.length === 0) {
    return (
      <Text style={dsStyles.empty}>No sets for this day</Text>
    );
  }

  return (
    <View style={dsStyles.root}>
      {stageGroups.map(({ stage, sets: stageSets }) => {
        const stageColor = stageBySetId.get(stageSets[0]?.set_id ?? "")?.color ?? "#888";
        return (
          <View key={stage.stage_id} style={dsStyles.stageGroup}>
            {/* Stage header — prototype l.201 */}
            <View style={dsStyles.stageHeader}>
              <View style={[dsStyles.stageDot, { backgroundColor: stageColor }]} />
              <Text style={[dsStyles.stageName, { color: stageColor }]}>
                {stage.name.toUpperCase()}
              </Text>
            </View>
            {/* Set rows — prototype l.202–217 */}
            {stageSets.map((set) => {
              const isPicked = myPickedSetIds.has(set.set_id);
              const goers = goingMembers(set.set_id);
              const artistName = set.artists[0]?.name ?? set.display_name;
              const startH = toDecH(set.starts_at);
              const endH = toDecH(set.ends_at);
              const timeLabel = `${fmt24(startH)} – ${fmt24(endH)}`;
              const pickedBg = isPicked ? "rgba(255,45,155,0.12)" : "rgba(255,255,255,0.04)";
              const pickedBorder = isPicked
                ? colors.neon.pink
                : "rgba(255,255,255,0.1)";

              return (
                <TouchableOpacity
                  key={set.set_id}
                  testID={`day-set-${set.set_id}`}
                  style={[
                    dsStyles.setRow,
                    { backgroundColor: pickedBg, borderColor: pickedBorder },
                  ]}
                  activeOpacity={0.8}
                  onPress={() => {
                    togglePick({ invite_code, set_id: set.set_id, is_picked: isPicked });
                  }}
                >
                  <View style={dsStyles.setInfo}>
                    <Text style={dsStyles.setArtist} numberOfLines={1}>
                      {artistName}
                    </Text>
                    <Text style={dsStyles.setTime}>{timeLabel}</Text>
                  </View>
                  <View style={dsStyles.setRight}>
                    {/* Going avatars — prototype l.205–210 */}
                    {goers.length > 0 && (
                      <View style={dsStyles.goingStack}>
                        {goers.slice(0, 3).map((m, i) => (
                          <View
                            key={m.member_id}
                            style={[
                              dsStyles.goingAvatar,
                              { backgroundColor: m.avatar_color, marginLeft: i === 0 ? 0 : -6 },
                            ]}
                          >
                            <Text style={dsStyles.goingAvatarText}>
                              {getInitials(m.display_name)}
                            </Text>
                          </View>
                        ))}
                      </View>
                    )}
                    {/* Pick indicator — prototype l.211–216 */}
                    {isPicked ? (
                      <View style={dsStyles.pickDot} testID={`pick-dot-filled-${set.set_id}`} />
                    ) : (
                      <View
                        style={dsStyles.pickDotEmpty}
                        testID={`pick-dot-empty-${set.set_id}`}
                      />
                    )}
                  </View>
                </TouchableOpacity>
              );
            })}
          </View>
        );
      })}
    </View>
  );
}

const dsStyles = StyleSheet.create({
  root: {
    paddingTop: 14,
    paddingHorizontal: 22,
  },
  empty: {
    color: colors.text.muted,
    fontSize: 14,
    paddingHorizontal: 22,
    paddingTop: 16,
  },
  stageGroup: {
    marginBottom: 18,
  },
  stageHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginBottom: 10,
  },
  stageDot: {
    width: 9,
    height: 9,
    borderRadius: 5,
  },
  stageName: {
    fontFamily: "Orbitron-Bold",
    fontSize: 12,
    letterSpacing: 1.2,
  },
  setRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    borderRadius: 14,
    padding: 12,
    marginBottom: 9,
    borderWidth: 1.5,
  },
  setInfo: {
    flex: 1,
  },
  setArtist: {
    fontFamily: "Manrope-Bold",
    fontSize: 16,
    color: colors.text.primary,
  },
  setTime: {
    fontFamily: "SpaceMono-Regular",
    fontSize: 11,
    color: "#9a8fc4",
    marginTop: 3,
  },
  setRight: {
    flexDirection: "row",
    alignItems: "center",
    gap: 9,
  },
  goingStack: {
    flexDirection: "row",
  },
  goingAvatar: {
    width: 24,
    height: 24,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1.5,
    borderColor: "#140e34",
  },
  goingAvatarText: {
    fontFamily: "Manrope-ExtraBold",
    fontSize: 9,
    color: colors.text.primary,
  },
  pickDot: {
    width: 26,
    height: 26,
    borderRadius: 13,
    backgroundColor: colors.neon.pink,
  },
  pickDotEmpty: {
    width: 26,
    height: 26,
    borderRadius: 13,
    borderWidth: 1.5,
    borderColor: "rgba(255,255,255,0.28)",
  },
});

// ─── Main Screen ─────────────────────────────────────────────────────────────

const TOAST_MS = 2600; // motion.toastInvite — prototype l.169

export function GroupDetail() {
  const route = useRoute<Props["route"]>();
  const navigation = useNavigation<Nav>();
  const queryClient = useQueryClient();
  const { invite_code } = route.params;

  const { data: group, isLoading: groupLoading, error: groupError } = useGroupState(invite_code);
  const { sets, stages, stageBySetId } = useScheduleData(invite_code);
  const { data: myGroups } = useMyGroups();
  const { mutate: togglePick } = usePickToggle();

  const [inviteCopied, setInviteCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<"all" | number>("all");
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (toastTimer.current != null) clearTimeout(toastTimer.current);
    };
  }, []);

  const members = group?.members ?? [];
  const picks = group?.picks ?? [];
  const days = uniqueDays(sets);

  const myMemberId = myGroups?.groups.find((g) => g.invite_code === invite_code)?.member_id;
  const myMember = members.find((m) => m.member_id === myMemberId);

  // Alphabetically sorted sets for All Artists view
  const sortedSets = [...sets].sort((a, b) => {
    const nameA = (a.artists[0]?.name ?? a.display_name).toLowerCase();
    const nameB = (b.artists[0]?.name ?? b.display_name).toLowerCase();
    return nameA.localeCompare(nameB);
  });

  if (groupLoading) {
    return (
      <ScreenContainer style={styles.center}>
        <ActivityIndicator color={colors.neon.violet} />
      </ScreenContainer>
    );
  }

  if (groupError != null || group == null) {
    return (
      <ScreenContainer style={styles.center}>
        <Text style={styles.errorText}>Failed to load group</Text>
      </ScreenContainer>
    );
  }

  const handleBack = () => {
    void queryClient.invalidateQueries({ queryKey: ["my-groups"] });
    navigation.goBack();
  };

  const handleInvite = async () => {
    const msg = `Join my group on Setlist! Group code: ${group.invite_code}`;
    try {
      await Share.share({ message: msg });
    } catch (_) {
      // share cancelled — still show toast
    }
    setInviteCopied(true);
    toastTimer.current = setTimeout(() => setInviteCopied(false), TOAST_MS);
  };

  const handleSchedule = () => {
    navigation.navigate("Schedule", { invite_code });
  };

  const handleSnapshot = () => {
    navigation.navigate("RightNowSnapshot", { invite_code });
  };

  const handleArtistPress = (artistName: string) => {
    navigation.navigate("ArtistDetail", { artist_name: artistName });
  };

  const tabLabels = ["All Artists", ...days.map((_, i) => `Day ${i + 1}`)];

  return (
    <ScreenContainer style={styles.screen}>
      <ScrollView style={styles.scroll} showsVerticalScrollIndicator={false}>
        {/* Header — prototype l.150–169 */}
        <GroupDetailHeader
          groupName={group.name}
          eventName={group.event.name}
          startDate={group.event.start_date}
          endDate={group.event.end_date}
          location={group.event.location}
          inviteCode={group.invite_code}
          members={members}
          myMember={myMember}
          onBack={handleBack}
          onInvite={() => void handleInvite()}
          onSchedule={handleSchedule}
          onSnapshot={handleSnapshot}
          inviteCopied={inviteCopied}
        />

        {/* Artists section — prototype l.170–230 */}
        <View style={styles.artistsSection}>
          {/* Header: "Artists" + count — prototype l.172–175 */}
          <View style={styles.artistsHeader}>
            <Text style={styles.artistsTitle}>Artists</Text>
            <Text style={styles.artistsCount}>{sets.length} acts</Text>
          </View>

          {/* Day tab strip — prototype l.170–175 */}
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.tabStrip}
          >
            {tabLabels.map((label, i) => {
              const key = i === 0 ? "all" : i - 1;
              const isActive = activeTab === (i === 0 ? "all" : i - 1);
              return (
                <TouchableOpacity
                  key={label}
                  testID={`tab-${label.replace(" ", "-").toLowerCase()}`}
                  style={[styles.tab, isActive && styles.tabActive]}
                  onPress={() => setActiveTab(i === 0 ? "all" : i - 1)}
                >
                  <Text style={[styles.tabText, isActive && styles.tabTextActive]}>
                    {label}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </ScrollView>

          {/* Content area */}
          {activeTab === "all" ? (
            /* All Artists list — prototype l.176–210 */
            <View style={styles.allList}>
              {sortedSets.length === 0 && (
                <Text style={styles.empty}>No artists yet</Text>
              )}
              {sortedSets.map((set, i) => {
                const artistName = set.artists[0]?.name ?? set.display_name;
                const hue = getHue(i);
                const stageColor = stageBySetId.get(set.set_id)?.color ?? "#888";

                return (
                  <TouchableOpacity
                    key={set.set_id}
                    testID={`all-artist-${set.set_id}`}
                    style={styles.allArtistRow}
                    activeOpacity={0.8}
                    onPress={() => handleArtistPress(artistName)}
                  >
                    {/* HUES[i%6] thumb — prototype l.206 */}
                    <View
                      style={[
                        styles.artistThumb,
                        { backgroundColor: hue.from },
                      ]}
                    />
                    <View style={styles.artistInfo}>
                      <Text style={styles.artistName} numberOfLines={1}>
                        {artistName}
                      </Text>
                      <Text style={styles.artistDay}>{set.day_label}</Text>
                    </View>
                    {/* Stage color dot — prototype l.209 */}
                    <View
                      style={[styles.stageColorDot, { backgroundColor: stageColor }]}
                    />
                  </TouchableOpacity>
                );
              })}
            </View>
          ) : (
            /* Day stage view — prototype l.219–230 */
            <DayStageView
              dayLabel={days[activeTab] ?? ""}
              sets={sets}
              stages={stages}
              stageBySetId={stageBySetId}
              picks={picks}
              members={members}
              myMemberId={myMemberId}
              invite_code={invite_code}
            />
          )}
        </View>
      </ScrollView>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.bg.canvas,
  },
  scroll: {
    flex: 1,
  },
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.bg.canvas,
  },
  errorText: {
    color: colors.text.error,
    fontSize: 15,
  },
  // Artists section — prototype l.170
  artistsSection: {
    paddingTop: 18,
    paddingBottom: 48,
  },
  artistsHeader: {
    flexDirection: "row",
    alignItems: "baseline",
    justifyContent: "space-between",
    paddingHorizontal: 22,
  },
  artistsTitle: {
    fontFamily: "Manrope-ExtraBold",
    fontSize: 20,
    color: colors.text.primary,
  },
  artistsCount: {
    fontFamily: "Manrope-Medium",
    fontSize: 12,
    color: "#8a82b8",
  },
  // Tab strip — prototype l.170–175
  tabStrip: {
    paddingHorizontal: 22,
    paddingTop: 13,
    gap: 8,
    flexDirection: "row",
  },
  tab: {
    paddingHorizontal: 15,
    paddingVertical: 8,
    borderRadius: 99,
    backgroundColor: "rgba(255,255,255,0.06)",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.14)",
  },
  tabActive: {
    backgroundColor: "#a78bfa",
    borderColor: "transparent",
  },
  tabText: {
    fontFamily: "Manrope-Bold",
    fontSize: 13,
    color: "#cfc7e6",
  },
  tabTextActive: {
    color: "#1a0c2e",
  },
  // All Artists list — prototype l.176–210
  allList: {
    paddingHorizontal: 22,
    paddingTop: 14,
    gap: 9,
  },
  allArtistRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 13,
    borderRadius: 14,
    backgroundColor: "rgba(255,255,255,0.05)",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.1)",
    padding: 11,
  },
  artistThumb: {
    width: 46,
    height: 46,
    borderRadius: 11,
    flexShrink: 0,
  },
  artistInfo: {
    flex: 1,
  },
  artistName: {
    fontFamily: "Manrope-Bold",
    fontSize: 15,
    color: colors.text.primary,
  },
  artistDay: {
    fontFamily: "Manrope-Medium",
    fontSize: 12,
    color: "#a99fce",
    marginTop: 2,
  },
  stageColorDot: {
    width: 9,
    height: 9,
    borderRadius: 5,
  },
  empty: {
    color: colors.text.muted,
    fontSize: 14,
    paddingVertical: 16,
  },
});
