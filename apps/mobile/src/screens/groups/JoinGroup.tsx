import { useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { ScreenContainer } from "@/components/ScreenContainer";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { BackChip } from "@/components/BackChip";
import { NeonGradientButton } from "@/components/NeonGradientButton";
import { normalizeCode } from "@/utils/inviteCode";
import { useJoinGroup } from "@/hooks/useJoinGroup";
import { colors, radius, spacing } from "@/theme/tokens";
import type { HomeStackParamList } from "@/navigation/types";
import type { ApiError } from "@/api/client";

type Nav = NativeStackNavigationProp<HomeStackParamList, "JoinGroup">;

export function JoinGroup() {
  const navigation = useNavigation<Nav>();
  const { mutate, isPending } = useJoinGroup();

  const [code, setCode] = useState("");
  const [joinError, setJoinError] = useState(false);

  const handleChange = (raw: string) => {
    setJoinError(false);
    setCode(normalizeCode(raw));
  };

  const canSubmit = code.length === 8 && !isPending;

  const handleSubmit = () => {
    if (!canSubmit) return;
    mutate(
      { invite_code: code },
      {
        onSuccess: (res) => {
          navigation.replace("GroupDetail", { invite_code: res.group.invite_code });
        },
        onError: (err) => {
          const apiErr = err as ApiError;
          if (apiErr.statusCode === 404) {
            setJoinError(true);
          }
        },
      }
    );
  };

  return (
    <ScreenContainer>
    <KeyboardAvoidingView
      style={styles.screen}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <View style={styles.header}>
        <BackChip onPress={() => navigation.goBack()} />
      </View>

      <View style={styles.body}>
        <View style={styles.iconCircle}>
          <Text style={styles.iconText}>🔑</Text>
        </View>
        <Text style={styles.title}>Join a group</Text>
        <Text style={styles.subtitle}>Enter the invite code</Text>

        <TextInput
          style={[styles.codeInput, joinError && styles.codeInputError]}
          value={code}
          onChangeText={handleChange}
          autoCapitalize="characters"
          autoCorrect={false}
          maxLength={8}
          placeholder="XXXXXXXX"
          placeholderTextColor={colors.text.placeholder}
          testID="code-input"
        />

        {joinError && (
          <Text style={styles.errorText}>
            This invite link is invalid or expired
          </Text>
        )}

        <Text style={styles.tip} testID="tip-text">Tip: try K7M2X9PQ</Text>
      </View>

      <NeonGradientButton
        label={isPending ? "Joining…" : "Join group"}
        onPress={handleSubmit}
        disabled={!canSubmit}
        testID="submit-btn"
      />
    </KeyboardAvoidingView>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.bg.canvas,
    paddingHorizontal: spacing.screenPad,
    paddingTop: spacing[9],
    paddingBottom: spacing[12],
  },
  header: {
    marginBottom: spacing[8],
  },
  body: {
    flex: 1,
    alignItems: "center",
    gap: spacing[5],
    paddingTop: spacing[9],
  },
  iconCircle: {
    width: 64,
    height: 64,
    borderRadius: 32,
    borderWidth: 2,
    borderColor: colors.neon.purple,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: spacing[3],
  },
  iconText: {
    fontSize: 28,
  },
  title: {
    fontFamily: "Manrope-ExtraBold",
    color: colors.text.primary,
    fontSize: 26,
    fontWeight: "800",
    letterSpacing: -0.26,
  },
  subtitle: {
    fontFamily: "Manrope-Medium",
    color: colors.text.secondary,
    fontSize: 15,
  },
  codeInput: {
    fontFamily: "SpaceMono-Bold",
    width: "100%",
    height: 54,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border.input,
    backgroundColor: colors.bg.surfaceMed,
    paddingHorizontal: 16,
    color: colors.text.primary,
    fontSize: 18,
    fontWeight: "700",
    letterSpacing: 0.18 * 18,
    textAlign: "center",
  },
  codeInputError: {
    borderColor: colors.text.error,
  },
  errorText: {
    fontFamily: "Manrope-Regular",
    color: colors.text.error,
    fontSize: 13,
    textAlign: "center",
  },
  tip: {
    fontFamily: "Manrope-Regular",
    color: colors.text.muted,
    fontSize: 12,
    marginTop: spacing[3],
  },
});
