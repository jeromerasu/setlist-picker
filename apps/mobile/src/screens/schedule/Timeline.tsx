import { StyleSheet, Text, View } from "react-native";
import { colors } from "@/theme/tokens";
import { HOUR_HEIGHT_PX, DAY_START_HOUR_CONST } from "@/utils/gridLayout";

const HOURS_SHOWN = 14;

export function Timeline() {
  const hours = Array.from({ length: HOURS_SHOWN }, (_, i) => {
    const h = DAY_START_HOUR_CONST + i;
    const display = h > 12 ? `${h - 12}${h < 24 ? "pm" : "am"}` : h === 12 ? "12pm" : `${h}am`;
    return { h, display };
  });

  return (
    <View style={styles.root} pointerEvents="none">
      {hours.map(({ h, display }) => (
        <View key={h} style={[styles.row, { top: (h - DAY_START_HOUR_CONST) * HOUR_HEIGHT_PX }]}>
          <Text style={styles.label}>{display}</Text>
          <View style={styles.line} />
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    position: "absolute",
    left: 0,
    right: 0,
    top: 0,
    height: HOURS_SHOWN * HOUR_HEIGHT_PX,
  },
  row: {
    position: "absolute",
    left: 0,
    right: 0,
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  label: {
    color: colors.text.muted,
    fontSize: 11,
    width: 40,
    textAlign: "right",
  },
  line: {
    flex: 1,
    height: 1,
    backgroundColor: colors.border.weak,
  },
});
