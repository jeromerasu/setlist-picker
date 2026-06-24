module.exports = function (api) {
  const isTest = api.env("test");

  const presets = [
    isTest
      ? "babel-preset-expo"
      : ["babel-preset-expo", { jsxImportSource: "nativewind" }],
  ];

  // react-native-css-interop/babel unconditionally loads react-native-worklets/plugin
  // which requires RN 0.83+ (incompatible with SDK 54's RN 0.81). Load the CSS
  // plugin directly and skip the worklets plugin entirely.
  const plugins = isTest
    ? []
    : [require("react-native-css-interop/dist/babel-plugin").default];

  return { presets, plugins };
};
