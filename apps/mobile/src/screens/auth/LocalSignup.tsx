import { useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { NeonGradientButton } from "@/components/NeonGradientButton";
import { BackChip } from "@/components/BackChip";
import { useLocalAuth } from "@/auth/useLocalAuth";
import { useAuth } from "@/auth/AuthContext";
import { colors, radius, spacing } from "@/theme/tokens";
import type { AuthStackParamList } from "@/navigation/AuthStack";

type Nav = NativeStackNavigationProp<AuthStackParamList, "LocalSignup">;

export function LocalSignup() {
  const navigation = useNavigation<Nav>();
  const { signIn } = useAuth();
  const { isLoading, error, signup } = useLocalAuth();

  const [display_name, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const isValidEmail = /^[^@]+@[^@]+\.[^@]+$/.test(email.trim());
  const canSubmit =
    display_name.trim().length > 0 && isValidEmail && password.length >= 8;

  const handleSignup = async () => {
    if (!canSubmit) return;
    const pair = await signup(email.trim().toLowerCase(), password, display_name.trim());
    if (pair) await signIn(pair);
  };

  return (
    <SafeAreaView edges={["top", "bottom"]} style={styles.safeArea}>
    <KeyboardAvoidingView
      style={styles.screen}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <View style={styles.header}>
        <BackChip onPress={() => navigation.goBack()} />
        <Text style={styles.title}>Create account</Text>
      </View>

      <View style={styles.form}>
        <TextInput
          style={styles.input}
          placeholder="Display name"
          placeholderTextColor={colors.text.placeholder}
          value={display_name}
          onChangeText={setDisplayName}
          testID="display-name-input"
        />
        <TextInput
          style={styles.input}
          placeholder="Email"
          placeholderTextColor={colors.text.placeholder}
          value={email}
          onChangeText={setEmail}
          autoCapitalize="none"
          autoCorrect={false}
          keyboardType="email-address"
          textContentType="emailAddress"
          autoComplete="email"
          testID="email-input"
        />
        <TextInput
          style={styles.input}
          placeholder="Password (min 8 chars)"
          placeholderTextColor={colors.text.placeholder}
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          testID="password-input"
        />

        {error != null && <Text style={styles.error}>{error}</Text>}

        <NeonGradientButton
          label={isLoading ? "Creating…" : "Create account"}
          onPress={handleSignup}
          disabled={!canSubmit || isLoading}
          testID="submit-btn"
        />
      </View>
    </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: colors.bg.canvas,
  },
  screen: {
    flex: 1,
    paddingHorizontal: spacing.screenPad,
    paddingTop: spacing[9],
    paddingBottom: spacing[12],
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing[5],
    marginBottom: spacing[9],
  },
  title: {
    color: colors.text.primary,
    fontSize: 24,
    fontWeight: "700",
  },
  form: {
    gap: spacing[4],
    flex: 1,
  },
  input: {
    height: 54,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border.input,
    backgroundColor: colors.bg.surfaceMed,
    paddingHorizontal: 16,
    color: colors.text.primary,
    fontSize: 15,
  },
  error: {
    color: colors.text.error,
    fontSize: 13,
  },
});
