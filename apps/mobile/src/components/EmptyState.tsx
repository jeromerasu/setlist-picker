import React from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { colors, spacing } from "@/theme/tokens";

export interface EmptyStateProps {
  icon: React.ReactNode;
  title: string;
  body: string;
  cta?: { label: string; onPress: () => void };
}

export function EmptyState({ icon, title, body, cta }: EmptyStateProps) {
  return (
    <View style={styles.container}>
      <View style={styles.iconWrap}>{icon}</View>
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.body}>{body}</Text>
      {cta != null && (
        <TouchableOpacity style={styles.ctaBtn} onPress={cta.onPress}>
          <Text style={styles.ctaText}>{cta.label}</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: spacing.screenPad,
    gap: spacing[4],
  },
  iconWrap: {
    marginBottom: spacing[3],
  },
  title: {
    color: colors.text.primary,
    fontSize: 22,
    fontWeight: "700",
    textAlign: "center",
  },
  body: {
    color: colors.text.secondary,
    fontSize: 15,
    textAlign: "center",
  },
  ctaBtn: {
    marginTop: spacing[4],
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 15,
    borderWidth: 1,
    borderColor: colors.border.default,
  },
  ctaText: {
    color: colors.text.primary,
    fontSize: 14,
    fontWeight: "600",
  },
});
