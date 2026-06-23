import { StyleSheet, Text, View } from "react-native";

export function SearchPlaceholder() {
  return (
    <View style={styles.container}>
      <Text style={styles.body}>Search coming soon</Text>
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
  body: { color: "#a99fce", fontSize: 15 },
});
