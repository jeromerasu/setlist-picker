module.exports = function (api) {
  const isTest = api.env("test");

  const presets = [
    isTest
      ? "babel-preset-expo"
      : ["babel-preset-expo", { jsxImportSource: "nativewind" }],
  ];
  if (!isTest) {
    presets.push("nativewind/babel");
  }

  return { presets };
};
