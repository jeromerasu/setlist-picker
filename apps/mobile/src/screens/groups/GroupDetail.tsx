import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from "react-native";
import { ScreenContainer } from "@/components/ScreenContainer";
import { useRoute, useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp, NativeStackScreenProps } from "@react-navigation/native-stack";
import { useQueryClient } from "@tanstack/react-query";
import { GroupDetailHeader } from "./GroupDetailHeader";
import { ArtistRowAll } from "./ArtistRowAll";
import { useGroupState } from "@/hooks/useGroupState";
import { useEventLineup } from "@/hooks/useEventLineup";
import { usePickToggle } from "@/hooks/usePickToggle";
import { bucketByDay, pickedSetIds } from "@/utils/dayBuckets";
import { shareInvite } from "@/utils/inviteShare";
import { colors, spacing } from "@/theme/tokens";
import type { HomeStackParamList } from "@/navigation/types";
import type { PickSummary } from "@/types/api";

type Props = NativeStackScreenProps<HomeStackParamList, "GroupDetail">;
type Nav = NativeStackNavigationProp<HomeStackParamList, "GroupDetail">;

function pickCountForSet(picks: PickSummary[], setId: string): number {
  return picks.filter((p) => p.set_id === setId).length;
}

export function GroupDetail() {
  const route = useRoute<Props["route"]>();
  const navigation = useNavigation<Nav>();
  const queryClient = useQueryClient();
  const { invite_code } = route.params;

  const { data: group, isLoading: groupLoading, error: groupError } = useGroupState(invite_code);
  const eventId = group?.event.event_id ?? "";
  const { data: lineup } = useEventLineup(eventId);

  const { mutate: togglePick } = usePickToggle();

  const sets = lineup?.sets ?? [];
  const picks = group?.picks ?? [];
  const myPicked = pickedSetIds(picks);
  const buckets = bucketByDay(sets);

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

  const handleToggle = (setId: string, isPicked: boolean) => {
    togglePick({ invite_code, set_id: setId, is_picked: isPicked });
  };

  const handleNavigateArtist = (artistName: string) => {
    navigation.navigate("ArtistDetail", { artist_name: artistName });
  };

  const handleShare = async () => {
    await shareInvite(group.name, group.invite_code);
  };

  const handleSchedule = () => {
    navigation.navigate("Schedule", { invite_code });
  };

  const handleSnapshot = () => {
    navigation.navigate("RightNowSnapshot", { invite_code });
  };

  const handleBack = () => {
    void queryClient.invalidateQueries({ queryKey: ["my-groups"] });
    navigation.goBack();
  };

  return (
    <ScreenContainer style={styles.screen}>
      <GroupDetailHeader
        groupName={group.name}
        inviteCode={group.invite_code}
        onBack={handleBack}
        onShare={handleShare}
        onSchedule={handleSchedule}
        onSnapshot={handleSnapshot}
      />

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
      >
        {buckets.length === 0 && (
          <Text style={styles.emptyText}>No artists in lineup yet.</Text>
        )}
        {buckets.map((bucket) => (
          <View key={bucket.label} style={styles.daySection}>
            <Text style={styles.dayLabel}>{bucket.label}</Text>
            {bucket.sets.map((set) => (
              <ArtistRowAll
                key={set.set_id}
                set={set}
                isPicked={myPicked.has(set.set_id)}
                memberCount={pickCountForSet(picks, set.set_id)}
                onToggle={handleToggle}
                onNavigate={handleNavigateArtist}
              />
            ))}
          </View>
        ))}
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
  scrollContent: {
    paddingHorizontal: spacing.screenPad,
    paddingBottom: spacing[12],
    gap: spacing[6],
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
  daySection: {
    gap: 0,
  },
  dayLabel: {
    color: colors.text.secondary,
    fontSize: 13,
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: 1.5,
    paddingVertical: spacing[4],
    borderBottomWidth: 1,
    borderBottomColor: colors.border.weak,
  },
  emptyText: {
    color: colors.text.muted,
    fontSize: 15,
    textAlign: "center",
    marginTop: spacing[9],
  },
});
