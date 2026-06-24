import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { GradientText } from "@/components/GradientText";
import { colors } from "@/theme/tokens";
import type { MemberOut } from "@/types/api";

interface Props {
  groupName: string;
  eventName: string;
  startDate: string;
  endDate: string;
  location: string | null;
  inviteCode: string;
  members: MemberOut[];
  myMember: MemberOut | undefined;
  onBack: () => void;
  onInvite: () => void;
  onSchedule: () => void;
  onSnapshot: () => void;
  inviteCopied: boolean;
}

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) return (parts[0]![0]! + parts[1]![0]!).toUpperCase();
  return name.slice(0, 2).toUpperCase();
}

export function GroupDetailHeader({
  groupName,
  eventName,
  startDate,
  endDate,
  location,
  inviteCode,
  members,
  myMember,
  onBack,
  onInvite,
  onSchedule,
  onSnapshot,
  inviteCopied,
}: Props) {
  return (
    <View style={styles.root}>
      {/* Top bar: back + group name (gradient) + user avatar — prototype l.152–163 */}
      <View style={styles.topBar}>
        <TouchableOpacity
          style={styles.backBtn}
          onPress={onBack}
          accessibilityLabel="Go back"
          testID="back-btn"
        >
          <Text style={styles.backGlyph}>‹</Text>
        </TouchableOpacity>
        <View style={styles.nameFlex}>
          <GradientText font="Orbitron-Black" weight={900} size={28} letterSpacing={0.02}>
            {groupName}
          </GradientText>
        </View>
        {myMember != null ? (
          <View style={[styles.userAvatar, { backgroundColor: myMember.avatar_color }]}>
            <Text style={styles.userAvatarText}>{getInitials(myMember.display_name)}</Text>
          </View>
        ) : (
          <View style={styles.userAvatar} />
        )}
      </View>

      {/* Event info block — prototype l.157–163 */}
      <View style={styles.eventBlock}>
        <View style={styles.infoRow}>
          <Text style={styles.infoIcon}>🎪</Text>
          <Text style={styles.infoName}>{eventName}</Text>
        </View>
        <View style={styles.infoRow}>
          <Text style={styles.infoIcon}>📅</Text>
          <Text style={styles.infoSub}>{startDate} – {endDate}</Text>
        </View>
        {location != null && (
          <View style={styles.infoRow}>
            <Text style={styles.infoIcon}>📍</Text>
            <Text style={styles.infoSub}>{location}</Text>
          </View>
        )}
        <View style={styles.infoRow}>
          <Text style={styles.infoIcon}>🔑</Text>
          <Text style={styles.infoCode}>{inviteCode}</Text>
        </View>
      </View>

      {/* Members stack — prototype l.160 */}
      {members.length > 0 && (
        <View style={styles.membersRow}>
          {members.slice(0, 3).map((m, i) => (
            <View
              key={m.member_id}
              style={[
                styles.memberAvatar,
                { backgroundColor: m.avatar_color, marginLeft: i === 0 ? 0 : -7 },
              ]}
            >
              <Text style={styles.memberAvatarText}>{getInitials(m.display_name)}</Text>
            </View>
          ))}
          {members.length > 3 && (
            <Text style={styles.memberOverflow}>+{members.length - 3}</Text>
          )}
        </View>
      )}

      {/* CTA row — prototype l.164–169 */}
      <View style={styles.ctaRow}>
        <TouchableOpacity style={styles.inviteBtn} onPress={onInvite} testID="invite-btn">
          <Text style={styles.ctaText}>Invite friends</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.scheduleBtn} onPress={onSchedule} testID="schedule-btn">
          <Text style={styles.ctaText}>Schedule</Text>
        </TouchableOpacity>
      </View>

      {/* Right now CTA — preserved from FE-005 */}
      <TouchableOpacity style={styles.snapshotRow} onPress={onSnapshot} testID="snapshot-btn">
        <Text style={styles.snapshotText}>📸 Right now</Text>
      </TouchableOpacity>

      {/* Invite toast — prototype l.169 (2600ms timer managed by parent) */}
      {inviteCopied && (
        <Text style={styles.inviteToast} testID="invite-toast">
          ✓ Invite copied — "Join my group on Setlist! Group code: {inviteCode}"
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    paddingBottom: 18,
    borderBottomWidth: 1,
    borderBottomColor: "rgba(255,255,255,0.08)",
  },
  // Top bar — prototype l.152
  topBar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 22,
    paddingTop: 10,
  },
  backBtn: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: "rgba(255,255,255,0.08)",
    alignItems: "center",
    justifyContent: "center",
  },
  backGlyph: {
    color: colors.text.primary,
    fontSize: 20,
    lineHeight: 24,
  },
  nameFlex: {
    flex: 1,
    alignItems: "center",
    paddingHorizontal: 8,
  },
  userAvatar: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: colors.neon.violetAvatar,
    alignItems: "center",
    justifyContent: "center",
  },
  userAvatarText: {
    fontFamily: "Manrope-ExtraBold",
    fontSize: 14,
    color: colors.text.primary,
  },
  // Event info — prototype l.157–163
  eventBlock: {
    paddingHorizontal: 22,
    paddingTop: 14,
    gap: 8,
  },
  infoRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  infoIcon: {
    fontSize: 13,
    width: 18,
  },
  infoName: {
    fontFamily: "Manrope-SemiBold",
    fontSize: 13,
    color: colors.text.primary,
  },
  infoSub: {
    fontFamily: "Manrope-Medium",
    fontSize: 13,
    color: "#b6acd8",
  },
  infoCode: {
    fontFamily: "SpaceMono-Regular",
    fontSize: 13,
    letterSpacing: 1.8,
    color: "#c8b9ff",
  },
  // Members row — prototype l.160
  membersRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 22,
    paddingTop: 12,
    gap: 10,
  },
  memberAvatar: {
    width: 30,
    height: 30,
    borderRadius: 15,
    borderWidth: 2,
    borderColor: "#140e34",
    alignItems: "center",
    justifyContent: "center",
  },
  memberAvatarText: {
    fontFamily: "Manrope-ExtraBold",
    fontSize: 10,
    color: colors.text.primary,
  },
  memberOverflow: {
    fontFamily: "Manrope-Bold",
    fontSize: 12,
    color: "#a99fce",
    marginLeft: 4,
  },
  // CTA row — prototype l.164–169
  ctaRow: {
    flexDirection: "row",
    gap: 10,
    paddingHorizontal: 22,
    paddingTop: 16,
  },
  inviteBtn: {
    flex: 1,
    height: 46,
    borderRadius: 13,
    backgroundColor: "rgba(255,255,255,0.07)",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.16)",
    alignItems: "center",
    justifyContent: "center",
  },
  scheduleBtn: {
    flex: 1,
    height: 46,
    borderRadius: 13,
    backgroundColor: "#a64bff",
    alignItems: "center",
    justifyContent: "center",
  },
  ctaText: {
    fontFamily: "Manrope-Bold",
    fontSize: 13,
    color: colors.text.primary,
  },
  // Right now — preserved
  snapshotRow: {
    paddingHorizontal: 22,
    paddingTop: 12,
    alignSelf: "flex-start",
  },
  snapshotText: {
    fontFamily: "Manrope-Medium",
    fontSize: 13,
    color: colors.text.secondary,
  },
  // Invite toast — prototype l.169
  inviteToast: {
    marginTop: 11,
    marginHorizontal: 22,
    textAlign: "center",
    fontFamily: "Manrope-SemiBold",
    fontSize: 12,
    color: "#28e0ff",
  },
});
