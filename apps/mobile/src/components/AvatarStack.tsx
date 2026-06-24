import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { Avatar } from "./Avatar";
import { colors } from "@/theme/tokens";

interface Member {
  initials: string;
  color: string;
  textColor?: string;
}

export interface AvatarStackProps {
  members: Member[];
  size?: 18 | 24 | 26;
  maxVisible?: number;
  ringColor?: string;
  overlap?: number;
  testID?: string;
  onPress?: () => void;
}

export function AvatarStack({
  members,
  size = 24,
  maxVisible = 4,
  ringColor = colors.bg.mid,
  overlap = -7,
  testID,
  onPress,
}: AvatarStackProps) {
  if (members.length === 0) return <View style={{ width: 0 }} />;

  const visible = members.slice(0, maxVisible);
  const extra = members.length - maxVisible;

  const avatarRow = (
    <View style={styles.row}>
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

  if (onPress != null) {
    // testID on the pressable so fireEvent.press works correctly in tests
    return (
      <TouchableOpacity onPress={onPress} activeOpacity={0.75} testID={testID}>
        {avatarRow}
      </TouchableOpacity>
    );
  }
  return <View testID={testID}>{avatarRow}</View>;
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
    color: colors.text.iconAccent,
    fontSize: 10,
    fontWeight: "600",
  },
});
