import { Modal, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { colors, radius, spacing } from "@/theme/tokens";

interface Props {
  groupName: string;
  visible: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function LeaveGroupModal({ groupName, visible, onConfirm, onCancel }: Props) {
  return (
    <Modal transparent visible={visible} animationType="fade" onRequestClose={onCancel}>
      <View style={styles.overlay}>
        <View style={styles.sheet}>
          <Text style={styles.title}>Leave group?</Text>
          <Text style={styles.body}>
            You will be removed from "{groupName}" and all your picks will be deleted.
          </Text>
          <View style={styles.actions}>
            <TouchableOpacity style={styles.cancelBtn} onPress={onCancel} testID="cancel-leave-btn">
              <Text style={styles.cancelLabel}>Cancel</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.confirmBtn} onPress={onConfirm} testID="confirm-leave-btn">
              <Text style={styles.confirmLabel}>Leave</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.6)",
    alignItems: "center",
    justifyContent: "flex-end",
  },
  sheet: {
    width: "100%",
    backgroundColor: colors.bg.elevated,
    borderTopLeftRadius: radius["2xl"],
    borderTopRightRadius: radius["2xl"],
    padding: spacing.screenPad,
    paddingBottom: spacing[13],
    gap: spacing[6],
  },
  title: {
    color: colors.text.primary,
    fontSize: 20,
    fontWeight: "700",
  },
  body: {
    color: colors.text.secondary,
    fontSize: 14,
    lineHeight: 22,
  },
  actions: {
    flexDirection: "row",
    gap: spacing[4],
  },
  cancelBtn: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: radius.xl,
    borderWidth: 1,
    borderColor: colors.border.default,
    alignItems: "center",
  },
  cancelLabel: {
    color: colors.text.primary,
    fontSize: 15,
    fontWeight: "600",
  },
  confirmBtn: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: radius.xl,
    backgroundColor: colors.text.error,
    alignItems: "center",
  },
  confirmLabel: {
    color: "#ffffff",
    fontSize: 15,
    fontWeight: "700",
  },
});
