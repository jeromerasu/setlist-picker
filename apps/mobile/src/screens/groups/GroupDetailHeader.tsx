import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { BackChip } from "@/components/BackChip";
import { colors, spacing } from "@/theme/tokens";

interface Props {
  groupName: string;
  inviteCode: string;
  onBack: () => void;
  onShare: () => void;
  onSchedule: () => void;
  onSnapshot: () => void;
}

export function GroupDetailHeader({
  groupName,
  inviteCode,
  onBack,
  onShare,
  onSchedule,
  onSnapshot,
}: Props) {
  return (
    <View style={styles.root}>
      <View style={styles.topRow}>
        <BackChip onPress={onBack} />
        <TouchableOpacity onPress={onShare} testID="share-btn">
          <Text style={styles.action}>Share</Text>
        </TouchableOpacity>
      </View>

      <Text style={styles.name} numberOfLines={2}>
        {groupName}
      </Text>
      <Text style={styles.code}>{inviteCode}</Text>

      <View style={styles.pills}>
        <TouchableOpacity style={styles.pill} onPress={onSchedule} testID="schedule-btn">
          <Text style={styles.pillLabel}>📅 Schedule</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.pill} onPress={onSnapshot} testID="snapshot-btn">
          <Text style={styles.pillLabel}>📸 Right now</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    gap: spacing[4],
    paddingHorizontal: spacing.screenPad,
    paddingTop: spacing[9],
    paddingBottom: spacing[5],
  },
  topRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  action: {
    color: colors.neon.cyan,
    fontSize: 14,
    fontWeight: "600",
  },
  name: {
    color: colors.text.primary,
    fontSize: 26,
    fontWeight: "700",
    marginTop: spacing[3],
  },
  code: {
    color: colors.text.tertiary,
    fontSize: 13,
    letterSpacing: 2,
  },
  pills: {
    flexDirection: "row",
    gap: spacing[4],
    marginTop: spacing[3],
  },
  pill: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: colors.border.mid,
  },
  pillLabel: {
    color: colors.text.secondary,
    fontSize: 13,
  },
});
