import { StyleSheet, TextInput, View } from "react-native";
import { colors, radius, sizes } from "@/theme/tokens";

export interface SearchInputProps {
  value: string;
  onChangeText: (text: string) => void;
  placeholder?: string;
  testID?: string;
}

export function SearchInput({
  value,
  onChangeText,
  placeholder = "Search…",
  testID,
}: SearchInputProps) {
  return (
    <View style={styles.container}>
      <TextInput
        style={styles.input}
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={colors.text.placeholder}
        autoCorrect={false}
        autoCapitalize="none"
        testID={testID}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    height: sizes.search,
    borderRadius: radius.md,
    backgroundColor: colors.bg.surfaceMed,
    borderWidth: 1,
    borderColor: colors.border.mid,
    paddingHorizontal: 14,
    justifyContent: "center",
  },
  input: {
    color: colors.text.primary,
    fontSize: 15,
  },
});
