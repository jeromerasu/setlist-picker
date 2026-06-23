import React from "react";
import { render } from "@testing-library/react-native";

jest.mock("expo-secure-store", () => ({
  getItemAsync: jest.fn().mockResolvedValue(null),
  setItemAsync: jest.fn().mockResolvedValue(undefined),
  deleteItemAsync: jest.fn().mockResolvedValue(undefined),
}));

jest.mock("expo-status-bar", () => ({
  StatusBar: () => null,
}));

jest.mock("@react-navigation/native", () => ({
  NavigationContainer: ({ children }: { children: unknown }) => {
    const R = require("react");
    return R.createElement(R.Fragment, null, children);
  },
  useNavigation: () => ({ navigate: jest.fn(), goBack: jest.fn() }),
}));

jest.mock("@react-navigation/bottom-tabs", () => ({
  createBottomTabNavigator: () => ({
    Navigator: ({ children }: { children: unknown }) => {
      const R = require("react");
      return R.createElement(R.Fragment, null, children);
    },
    Screen: ({ name }: { name: string }) => {
      const R = require("react");
      const RN = require("react-native");
      return R.createElement(RN.Text, { testID: `tab-${name}` }, name);
    },
  }),
}));

jest.mock("@react-navigation/native-stack", () => ({
  createNativeStackNavigator: () => ({
    Navigator: ({ children }: { children: unknown }) => {
      const R = require("react");
      return R.createElement(R.Fragment, null, children);
    },
    Screen: () => null,
  }),
}));

// Force authenticated state so RootNavigator renders BottomTabs, not AuthStack
jest.mock("@/auth/AuthContext", () => ({
  AuthProvider: ({ children }: { children: unknown }) => {
    const R = require("react");
    return R.createElement(R.Fragment, null, children);
  },
  useAuth: () => ({ isLoading: false, isAuthenticated: true, signIn: jest.fn(), signOut: jest.fn() }),
}));

import App from "../App";

describe("App", () => {
  it("app_renders_without_throwing", () => {
    expect(() => render(<App />)).not.toThrow();
  });

  it("bottom_tabs_show_three_labels", () => {
    const { getAllByText } = render(<App />);
    expect(getAllByText("Home").length).toBeGreaterThan(0);
    expect(getAllByText("Search").length).toBeGreaterThan(0);
    expect(getAllByText("You").length).toBeGreaterThan(0);
  });
});
