import { useEffect, useRef } from "react";
import { Animated, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { Avatar } from "@/components/Avatar";
import { colors, motion, radius, spacing } from "@/theme/tokens";
import type { MemberOut } from "@/types/api";

interface Props {
  members: MemberOut[];
  selectedIds: Set<string>;
  onToggle: (memberId: string) => void;
  onClearAll: () => void;
  onDone: () => void;
}

export function FilterSheet({ members, selectedIds, onToggle, onClearAll, onDone }: Props) {
  // Backdrop: fadeIn 150ms; sheet: sheetUp 250ms — per DESIGN-TOKENS § 4.3 (prototype l.443)
  const backdropOpacity = useRef(new Animated.Value(0)).current;
  const sheetTranslate = useRef(new Animated.Value(600)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(backdropOpacity, {
        toValue: 1,
        duration: motion.fadeInToast,
        useNativeDriver: true,
      }),
      Animated.timing(sheetTranslate, {
        toValue: 0,
        duration: motion.sheetUp,
        useNativeDriver: true,
      }),
    ]).start();
  }, [backdropOpacity, sheetTranslate]);

  const allSelected = selectedIds.size === 0;
  const showingLabel = allSelected ? "Showing all" : `${selectedIds.size} selected`;

  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="box-none">
      {/* Backdrop — overlay.deep (prototype l.442) */}
      <Animated.View
        style={[styles.backdrop, { opacity: backdropOpacity }]}
        onTouchEnd={onDone}
        testID="filter-sheet-backdrop"
      />
      {/* Sheet — bg.high, radius 24 24 0 0, sheetUp animation (prototype l.443) */}
      <Animated.View
        style={[styles.sheet, { transform: [{ translateY: sheetTranslate }] }]}
        testID="filter-sheet"
      >
        <View style={styles.handle} />
        <View style={styles.sheetHeader}>
          <Text style={styles.sheetTitle}>Filter Group</Text>
          <TouchableOpacity style={styles.doneBtn} onPress={onDone} testID="filter-sheet-done">
            <Text style={styles.doneBtnText}>Done</Text>
          </TouchableOpacity>
        </View>
        <View style={styles.dividerRow}>
          <TouchableOpacity onPress={onClearAll} testID="filter-clear-all">
            <Text style={styles.clearAll}>Clear All</Text>
          </TouchableOpacity>
          <Text style={styles.showingLabel}>{showingLabel}</Text>
        </View>
        <View style={styles.memberList}>
          {members.map((m) => {
            const isOn = selectedIds.size === 0 || selectedIds.has(m.member_id);
            const name = m.display_name_override ?? m.display_name;
            const initials = name.trim().slice(0, 2).toUpperCase() || "??";
            return (
              <TouchableOpacity
                key={m.member_id}
                style={styles.memberRow}
                onPress={() => onToggle(m.member_id)}
                testID={`filter-member-${m.member_id}`}
              >
                <Avatar initials={initials} color={m.avatar_color} textColor={colors.text.invertedDark} size={34} />
                <Text style={styles.memberName}>{name}</Text>
                <View
                  style={[
                    styles.checkbox,
                    isOn ? styles.checkboxOn : styles.checkboxOff,
                  ]}
                >
                  {isOn && (
                    <Text style={styles.checkmark}>✓</Text>
                  )}
                </View>
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
    backgroundColor: colors.overlay.deep,
  },
  sheet: {
    position: "absolute",
    left: 0,
    right: 0,
    bottom: 0,
    zIndex: 41,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    backgroundColor: colors.bg.high,
    borderTopWidth: 1,
    borderColor: colors.border.mid,
    paddingHorizontal: spacing[9],
    paddingTop: spacing[6],
    paddingBottom: spacing[11],
  },
  handle: {
    width: 40,
    height: 5,
    borderRadius: radius.full,
    backgroundColor: colors.bg.surfaceStrong,
    alignSelf: "center",
    marginBottom: spacing[7],
  },
  sheetHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: spacing[8],
  },
  sheetTitle: {
    color: colors.text.primary,
    fontSize: 20,
    fontWeight: "800",
  },
  doneBtn: {
    backgroundColor: colors.bg.surfaceStrong,
    paddingHorizontal: spacing[7],
    paddingVertical: 7,
    borderRadius: radius.full,
  },
  doneBtnText: {
    color: colors.text.primary,
    fontSize: 15,
    fontWeight: "700",
  },
  dividerRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingBottom: spacing[6],
    borderBottomWidth: 1,
    borderBottomColor: colors.border.subtle,
    marginBottom: spacing[4],
  },
  clearAll: {
    color: colors.neon.purple,
    fontSize: 14,
    fontWeight: "700",
  },
  showingLabel: {
    color: colors.text.tertiary,
    fontSize: 13,
    fontWeight: "500",
  },
  memberList: {
    gap: 4,
  },
  memberRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    paddingVertical: 11,
    paddingHorizontal: 4,
  },
  memberName: {
    flex: 1,
    color: colors.text.primary,
    fontSize: 15,
    fontWeight: "600",
  },
  checkbox: {
    width: 24,
    height: 24,
    borderRadius: radius.sm,
    borderWidth: 1.5,
    alignItems: "center",
    justifyContent: "center",
  },
  checkboxOn: {
    backgroundColor: colors.neon.purple,
    borderColor: colors.neon.purple,
  },
  checkboxOff: {
    backgroundColor: "transparent",
    borderColor: colors.neon.purple,
  },
  checkmark: {
    color: colors.text.invertedDark,
    fontSize: 12,
    fontWeight: "700",
  },
});
