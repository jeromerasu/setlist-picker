import { useEffect, useRef } from "react";
import { Animated, ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { Avatar } from "@/components/Avatar";
import { colors, motion, radius, spacing } from "@/theme/tokens";

export interface GoingSheetMember {
  display_name: string;
  avatar_color: string;
}

interface Props {
  artistName: string;
  members: GoingSheetMember[];
  onClose: () => void;
}

export function GoingMembersSheet({ artistName, members, onClose }: Props) {
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

  const sorted = [...members].sort((a, b) =>
    a.display_name.localeCompare(b.display_name),
  );

  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="box-none">
      {/* Backdrop — overlay.deep */}
      <Animated.View
        style={[styles.backdrop, { opacity: backdropOpacity }]}
        onTouchEnd={onClose}
        testID="going-sheet-backdrop"
      />
      {/* Sheet — bg.high, radius 24 24 0 0 */}
      <Animated.View
        style={[styles.sheet, { transform: [{ translateY: sheetTranslate }] }]}
        testID="going-sheet"
      >
        <View style={styles.handle} />
        <View style={styles.sheetHeader}>
          <View style={styles.headerLeft}>
            <Text style={styles.sheetTitle} numberOfLines={1} testID="going-sheet-title">
              {artistName}
            </Text>
            <View style={styles.goingPill} testID="going-sheet-count-pill">
              <Text style={styles.goingPillText}>{members.length} GOING</Text>
            </View>
          </View>
          <TouchableOpacity style={styles.closeBtn} onPress={onClose} testID="going-sheet-close">
            <Text style={styles.closeBtnText}>Done</Text>
          </TouchableOpacity>
        </View>

        <ScrollView
          style={styles.list}
          contentContainerStyle={styles.listContent}
          showsVerticalScrollIndicator={false}
        >
          {sorted.map((m, i) => {
            const initials = m.display_name.trim().slice(0, 2).toUpperCase() || "??";
            return (
              <View key={i} style={styles.memberRow} testID={`going-sheet-member-${i}`}>
                <Avatar
                  initials={initials}
                  color={m.avatar_color}
                  textColor={colors.text.invertedDark}
                  size={34}
                />
                <Text style={styles.memberName}>{m.display_name}</Text>
                <View style={styles.badge}>
                  <Text style={styles.badgeText}>GOING</Text>
                </View>
              </View>
            );
          })}
        </ScrollView>
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    ...StyleSheet.absoluteFillObject,
    zIndex: 50,
    backgroundColor: colors.overlay.deep,
  },
  sheet: {
    position: "absolute",
    left: 0,
    right: 0,
    bottom: 0,
    zIndex: 51,
    maxHeight: "80%",
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
  headerLeft: {
    flex: 1,
    flexDirection: "column",
    gap: 5,
    marginRight: spacing[5],
  },
  sheetTitle: {
    fontFamily: "Manrope-ExtraBold",
    color: colors.text.primary,
    fontSize: 18,
    lineHeight: 22,
  },
  goingPill: {
    alignSelf: "flex-start",
    backgroundColor: colors.bg.surfaceMed,
    borderRadius: radius.full,
    paddingHorizontal: 10,
    paddingVertical: 3,
  },
  goingPillText: {
    fontFamily: "Manrope-Bold",
    color: colors.text.success,
    fontSize: 11,
    letterSpacing: 0.7,
  },
  closeBtn: {
    backgroundColor: colors.bg.surfaceStrong,
    paddingHorizontal: spacing[7],
    paddingVertical: 7,
    borderRadius: radius.full,
  },
  closeBtnText: {
    fontFamily: "Manrope-Bold",
    color: colors.text.primary,
    fontSize: 15,
    fontWeight: "700",
  },
  list: {
    flex: 0,
  },
  listContent: {
    gap: 0,
  },
  memberRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 13,
    paddingVertical: 11,
    borderBottomWidth: 1,
    borderBottomColor: colors.border.subtle,
  },
  memberName: {
    flex: 1,
    fontFamily: "Manrope-SemiBold",
    color: colors.text.primary,
    fontSize: 16,
  },
  badge: {
    backgroundColor: colors.bg.surfaceMed,
    borderRadius: radius.full,
    paddingHorizontal: 9,
    paddingVertical: 3,
  },
  badgeText: {
    fontFamily: "Manrope-Bold",
    color: colors.text.success,
    fontSize: 11,
    letterSpacing: 0.5,
  },
});
