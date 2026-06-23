import React from "react";
import { View } from "react-native";

const ViewShot = React.forwardRef<any, any>(({ children, ...props }, ref) => {
  return React.createElement(View, { ref, ...props }, children);
});
ViewShot.displayName = "ViewShot";

export default ViewShot;
