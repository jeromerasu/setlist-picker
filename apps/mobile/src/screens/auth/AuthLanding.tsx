import { StyleSheet, Text, View } from "react-native";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { NeonGradientButton } from "@/components/NeonGradientButton";
import { OutlineButton } from "@/components/OutlineButton";
import { useAppleSignIn } from "@/auth/useAppleSignIn";
import { useGoogleSignIn } from "@/auth/useGoogleSignIn";
import { useAuth } from "@/auth/AuthContext";
import { colors, spacing } from "@/theme/tokens";
import type { AuthStackParamList } from "@/navigation/AuthStack";

type Nav = NativeStackNavigationProp<AuthStackParamList, "AuthLanding">;

export function AuthLanding() {
  const navigation = useNavigation<Nav>();
  const { signIn } = useAuth();
  const apple = useAppleSignIn();
  const google = useGoogleSignIn();

  const handleApple = async () => {
    const pair = await apple.signInWithApple();
    if (pair) await signIn(pair);
  };

  const handleGoogle = async () => {
    const pair = await google.signInWithGoogle();
    if (pair) await signIn(pair);
  };

  const error = apple.error ?? google.error;

  return (
    <View style={styles.screen}>
      <View style={styles.top}>
        <Text style={styles.wordmark}>setlist</Text>
        <Text style={styles.sub}>Pick sets. Vote with your crew.</Text>
      </View>

      {error != null && <Text style={styles.error}>{error}</Text>}

      <View style={styles.actions}>
        <NeonGradientButton
          label="Continue with Apple"
          onPress={handleApple}
          disabled={apple.isLoading || google.isLoading}
          testID="apple-btn"
        />
        <OutlineButton
          label="Continue with Google"
          onPress={handleGoogle}
          testID="google-btn"
        />
        <OutlineButton
          label="Sign in with email"
          onPress={() => navigation.navigate("LocalLogin")}
          testID="email-btn"
        />
        <Text
          style={styles.signupLink}
          onPress={() => navigation.navigate("LocalSignup")}
          testID="signup-link"
        >
          New here? Create an account
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.bg.canvas,
    paddingHorizontal: spacing.screenPad,
    justifyContent: "space-between",
    paddingTop: spacing[13],
    paddingBottom: spacing[12],
  },
  top: {
    gap: spacing[4],
  },
  wordmark: {
    color: colors.neon.purple,
    fontSize: 42,
    fontWeight: "800",
    letterSpacing: -0.5,
  },
  sub: {
    color: colors.text.secondary,
    fontSize: 16,
  },
  error: {
    color: colors.text.error,
    fontSize: 14,
    textAlign: "center",
  },
  actions: {
    gap: spacing[4],
  },
  signupLink: {
    color: colors.text.tertiary,
    fontSize: 14,
    textAlign: "center",
    marginTop: spacing[3],
  },
});
