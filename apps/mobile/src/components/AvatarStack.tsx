import { StyleSheet, Text, View } from "react-native";
import { Avatar } from "./Avatar";
import { colors } from "@/theme/tokens";

interface Member {
  initials: string;
  color: string;
  textColor?: string;
}

export interface AvatarStackProps {
  members: Member[];
  size?: 24 | 26;
  ringColor?: string;
  overlap?: number;
  testID?: string;
}

const MAX_VISIBLE = 4;

export function AvatarStack({
  members,
  size = 24,
  ringColor = colors.bg.mid,
  overlap = -7,
  testID,
}: AvatarStackProps) {
  if (members.length === 0) return <View style={{ width: 0 }} />;

  const visible = members.slice(0, MAX_VISIBLE);
  const extra = members.length - MAX_VISIBLE;

  return (
    <View style={styles.row} testID={testID}>
      {visible.map((m, i) => (
        <View key={i} style={i > 0 ? { marginLeft: overlap } : undefined}>
          <Avatar
            initials={m.initials}
            color={m.color}
            textColor={m.textColor}
            size={size}
            ringColor={ringColor}
          />
        </View>
      ))}
      {extra > 0 && (
        <View
          style={[
            styles.pill,
            {
              marginLeft: overlap,
              height: size,
              minWidth: size,
              borderRadius: size / 2,
            },
          ]}
        >
          <Text style={styles.pillText}>+{extra}</Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    alignItems: "center",
  },
  pill: {
    backgroundColor: colors.bg.surfaceMed,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 4,
  },
  pillText: {
    color: colors.text.secondary,
    fontSize: 10,
    fontWeight: "600",
  },
});
