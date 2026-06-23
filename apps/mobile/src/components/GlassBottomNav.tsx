import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { colors, radius } from "@/theme/tokens";

export interface NavItem {
  label: string;
  icon: React.ReactNode;
  onPress: () => void;
  isActive: boolean;
}

export interface GlassBottomNavProps {
  items: NavItem[];
}

export function GlassBottomNav({ items }: GlassBottomNavProps) {
  return (
    <View style={styles.container}>
      {items.map((item, i) => (
        <TouchableOpacity key={i} style={styles.item} onPress={item.onPress}>
          <View style={{ opacity: item.isActive ? 1 : 0.5 }}>{item.icon}</View>
          <Text
            style={[
              styles.label,
              { color: item.isActive ? colors.neon.purple : colors.text.tertiary },
            ]}
          >
            {item.label}
          </Text>
        </TouchableOpacity>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    backgroundColor: colors.bg.glassNav,
    borderRadius: radius["4xl"],
    borderWidth: 1,
    borderColor: colors.border.mid,
    paddingVertical: 12,
    paddingHorizontal: 8,
  },
  item: {
    flex: 1,
    alignItems: "center",
    gap: 4,
  },
  label: {
    fontSize: 12,
    fontWeight: "600",
  },
});
