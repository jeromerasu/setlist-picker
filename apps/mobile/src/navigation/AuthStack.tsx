import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { AuthLanding } from "@/screens/auth/AuthLanding";
import { LocalLogin } from "@/screens/auth/LocalLogin";
import { LocalSignup } from "@/screens/auth/LocalSignup";

export type AuthStackParamList = {
  AuthLanding: undefined;
  LocalLogin: undefined;
  LocalSignup: undefined;
};

const Stack = createNativeStackNavigator<AuthStackParamList>();

export function AuthStack() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="AuthLanding" component={AuthLanding} />
      <Stack.Screen name="LocalLogin" component={LocalLogin} />
      <Stack.Screen name="LocalSignup" component={LocalSignup} />
    </Stack.Navigator>
  );
}
