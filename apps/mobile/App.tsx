import { NavigationContainer } from "@react-navigation/native";
import { QueryClientProvider } from "@tanstack/react-query";
import { StatusBar } from "expo-status-bar";
import { queryClient } from "@/api/queryClient";
import { AuthProvider } from "@/auth/AuthContext";
import { RootNavigator } from "@/navigation/RootNavigator";

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <NavigationContainer>
          <StatusBar style="light" />
          <RootNavigator />
        </NavigationContainer>
      </AuthProvider>
    </QueryClientProvider>
  );
}
