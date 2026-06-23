import { StyleSheet, Text, View } from "react-native";

export function HomePlaceholder() {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>GROUPS</Text>
      <Text style={styles.body}>Coming soon</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0a0712",
    alignItems: "center",
    justifyContent: "center",
  },
  title: {
    color: "#ffffff",
    fontSize: 30,
    fontWeight: "900",
    letterSpacing: 0.03 * 30,
  },
  body: {
    color: "#a99fce",
    fontSize: 15,
    marginTop: 8,
  },
});
