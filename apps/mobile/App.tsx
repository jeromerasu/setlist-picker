import { NavigationContainer } from "@react-navigation/native";
import { QueryClientProvider } from "@tanstack/react-query";
import { StatusBar } from "expo-status-bar";
import { queryClient } from "@/api/queryClient";
import { BottomTabs } from "@/navigation/BottomTabs";

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <NavigationContainer>
        <StatusBar style="light" />
        <BottomTabs />
      </NavigationContainer>
    </QueryClientProvider>
  );
}
