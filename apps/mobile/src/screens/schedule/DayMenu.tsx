import { useEffect, useRef } from "react";
import { Animated, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { colors, motion, radius, spacing } from "@/theme/tokens";

interface Props {
  days: string[];
  selected: string;
  onSelect: (day: string) => void;
  onClose: () => void;
}

export function DayMenu({ days, selected, onSelect, onClose }: Props) {
  // fadeIn 150ms — motion.fadeInToast per DESIGN-TOKENS § 4.3 (prototype l.428)
  const opacity = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(opacity, {
      toValue: 1,
      duration: motion.fadeInToast,
      useNativeDriver: true,
    }).start();
  }, [opacity]);

  const handleSelect = (day: string) => {
    onSelect(day);
    onClose();
  };

  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="box-none">
      {/* Backdrop — overlay.dim (prototype l.428) */}
      <Animated.View
        style={[styles.backdrop, { opacity }]}
        onTouchEnd={onClose}
        testID="day-menu-backdrop"
      />
      {/* Centered dropdown — bg.elevated, top:84, fadeIn (prototype l.429) */}
      <Animated.View style={[styles.dropdownWrapper, { opacity }]} pointerEvents="box-none">
        <View style={styles.dropdown}>
          {days.map((day, i) => {
            const isActive = day === selected;
            const isLast = i === days.length - 1;
            return (
              <TouchableOpacity
                key={day}
                style={[styles.row, !isLast && styles.rowBorder]}
                onPress={() => handleSelect(day)}
                testID={`day-option-${day}`}
              >
                <View
                  style={[
                    styles.numBubble,
                    isActive ? styles.numBubbleActive : styles.numBubbleInactive,
                  ]}
                >
                  <Text style={[styles.numText, isActive && styles.numTextActive]}>
                    {i + 1}
                  </Text>
                </View>
                <Text
                  style={[styles.dayLabel, isActive ? styles.dayLabelActive : styles.dayLabelInactive]}
                >
                  Day {i + 1}
                </Text>
                {isActive && <Text style={styles.check}>✓</Text>}
              </TouchableOpacity>
            );
          })}
        </View>
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    ...StyleSheet.absoluteFillObject,
    zIndex: 40,
    backgroundColor: colors.overlay.dim,
  },
  dropdownWrapper: {
    position: "absolute",
    top: 84,
    left: 0,
    right: 0,
    zIndex: 41,
    alignItems: "center",
  },
  dropdown: {
    width: 230,
    borderRadius: radius["2xl"],
    overflow: "hidden",
    backgroundColor: colors.bg.elevated,
    borderWidth: 1,
    borderColor: colors.border.mid,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 16 },
    shadowOpacity: 0.5,
    shadowRadius: 20,
    elevation: 20,
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing[6],
    paddingVertical: spacing[6],
    paddingHorizontal: spacing[8],
  },
  rowBorder: {
    borderBottomWidth: 1,
    borderBottomColor: colors.border.weak,
  },
  numBubble: {
    width: 30,
    height: 30,
    borderRadius: 15,
    alignItems: "center",
    justifyContent: "center",
  },
  numBubbleActive: {
    backgroundColor: colors.neon.purple,
  },
  numBubbleInactive: {
    backgroundColor: colors.bg.surfaceStrong,
  },
  numText: {
    fontFamily: "Manrope-Bold",
    fontSize: 13,
    fontWeight: "700",
    color: colors.text.secondary,
  },
  numTextActive: {
    color: colors.text.invertedDark,
  },
  dayLabel: {
    fontFamily: "Manrope-SemiBold",
    flex: 1,
    fontSize: 15,
    fontWeight: "600",
  },
  dayLabelActive: {
    color: colors.text.primary,
  },
  dayLabelInactive: {
    color: colors.text.secondary,
  },
  check: {
    fontFamily: "Manrope-Bold",
    color: colors.neon.purple,
    fontSize: 14,
  },
});
