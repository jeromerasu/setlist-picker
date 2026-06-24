import { useState } from "react";
import {
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { ScreenContainer } from "@/components/ScreenContainer";
import { useQueryClient } from "@tanstack/react-query";
import { Avatar } from "@/components/Avatar";
import { NeonGradientButton } from "@/components/NeonGradientButton";
import { AvatarColorPicker } from "./AvatarColorPicker";
import { LeaveGroupModal } from "./LeaveGroupModal";
import { useUpdateProfile } from "@/hooks/useUpdateProfile";
import { useLeaveGroup } from "@/hooks/useLeaveGroup";
import { useMyGroups } from "@/hooks/useMyGroups";
import { useAuth } from "@/auth/AuthContext";
import { colors, radius, spacing } from "@/theme/tokens";

const DEFAULT_COLOR = "#a64bff";

export function AccountProfile() {
  const { signOut } = useAuth();
  const queryClient = useQueryClient();
  const { data: groupsData } = useMyGroups();
  const groups = groupsData?.groups ?? [];

  const [displayName, setDisplayName] = useState("");
  const [avatarColor, setAvatarColor] = useState(DEFAULT_COLOR);
  const [leaveTarget, setLeaveTarget] = useState<{ invite_code: string; name: string } | null>(null);

  const { mutate: updateProfile, isPending: saving } = useUpdateProfile();
  const { mutate: leaveGroup, isPending: leaving } = useLeaveGroup();

  const canSave = displayName.trim().length >= 1 && !saving;

  const handleSave = () => {
    if (!canSave) return;
    updateProfile(
      { display_name: displayName.trim(), avatar_color: avatarColor },
      {
        onSuccess: () => {
          void queryClient.invalidateQueries({ queryKey: ["me"] });
          Alert.alert("Profile updated");
        },
        onError: (err) => {
          Alert.alert("Error", err.message ?? "Could not save profile");
        },
      },
    );
  };

  const handleConfirmLeave = () => {
    if (leaveTarget == null) return;
    leaveGroup(leaveTarget.invite_code, {
      onSuccess: () => {
        setLeaveTarget(null);
        void queryClient.invalidateQueries({ queryKey: ["my-groups"] });
      },
    });
  };

  const initials = displayName.trim().slice(0, 2).toUpperCase() || "ME";

  return (
    <ScreenContainer style={styles.screen}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.sectionTitle}>Your profile</Text>

        <View style={styles.avatarRow}>
          <Avatar initials={initials} color={avatarColor} size={40} />
          <TextInput
            style={styles.nameInput}
            value={displayName}
            onChangeText={setDisplayName}
            placeholder="Display name"
            placeholderTextColor={colors.text.placeholder}
            maxLength={40}
            testID="display-name-input"
          />
        </View>

        <AvatarColorPicker selected={avatarColor} onSelect={setAvatarColor} />

        <NeonGradientButton
          label={saving ? "Saving…" : "Save profile"}
          onPress={handleSave}
          disabled={!canSave}
          testID="save-btn"
        />

        {groups.length > 0 && (
          <View style={styles.groupsSection}>
            <Text style={styles.sectionTitle}>Your groups</Text>
            {groups.map((g) => (
              <View key={g.group_id} style={styles.groupRow}>
                <Text style={styles.groupName} numberOfLines={1}>
                  {g.name}
                </Text>
                <TouchableOpacity
                  style={styles.leaveBtn}
                  onPress={() => setLeaveTarget({ invite_code: g.invite_code, name: g.name })}
                  testID={`leave-btn-${g.group_id}`}
                >
                  <Text style={styles.leaveBtnLabel}>Leave</Text>
                </TouchableOpacity>
              </View>
            ))}
          </View>
        )}

        <TouchableOpacity style={styles.signOutBtn} onPress={() => void signOut()} testID="sign-out-btn">
          <Text style={styles.signOutLabel}>Sign out</Text>
        </TouchableOpacity>
      </ScrollView>

      {leaveTarget != null && (
        <LeaveGroupModal
          groupName={leaveTarget.name}
          visible
          onConfirm={handleConfirmLeave}
          onCancel={() => setLeaveTarget(null)}
        />
      )}
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.bg.canvas,
  },
  content: {
    paddingHorizontal: spacing.screenPad,
    paddingTop: spacing[9],
    paddingBottom: spacing[13],
    gap: spacing[7],
  },
  sectionTitle: {
    color: colors.text.secondary,
    fontSize: 13,
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: 1.5,
  },
  avatarRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing[5],
  },
  nameInput: {
    flex: 1,
    height: 46,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border.input,
    backgroundColor: colors.bg.surfaceMed,
    paddingHorizontal: 14,
    color: colors.text.primary,
    fontSize: 15,
  },
  groupsSection: {
    gap: spacing[4],
  },
  groupRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: colors.border.weak,
  },
  groupName: {
    flex: 1,
    color: colors.text.primary,
    fontSize: 14,
  },
  leaveBtn: {
    paddingHorizontal: 12,
    paddingVertical: 5,
    borderRadius: radius.sm,
    borderWidth: 1,
    borderColor: colors.text.error,
  },
  leaveBtnLabel: {
    color: colors.text.error,
    fontSize: 13,
    fontWeight: "600",
  },
  signOutBtn: {
    alignSelf: "center",
    paddingVertical: 10,
    paddingHorizontal: 24,
  },
  signOutLabel: {
    color: colors.text.tertiary,
    fontSize: 14,
  },
});
