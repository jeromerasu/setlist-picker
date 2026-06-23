import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { colors, radius, spacing } from "@/theme/tokens";
import type { MyGroupListItem } from "@/types/api";
import type { HueEntry } from "@/theme/heroes";

const HERO_HEIGHT = 96;
const SCRIM = "rgba(10,7,18,0.54)";

export interface GroupCardProps {
  group: MyGroupListItem;
  hue: HueEntry;
  onPress: () => void;
  testID?: string;
}

export function GroupCard({ group, hue, onPress, testID }: GroupCardProps) {
  const isArchived = group.archived_at !== null;

  return (
    <TouchableOpacity
      style={styles.card}
      onPress={onPress}
      activeOpacity={0.85}
      testID={testID}
    >
      {/* Hero area with gradient-like dual-color bg */}
      <View style={[styles.hero, { backgroundColor: hue.from }]}>
        <View style={styles.scrim}>
          <Text style={styles.groupName} numberOfLines={1}>
            {group.name}
          </Text>
          {isArchived && (
            <View style={styles.archivedPill}>
              <Text style={styles.archivedText}>ARCHIVED</Text>
            </View>
          )}
        </View>
      </View>

      {/* Meta rows */}
      <View style={styles.meta}>
        <Text style={styles.metaRow} numberOfLines={1}>
          {"🎪 "}
          <Text style={styles.metaLabel} numberOfLines={1} ellipsizeMode="tail">
            {group.event_id}
          </Text>
        </Text>
        <Text style={styles.metaRow} numberOfLines={1}>
          {"📅 "}
          <Text style={styles.metaLabel}>
            {group.joined_at.slice(0, 10)}
          </Text>
        </Text>
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: radius["3xl"],
    backgroundColor: colors.bg.surfaceMed,
    borderWidth: 1,
    borderColor: colors.border.subtle,
    overflow: "hidden",
    marginBottom: spacing[3],
  },
  hero: {
    height: HERO_HEIGHT,
  },
  scrim: {
    flex: 1,
    backgroundColor: SCRIM,
    justifyContent: "flex-end",
    paddingHorizontal: spacing[5],
    paddingBottom: 13,
    flexDirection: "row",
    alignItems: "flex-end",
  },
  groupName: {
    flex: 1,
    color: colors.text.primary,
    fontSize: 18,
    fontWeight: "800",
  },
  archivedPill: {
    backgroundColor: "rgba(255,255,255,0.15)",
    borderRadius: 4,
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  archivedText: {
    color: colors.text.secondary,
    fontSize: 9,
    fontWeight: "700",
    letterSpacing: 0.6,
  },
  meta: {
    paddingHorizontal: spacing[5],
    paddingVertical: spacing[4],
    gap: 4,
  },
  metaRow: {
    color: colors.text.secondary,
    fontSize: 13,
  },
  metaLabel: {
    color: colors.text.secondary,
    fontSize: 13,
  },
});
