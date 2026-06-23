import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { Text } from "react-native";
import { HomeStack } from "./HomeStack";
import { SearchPlaceholder } from "@/screens/placeholder/SearchPlaceholder";
import { AccountProfile } from "@/screens/profile/AccountProfile";

const Tab = createBottomTabNavigator();

const ACTIVE_COLOR = "#a78bfa";
const INACTIVE_COLOR = "#6a6592";
const BG = "#0a0712";

function _icon(label: string, focused: boolean) {
  const symbols: Record<string, string> = {
    Home: "♦",
    Search: "◎",
    You: "◉",
  };
  return (
    <Text
      style={{
        fontSize: 18,
        color: focused ? ACTIVE_COLOR : INACTIVE_COLOR,
      }}
    >
      {symbols[label] ?? "●"}
    </Text>
  );
}

export function BottomTabs() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarIcon: ({ focused }) => _icon(route.name, focused),
        tabBarActiveTintColor: ACTIVE_COLOR,
        tabBarInactiveTintColor: INACTIVE_COLOR,
        tabBarStyle: { backgroundColor: BG, borderTopColor: "rgba(255,255,255,0.12)" },
        headerShown: false,
      })}
    >
      <Tab.Screen name="Home" component={HomeStack} />
      <Tab.Screen name="Search" component={SearchPlaceholder} />
      <Tab.Screen name="You" component={AccountProfile} />
    </Tab.Navigator>
  );
}
