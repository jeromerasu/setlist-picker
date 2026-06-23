import { ActivityIndicator, View } from "react-native";
import { useAuth } from "@/auth/AuthContext";
import { AuthStack } from "./AuthStack";
import { BottomTabs } from "./BottomTabs";
import { colors } from "@/theme/tokens";

export function RootNavigator() {
  const { isLoading, isAuthenticated } = useAuth();

  if (isLoading) {
    return (
      <View style={{ flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.bg.canvas }}>
        <ActivityIndicator color={colors.neon.purple} />
      </View>
    );
  }

  return isAuthenticated ? <BottomTabs /> : <AuthStack />;
}
