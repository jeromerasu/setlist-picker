import React from "react";
import { View } from "react-native";
import type { ViewStyle } from "react-native";

interface Props {
  children?: React.ReactNode;
  style?: ViewStyle;
  testID?: string;
  colors?: readonly string[];
  start?: { x: number; y: number };
  end?: { x: number; y: number };
}

export const LinearGradient = ({ children, style, testID }: Props): React.ReactElement =>
  React.createElement(View, { style, testID }, children);
