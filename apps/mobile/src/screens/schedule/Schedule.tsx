import { useState } from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";
import { useRoute, useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp, NativeStackScreenProps } from "@react-navigation/native-stack";
import { BackChip } from "@/components/BackChip";
import { DayMenu } from "./DayMenu";
import { AllStagesGrid } from "./AllStagesGrid";
import { useScheduleData } from "@/hooks/useScheduleData";
import { useGroupState } from "@/hooks/useGroupState";
import { pickedSetIds } from "@/utils/dayBuckets";
import { uniqueDays, setsForDay } from "@/utils/dayList";
import { colors, spacing } from "@/theme/tokens";
import type { HomeStackParamList } from "@/navigation/types";
import type { SetDetail } from "@/types/api";

type Props = NativeStackScreenProps<HomeStackParamList, "Schedule">;
type Nav = NativeStackNavigationProp<HomeStackParamList, "Schedule">;

export function Schedule() {
  const route = useRoute<Props["route"]>();
  const navigation = useNavigation<Nav>();
  const { invite_code } = route.params;

  const { sets, eventName, isLoading } = useScheduleData(invite_code);
  const { data: group } = useGroupState(invite_code);

  const days = uniqueDays(sets);
  const [selectedDay, setSelectedDay] = useState<string>("");

  const activeDay = selectedDay !== "" ? selectedDay : (days[0] ?? "");
  const daySets = setsForDay(sets, activeDay);
  const myPicked = pickedSetIds(group?.picks ?? []);

  const handleSelectSet = (set: SetDetail) => {
    const artistName = set.artists[0]?.name ?? set.display_name;
    navigation.navigate("ArtistDetail", { artist_name: artistName });
  };

  if (isLoading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={colors.neon.violet} />
      </View>
    );
  }

  return (
    <View style={styles.screen}>
      <View style={styles.header}>
        <BackChip onPress={() => navigation.goBack()} />
        <Text style={styles.eventName} numberOfLines={1}>
          {eventName}
        </Text>
      </View>

      <DayMenu days={days} selected={activeDay} onSelect={setSelectedDay} />

      <View style={styles.grid}>
        <AllStagesGrid
          sets={daySets}
          pickedIds={myPicked}
          onSelectSet={handleSelectSet}
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.bg.canvas,
    paddingTop: spacing[9],
    gap: spacing[5],
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing[5],
    paddingHorizontal: spacing.screenPad,
  },
  eventName: {
    color: colors.text.primary,
    fontSize: 20,
    fontWeight: "700",
    flex: 1,
  },
  grid: {
    flex: 1,
    overflow: "hidden",
  },
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.bg.canvas,
  },
});
