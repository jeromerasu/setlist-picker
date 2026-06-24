import { useState } from "react";
import { ActivityIndicator, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { useRoute, useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp, NativeStackScreenProps } from "@react-navigation/native-stack";
import { ScreenContainer } from "@/components/ScreenContainer";
import { BackChip } from "@/components/BackChip";
import { DayMenu } from "./DayMenu";
import { AllStagesGrid } from "./AllStagesGrid";
import { ScheduleTimeline } from "./ScheduleTimeline";
import { FilterSheet } from "./FilterSheet";
import { useScheduleData } from "@/hooks/useScheduleData";
import { useGroupState } from "@/hooks/useGroupState";
import { useGroupSchedule } from "@/hooks/useGroupSchedule";
import { usePickToggle } from "@/hooks/usePickToggle";
import { uniqueDays, setsForDay } from "@/utils/dayList";
import { colors, spacing } from "@/theme/tokens";
import type { HomeStackParamList } from "@/navigation/types";
import type { SetDetail } from "@/types/api";

type Props = NativeStackScreenProps<HomeStackParamList, "Schedule">;
type Nav = NativeStackNavigationProp<HomeStackParamList, "Schedule">;

type TabId = "all-stages" | "schedule";

export function Schedule() {
  const route = useRoute<Props["route"]>();
  const navigation = useNavigation<Nav>();
  const { invite_code } = route.params;

  const { sets, stages, stageBySetId, myMemberId, isLoading } = useScheduleData(invite_code);
  const { data: group } = useGroupState(invite_code);
  const { mutate: togglePick } = usePickToggle();

  const days = uniqueDays(sets);
  const [selectedDay, setSelectedDay] = useState("");
  const [dayMenuOpen, setDayMenuOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<TabId>("all-stages");
  const [filterSheetOpen, setFilterSheetOpen] = useState(false);
  const [selectedMemberIds, setSelectedMemberIds] = useState<Set<string>>(new Set());

  const activeDay = selectedDay !== "" ? selectedDay : (days[0] ?? "");
  const { data: groupSchedule } = useGroupSchedule(invite_code, activeDay);
  const groupScheduleBySetId = new Map(
    (groupSchedule?.sets ?? []).map((gs) => [gs.set_id, gs]),
  );

  const dayIndex = days.indexOf(activeDay);
  const dayNumber = dayIndex >= 0 ? dayIndex + 1 : 1;

  const daySets = setsForDay(sets, activeDay);
  const members = group?.members ?? [];
  const picks = group?.picks ?? [];

  const handleSelectSet = (set: SetDetail) => {
    const artistName = set.artists[0]?.name ?? set.display_name;
    navigation.navigate("ArtistDetail", { artist_name: artistName });
  };

  const handleRemovePick = (setId: string) => {
    console.info("[schedule] remove pick", { setId, invite_code });
    togglePick({ invite_code, set_id: setId, is_picked: true });
  };

  const handleToggleMember = (memberId: string) => {
    setSelectedMemberIds((prev) => {
      const next = new Set(prev);
      if (next.has(memberId)) {
        next.delete(memberId);
      } else {
        next.add(memberId);
      }
      return next;
    });
  };

  const handleClearAllMembers = () => setSelectedMemberIds(new Set());

  if (isLoading) {
    return (
      <ScreenContainer style={styles.center}>
        <ActivityIndicator color={colors.neon.violet} />
      </ScreenContainer>
    );
  }

  const allStagesActive = activeTab === "all-stages";
  const scheduleActive = activeTab === "schedule";

  // Filter group picks by selectedMemberIds (empty = all members shown)
  const filteredPicks =
    selectedMemberIds.size > 0
      ? picks.filter((p) => selectedMemberIds.has(p.member_id))
      : picks;

  return (
    <ScreenContainer style={styles.screen}>
      {/* Top bar — prototype l.286–290 */}
      <View style={styles.header}>
        <BackChip onPress={() => navigation.goBack()} />
        {/* Day dropdown button: "Day N ⌄" — prototype l.288 */}
        <TouchableOpacity
          style={styles.dayBtn}
          onPress={() => setDayMenuOpen(true)}
          testID="day-picker-btn"
        >
          <Text style={styles.dayBtnText}>Day {dayNumber}</Text>
          <Text style={styles.dayBtnCaret}> ⌄</Text>
        </TouchableOpacity>
        {/* Share icon placeholder — prototype l.289 */}
        <View style={styles.iconBtn} />
      </View>

      {/* Sub tabs: All Stages | Schedule — prototype l.293–296 */}
      <View style={styles.tabRow}>
        <TouchableOpacity
          style={[styles.tab, allStagesActive && styles.tabActive]}
          onPress={() => setActiveTab("all-stages")}
          testID="all-stages-tab"
        >
          <Text style={[styles.tabText, allStagesActive ? styles.tabTextActive : styles.tabTextInactive]}>
            All Stages
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, scheduleActive && styles.tabActive]}
          onPress={() => setActiveTab("schedule")}
          testID="schedule-tab"
        >
          <Text style={[styles.tabText, scheduleActive ? styles.tabTextActive : styles.tabTextInactive]}>
            Schedule
          </Text>
        </TouchableOpacity>
      </View>

      {/* Content area */}
      <View style={styles.content}>
        {allStagesActive ? (
          <AllStagesGrid
            sets={daySets}
            stages={stages}
            stageBySetId={stageBySetId}
            picks={picks}
            members={members}
            myMemberId={myMemberId}
            invite_code={invite_code}
          />
        ) : (
          <ScheduleTimeline
            sets={sets}
            picks={filteredPicks}
            members={members}
            myMemberId={myMemberId}
            stageBySetId={stageBySetId}
            activeDay={activeDay}
            groupScheduleBySetId={groupScheduleBySetId}
            onNavigateToArtist={handleSelectSet}
            onRemovePick={handleRemovePick}
            onOpenFilterSheet={() => setFilterSheetOpen(true)}
          />
        )}
      </View>

      {/* Day picker overlay — prototype l.427–438 */}
      {dayMenuOpen && (
        <DayMenu
          days={days}
          selected={activeDay}
          onSelect={(day) => {
            setSelectedDay(day);
            setDayMenuOpen(false);
          }}
          onClose={() => setDayMenuOpen(false)}
        />
      )}

      {/* Filter group sheet — prototype l.440–457 */}
      {filterSheetOpen && (
        <FilterSheet
          members={members}
          selectedIds={selectedMemberIds}
          onToggle={handleToggleMember}
          onClearAll={handleClearAllMembers}
          onDone={() => setFilterSheetOpen(false)}
        />
      )}
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.bg.canvas,
  },
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.bg.canvas,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: spacing[7],
    paddingTop: spacing[3],
    paddingBottom: 4,
  },
  dayBtn: {
    flexDirection: "row",
    alignItems: "center",
  },
  dayBtnText: {
    color: colors.text.primary,
    fontSize: 19,
    fontWeight: "700",
  },
  dayBtnCaret: {
    color: colors.neon.purple,
    fontSize: 13,
  },
  iconBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: colors.bg.surfaceStrong,
  },
  tabRow: {
    flexDirection: "row",
    marginTop: 14,
    paddingHorizontal: spacing[9],
  },
  tab: {
    flex: 1,
    paddingBottom: 11,
    alignItems: "center",
    justifyContent: "center",
    borderBottomWidth: 2,
    borderBottomColor: "transparent",
  },
  tabActive: {
    borderBottomColor: colors.text.primary,
  },
  tabText: {
    fontSize: 15,
    fontWeight: "600",
  },
  tabTextActive: {
    color: colors.text.primary,
  },
  tabTextInactive: {
    color: colors.text.tertiary,
  },
  content: {
    flex: 1,
    overflow: "hidden",
  },
});
