import { useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
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

type Nav = NativeStackNavigationProp<AuthStackParamList, "LocalLogin">;

export function LocalLogin() {
  const navigation = useNavigation<Nav>();
  const { signIn } = useAuth();
  const { isLoading, error, login } = useLocalAuth();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const canSubmit = username.trim().length > 0 && password.length >= 6;

  const handleLogin = async () => {
    if (!canSubmit) return;
    const pair = await login(username.trim(), password);
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
        <Text style={styles.title}>Sign in</Text>
      </View>

      <View style={styles.form}>
        <TextInput
          style={styles.input}
          placeholder="Username"
          placeholderTextColor={colors.text.placeholder}
          value={username}
          onChangeText={setUsername}
          autoCapitalize="none"
          autoCorrect={false}
          testID="username-input"
        />
        <TextInput
          style={styles.input}
          placeholder="Password"
          placeholderTextColor={colors.text.placeholder}
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          testID="password-input"
        />

        {error != null && <Text style={styles.error}>{error}</Text>}

        <NeonGradientButton
          label={isLoading ? "Signing in…" : "Sign in"}
          onPress={handleLogin}
          disabled={!canSubmit || isLoading}
          testID="submit-btn"
        />
      </View>

      <TouchableOpacity onPress={() => navigation.navigate("LocalSignup")} testID="signup-link">
        <Text style={styles.footer}>Don't have an account? Sign up</Text>
      </TouchableOpacity>
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
  footer: {
    color: colors.text.tertiary,
    fontSize: 14,
    textAlign: "center",
  },
});
