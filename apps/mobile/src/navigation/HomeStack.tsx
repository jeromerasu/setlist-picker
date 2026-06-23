import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { GroupsList } from "@/screens/groups/GroupsList";
import { CreateGroup } from "@/screens/groups/CreateGroup";
import { EventPicker } from "@/screens/groups/EventPicker";
import { JoinGroup } from "@/screens/groups/JoinGroup";
import { GroupDetail } from "@/screens/groups/GroupDetail";
import { Schedule } from "@/screens/schedule/Schedule";
import { ArtistDetail } from "@/screens/artist/ArtistDetail";
import type { HomeStackParamList } from "./types";

const Stack = createNativeStackNavigator<HomeStackParamList>();

export function HomeStack() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="GroupsList" component={GroupsList} />
      <Stack.Screen name="CreateGroup" component={CreateGroup} />
      <Stack.Screen name="EventPicker" component={EventPicker} />
      <Stack.Screen name="JoinGroup" component={JoinGroup} />
      <Stack.Screen name="GroupDetail" component={GroupDetail} />
      <Stack.Screen name="Schedule" component={Schedule} />
      <Stack.Screen name="ArtistDetail" component={ArtistDetail} />
      {/* Additional screens registered as tickets land */}
    </Stack.Navigator>
  );
}
