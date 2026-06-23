import { ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { colors, spacing } from "@/theme/tokens";

interface Props {
  days: string[];
  selected: string;
  onSelect: (day: string) => void;
}

export function DayMenu({ days, selected, onSelect }: Props) {
  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      style={styles.scroll}
      contentContainerStyle={styles.content}
    >
      {days.map((day) => (
        <TouchableOpacity
          key={day}
          style={[styles.pill, selected === day && styles.pillActive]}
          onPress={() => onSelect(day)}
          testID={`day-tab-${day}`}
        >
          <Text style={[styles.label, selected === day && styles.labelActive]}>{day}</Text>
        </TouchableOpacity>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: {
    flexShrink: 0,
  },
  content: {
    paddingHorizontal: spacing.screenPad,
    gap: spacing[3],
    flexDirection: "row",
  },
  pill: {
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: colors.border.default,
  },
  pillActive: {
    backgroundColor: colors.neon.violet,
    borderColor: colors.neon.violet,
  },
  label: {
    color: colors.text.secondary,
    fontSize: 14,
    fontWeight: "600",
  },
  labelActive: {
    color: colors.text.primary,
  },
});
