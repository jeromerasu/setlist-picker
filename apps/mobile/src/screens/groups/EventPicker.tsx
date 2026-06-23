import { useState } from "react";
import {
  FlatList,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { BackChip } from "@/components/BackChip";
import { SearchInput } from "@/components/SearchInput";
import { EmptyState } from "@/components/EmptyState";
import { useEvents } from "@/hooks/useEvents";
import { deriveMono, deriveTileGradient } from "@/utils/eventTile";
import { colors, radius, spacing } from "@/theme/tokens";
import type { HomeStackParamList } from "@/navigation/types";
import type { EventListItem } from "@/types/api";

type Nav = NativeStackNavigationProp<HomeStackParamList, "EventPicker">;

const TILE_SIZE = 46;

export function EventPicker() {
  const navigation = useNavigation<Nav>();
  const [query, setQuery] = useState("");
  const { data, isLoading } = useEvents(query);

  const events = data?.events ?? [];

  const handleSelect = (event: EventListItem) => {
    navigation.navigate("CreateGroup", {
      selectedEvent: { event_id: event.event_id, name: event.name },
    });
  };

  const renderItem = ({ item: event }: { item: EventListItem }) => {
    const mono = deriveMono(event.name);
    void deriveTileGradient(event.name);

    return (
      <TouchableOpacity
        style={styles.row}
        onPress={() => handleSelect(event)}
        testID={`event-row-${event.event_id}`}
      >
        <View style={styles.tile}>
          <Text style={styles.tileText}>{mono}</Text>
        </View>
        <View style={styles.rowInfo}>
          <Text style={styles.eventName} numberOfLines={1}>
            {event.name}
          </Text>
          <Text style={styles.eventMeta} numberOfLines={1}>
            {event.start_date}
            {event.location != null ? ` · ${event.location}` : ""}
          </Text>
        </View>
      </TouchableOpacity>
    );
  };

  return (
    <View style={styles.screen}>
      <View style={styles.header}>
        <BackChip onPress={() => navigation.goBack()} />
        <Text style={styles.title}>Choose event</Text>
      </View>

      <SearchInput
        value={query}
        onChangeText={setQuery}
        placeholder="Search festivals…"
        testID="search-input"
      />

      {!isLoading && events.length === 0 && query.length > 0 ? (
        <EmptyState
          icon={<Text style={styles.icon}>🔍</Text>}
          title={`No festivals match "${query}"`}
          body="Try a different search."
        />
      ) : (
        <FlatList
          data={events}
          keyExtractor={(e) => e.event_id}
          renderItem={renderItem}
          style={styles.list}
          contentContainerStyle={styles.listContent}
          ItemSeparatorComponent={() => <View style={styles.separator} />}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.bg.canvas,
    paddingHorizontal: spacing.screenPad,
    paddingTop: spacing[9],
    gap: spacing[5],
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing[5],
  },
  title: {
    color: colors.text.primary,
    fontSize: 24,
    fontWeight: "700",
  },
  list: {
    flex: 1,
  },
  listContent: {
    paddingBottom: spacing[12],
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing[4],
    paddingVertical: 9,
  },
  separator: {
    height: 1,
    backgroundColor: colors.border.weak,
  },
  tile: {
    width: TILE_SIZE,
    height: TILE_SIZE,
    borderRadius: radius.sm,
    backgroundColor: colors.neon.violetSat,
    alignItems: "center",
    justifyContent: "center",
  },
  tileText: {
    color: colors.text.primary,
    fontSize: 14,
    fontWeight: "700",
  },
  rowInfo: {
    flex: 1,
    gap: 2,
  },
  eventName: {
    color: colors.text.primary,
    fontSize: 15,
    fontWeight: "700",
  },
  eventMeta: {
    color: colors.text.secondary,
    fontSize: 13,
  },
  icon: {
    fontSize: 36,
  },
});
