import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { GroupsList } from "@/screens/groups/GroupsList";
import type { HomeStackParamList } from "./types";

// Lazy imports to avoid circular dependency during test mocking
const Stack = createNativeStackNavigator<HomeStackParamList>();

export function HomeStack() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="GroupsList" component={GroupsList} />
      {/* Additional screens registered here as tickets land */}
    </Stack.Navigator>
  );
}
