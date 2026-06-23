import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { GroupsList } from "@/screens/groups/GroupsList";
import { CreateGroup } from "@/screens/groups/CreateGroup";
import { EventPicker } from "@/screens/groups/EventPicker";
import type { HomeStackParamList } from "./types";

const Stack = createNativeStackNavigator<HomeStackParamList>();

export function HomeStack() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="GroupsList" component={GroupsList} />
      <Stack.Screen name="CreateGroup" component={CreateGroup} />
      <Stack.Screen name="EventPicker" component={EventPicker} />
      {/* Additional screens registered as tickets land */}
    </Stack.Navigator>
  );
}
