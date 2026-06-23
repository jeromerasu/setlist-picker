import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { Avatar } from "@/components/Avatar";
import { HUES } from "@/theme/heroes";
import { colors, spacing } from "@/theme/tokens";
import type { SetDetail } from "@/types/api";

function toInitials(name: string): string {
  const words = name.trim().split(/\s+/);
  if (words.length === 1) return (words[0] ?? "").slice(0, 2).toUpperCase();
  return ((words[0]?.[0] ?? "") + (words[1]?.[0] ?? "")).toUpperCase();
}

function toColor(name: string): string {
  let h = 5381;
  for (let i = 0; i < name.length; i++) {
    h = ((h << 5) + h) ^ name.charCodeAt(i);
    h = h >>> 0;
  }
  return HUES[h % HUES.length]!.from;
}

interface Props {
  set: SetDetail;
  isPicked: boolean;
  memberCount: number;
  onToggle: (setId: string, currentlyPicked: boolean) => void;
  onNavigate: (artistName: string) => void;
}

export function ArtistRowAll({
  set,
  isPicked,
  memberCount,
  onToggle,
  onNavigate,
}: Props) {
  const primaryArtist = set.artists[0];
  const displayName = primaryArtist?.name ?? set.display_name;

  return (
    <View style={styles.row}>
      <TouchableOpacity
        style={styles.mainArea}
        onPress={() => onNavigate(displayName)}
        testID={`artist-row-${set.set_id}`}
      >
        <Avatar initials={toInitials(displayName)} color={toColor(displayName)} size={40} />
        <View style={styles.info}>
          <Text style={styles.name} numberOfLines={1}>
            {displayName}
          </Text>
          <Text style={styles.meta}>{set.day_label}</Text>
        </View>
      </TouchableOpacity>

      <TouchableOpacity
        style={[styles.heartBtn, isPicked && styles.heartPicked]}
        onPress={() => onToggle(set.set_id, isPicked)}
        testID={`pick-btn-${set.set_id}`}
      >
        <Text style={styles.heart}>{isPicked ? "♥" : "♡"}</Text>
        {memberCount > 0 && (
          <Text style={styles.count}>{memberCount}</Text>
        )}
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 10,
    gap: spacing[4],
  },
  mainArea: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    gap: spacing[4],
  },
  info: {
    flex: 1,
    gap: 2,
  },
  name: {
    color: colors.text.primary,
    fontSize: 15,
    fontWeight: "600",
  },
  meta: {
    color: colors.text.secondary,
    fontSize: 13,
  },
  heartBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: colors.border.default,
  },
  heartPicked: {
    borderColor: colors.neon.pink,
    backgroundColor: "rgba(255,45,155,0.08)",
  },
  heart: {
    fontSize: 16,
    color: colors.neon.pink,
  },
  count: {
    color: colors.text.secondary,
    fontSize: 13,
    fontWeight: "600",
  },
});
