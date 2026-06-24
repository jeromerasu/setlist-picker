import { StyleSheet, Text } from "react-native";
import { ScreenContainer } from "@/components/ScreenContainer";

export function SearchPlaceholder() {
  return (
    <ScreenContainer style={styles.container}>
      <Text style={styles.body}>Search coming soon</Text>
    </ScreenContainer>
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
