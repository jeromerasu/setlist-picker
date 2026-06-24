import { ActivityIndicator, ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { ScreenContainer } from "@/components/ScreenContainer";
import { useRef } from "react";
import { useRoute, useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp, NativeStackScreenProps } from "@react-navigation/native-stack";
import { BackChip } from "@/components/BackChip";
import { AvatarStack } from "@/components/AvatarStack";
import { useSnapshot } from "@/hooks/useSnapshot";
import { captureAndShare } from "@/utils/captureScreenshot";
import { colors, spacing } from "@/theme/tokens";
import type { HomeStackParamList } from "@/navigation/types";
import type { SnapshotSet } from "@/types/api";

type Props = NativeStackScreenProps<HomeStackParamList, "RightNowSnapshot">;
type Nav = NativeStackNavigationProp<HomeStackParamList, "RightNowSnapshot">;

export function RightNowSnapshot() {
  const route = useRoute<Props["route"]>();
  const navigation = useNavigation<Nav>();
  const { invite_code, at } = route.params;
  const viewShotRef = useRef<any>(null);

  const { data, isLoading, error } = useSnapshot(invite_code, at);

  const handleShare = async () => {
    await captureAndShare(viewShotRef, `setlist-snapshot-${invite_code}.png`);
  };

  if (isLoading) {
    return (
      <ScreenContainer style={styles.center}>
        <ActivityIndicator color={colors.neon.violet} />
      </ScreenContainer>
    );
  }

  if (error != null || data == null) {
    return (
      <ScreenContainer style={styles.center}>
        <Text style={styles.errorText}>Snapshot unavailable</Text>
      </ScreenContainer>
    );
  }

  const allSets: SnapshotSet[] = data.stages.flatMap((s) => s.sets);

  return (
    <ScreenContainer style={styles.screen}>
      <View style={styles.header}>
        <BackChip onPress={() => navigation.goBack()} />
        <Text style={styles.title} numberOfLines={1} testID="snapshot-group-name">
          {data.group_name}
        </Text>
        <TouchableOpacity onPress={handleShare} testID="share-btn">
          <Text style={styles.shareLabel}>Share</Text>
        </TouchableOpacity>
      </View>

      <View ref={viewShotRef} style={styles.card}>
        <Text style={styles.cardTitle}>{data.event_name}</Text>
        <Text style={styles.cardAt}>{new Date(data.snapshot_at).toLocaleString()}</Text>

        <ScrollView showsVerticalScrollIndicator={false} style={styles.scroll}>
          {allSets.length === 0 && (
            <Text style={styles.empty}>No picks in the next {data.window_minutes} min.</Text>
          )}
          {allSets.map((set) => (
            <View key={set.set_id} style={styles.setRow} testID={`snapshot-set-${set.set_id}`}>
              <View style={styles.setInfo}>
                <Text style={styles.setName} numberOfLines={1}>
                  {set.display_name}
                </Text>
                <Text style={styles.setMeta}>{set.day_label}</Text>
              </View>
              <AvatarStack
                members={set.pickers.map((p) => ({
                  initials: p.display_name.slice(0, 2).toUpperCase(),
                  color: p.avatar_color,
                }))}
              />
            </View>
          ))}
        </ScrollView>
      </View>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.bg.canvas,
    paddingTop: spacing[9],
    paddingHorizontal: spacing.screenPad,
    gap: spacing[6],
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing[4],
  },
  title: {
    flex: 1,
    color: colors.text.primary,
    fontSize: 18,
    fontWeight: "700",
  },
  shareLabel: {
    color: colors.neon.cyan,
    fontSize: 14,
    fontWeight: "600",
  },
  card: {
    flex: 1,
    backgroundColor: colors.bg.mid,
    borderRadius: 16,
    padding: spacing[6],
    gap: spacing[4],
  },
  cardTitle: {
    color: colors.text.primary,
    fontSize: 20,
    fontWeight: "700",
  },
  cardAt: {
    color: colors.text.tertiary,
    fontSize: 13,
  },
  scroll: { flex: 1 },
  setRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: colors.border.weak,
  },
  setInfo: { flex: 1, gap: 2 },
  setName: {
    color: colors.text.primary,
    fontSize: 14,
    fontWeight: "600",
  },
  setMeta: {
    color: colors.text.secondary,
    fontSize: 12,
  },
  empty: {
    color: colors.text.muted,
    fontSize: 14,
    textAlign: "center",
    marginTop: spacing[9],
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
});
