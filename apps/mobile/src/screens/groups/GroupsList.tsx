import {
  ActivityIndicator,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useQueryClient } from "@tanstack/react-query";
import { GlassCard } from "@/components/GlassCard";
import { NeonGradientButton } from "@/components/NeonGradientButton";
import { OutlineButton } from "@/components/OutlineButton";
import { EmptyState } from "@/components/EmptyState";
import { GroupCard } from "./GroupCard";
import { useMyGroups } from "@/hooks/useMyGroups";
import { getHue } from "@/theme/heroes";
import { colors, spacing } from "@/theme/tokens";
import type { HomeStackParamList } from "@/navigation/types";

type Nav = NativeStackNavigationProp<HomeStackParamList, "GroupsList">;

export function GroupsList() {
  const navigation = useNavigation<Nav>();
  const queryClient = useQueryClient();
  const { data, isLoading, isError, refetch, isFetching } = useMyGroups();

  const groups = data?.groups ?? [];

  const handleRefresh = () => {
    void queryClient.invalidateQueries({ queryKey: ["my-groups"] });
  };

  if (isLoading) {
    return (
      <View style={styles.loadingScreen}>
        <ActivityIndicator color={colors.neon.purple} />
      </View>
    );
  }

  if (isError) {
    return (
      <View style={styles.screen}>
        <EmptyState
          icon={<Text style={styles.icon}>⚠️</Text>}
          title="Couldn't load groups"
          body="Check your connection and try again."
          cta={{ label: "Retry", onPress: () => void refetch() }}
        />
      </View>
    );
  }

  const CTAs = (
    <View style={styles.ctas}>
      <NeonGradientButton
        label="+ CREATE A GROUP"
        onPress={() => navigation.navigate("CreateGroup", {})}
        testID="create-cta"
      />
      <OutlineButton
        label="Join a group"
        onPress={() => navigation.navigate("JoinGroup")}
        testID="join-cta"
      />
    </View>
  );

  if (groups.length === 0) {
    return (
      <View style={styles.screen}>
        <Text style={styles.wordmark}>GROUPS</Text>
        <Text style={styles.subtitle}>Pick sets together. See who's where.</Text>
        <EmptyState
          icon={<Text style={styles.icon}>🌌</Text>}
          title="No groups yet"
          body="Create a group to start planning, or join one with an invite code."
        />
        {CTAs}
      </View>
    );
  }

  return (
    <View style={styles.screen}>
      <Text style={styles.wordmark}>GROUPS</Text>
      <Text style={styles.subtitle}>Pick sets together. See who's where.</Text>
      <ScrollView
        style={styles.list}
        contentContainerStyle={styles.listContent}
        refreshControl={
          <RefreshControl
            refreshing={isFetching && !isLoading}
            onRefresh={handleRefresh}
            tintColor={colors.neon.purple}
          />
        }
      >
        {groups.map((group, i) => (
          <GroupCard
            key={group.group_id}
            group={group}
            hue={getHue(i)}
            onPress={() => navigation.navigate("GroupDetail", { invite_code: group.invite_code })}
            testID={`group-card-${i}`}
          />
        ))}
      </ScrollView>
      {CTAs}
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.bg.canvas,
    paddingHorizontal: spacing.screenPad,
    paddingTop: spacing[9],
  },
  loadingScreen: {
    flex: 1,
    backgroundColor: colors.bg.canvas,
    alignItems: "center",
    justifyContent: "center",
  },
  wordmark: {
    color: colors.neon.purple,
    fontSize: 28,
    fontWeight: "800",
    letterSpacing: 1,
    marginBottom: 4,
  },
  subtitle: {
    color: colors.text.secondary,
    fontSize: 14,
    marginBottom: spacing[7],
  },
  list: {
    flex: 1,
  },
  listContent: {
    paddingBottom: spacing[8],
  },
  ctas: {
    position: "absolute",
    bottom: 90,
    left: spacing.screenPad,
    right: spacing.screenPad,
    gap: spacing[3],
  },
  icon: {
    fontSize: 40,
  },
});
