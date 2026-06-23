import { useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { useNavigation, useRoute } from "@react-navigation/native";
import type { NativeStackNavigationProp, NativeStackScreenProps } from "@react-navigation/native-stack";
import { useQueryClient } from "@tanstack/react-query";
import { BackChip } from "@/components/BackChip";
import { NeonGradientButton } from "@/components/NeonGradientButton";
import { useCreateGroup } from "@/hooks/useCreateGroup";
import { colors, radius, spacing } from "@/theme/tokens";
import type { HomeStackParamList } from "@/navigation/types";
import type { ApiError } from "@/api/client";

type Nav = NativeStackNavigationProp<HomeStackParamList, "CreateGroup">;
type RouteProps = NativeStackScreenProps<HomeStackParamList, "CreateGroup">["route"];

export function CreateGroup() {
  const navigation = useNavigation<Nav>();
  const route = useRoute<RouteProps>();
  const queryClient = useQueryClient();
  const { mutate, isPending, error } = useCreateGroup();

  const [name, setName] = useState("");
  const selectedEvent = route.params?.selectedEvent ?? null;

  const canSubmit = name.trim().length > 0 && selectedEvent !== null && !isPending;

  const handleSubmit = () => {
    if (!canSubmit || selectedEvent === null) return;
    mutate(
      { name: name.trim(), event_id: selectedEvent.event_id },
      {
        onSuccess: (res) => {
          void queryClient.invalidateQueries({ queryKey: ["my-groups"] });
          navigation.replace("GroupDetail", { invite_code: res.invite_code });
        },
        onError: (err) => {
          if (err.error_code === "event_not_found") {
            // Clear event selection so user can pick again
            navigation.setParams({ selectedEvent: undefined });
          }
        },
      }
    );
  };

  const apiError = error as ApiError | null;

  return (
    <KeyboardAvoidingView
      style={styles.screen}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <View style={styles.header}>
        <BackChip onPress={() => navigation.goBack()} />
        <Text style={styles.title}>New group</Text>
      </View>

      <View style={styles.form}>
        <Text style={styles.label}>Group name</Text>
        <TextInput
          style={styles.input}
          value={name}
          onChangeText={setName}
          placeholder="e.g. ravefam"
          placeholderTextColor={colors.text.placeholder}
          maxLength={80}
          autoCapitalize="none"
          testID="name-input"
        />

        <Text style={styles.label}>Event</Text>
        <TouchableOpacity
          style={styles.eventBtn}
          onPress={() => navigation.navigate("EventPicker")}
          testID="event-btn"
        >
          <Text style={selectedEvent ? styles.eventSelected : styles.eventPlaceholder}>
            {selectedEvent?.name ?? "Choose a festival"}
          </Text>
        </TouchableOpacity>

        {apiError != null && (
          <Text style={styles.error}>
            {apiError.error_code === "event_not_found"
              ? "That festival is no longer available."
              : apiError.message}
          </Text>
        )}
      </View>

      <NeonGradientButton
        label={isPending ? "Creating…" : "Create group"}
        onPress={handleSubmit}
        disabled={!canSubmit}
        testID="submit-btn"
      />
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.bg.canvas,
    paddingHorizontal: spacing.screenPad,
    paddingTop: spacing[9],
    paddingBottom: spacing[12],
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing[5],
    marginBottom: spacing[9],
  },
  title: {
    color: colors.text.primary,
    fontSize: 24,
    fontWeight: "700",
  },
  form: {
    flex: 1,
    gap: spacing[4],
  },
  label: {
    color: colors.text.secondary,
    fontSize: 12,
    fontWeight: "600",
    textTransform: "uppercase",
    letterSpacing: 0.8,
  },
  input: {
    height: 54,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border.input,
    backgroundColor: colors.bg.surfaceMed,
    paddingHorizontal: 16,
    color: colors.text.primary,
    fontSize: 15,
  },
  eventBtn: {
    height: 54,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border.input,
    backgroundColor: colors.bg.surfaceMed,
    paddingHorizontal: 16,
    justifyContent: "center",
  },
  eventSelected: {
    color: colors.text.primary,
    fontSize: 15,
  },
  eventPlaceholder: {
    color: colors.text.placeholder,
    fontSize: 15,
  },
  error: {
    color: colors.text.error,
    fontSize: 13,
  },
});
