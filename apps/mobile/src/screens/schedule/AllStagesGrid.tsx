import { ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { Timeline } from "./Timeline";
import { groupByStage, setTop, setHeight, HOUR_HEIGHT_PX } from "@/utils/gridLayout";
import { colors, radius, spacing } from "@/theme/tokens";
import type { SetDetail } from "@/types/api";

interface Props {
  sets: SetDetail[];
  pickedIds: Set<string>;
  onSelectSet: (set: SetDetail) => void;
}

const HOURS_SHOWN = 14;
const COLUMN_WIDTH = 110;

export function AllStagesGrid({ sets, pickedIds, onSelectSet }: Props) {
  const stageMap = groupByStage(sets);
  const stages = Array.from(stageMap.entries());

  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false}>
      <ScrollView showsVerticalScrollIndicator={false}>
        <View style={[styles.container, { height: HOURS_SHOWN * HOUR_HEIGHT_PX }]}>
          <Timeline />
          <View style={styles.columns}>
            {stages.map(([stageName, stageSets]) => (
              <View key={stageName} style={styles.column}>
                <Text style={styles.stageHeader} numberOfLines={1}>
                  {stageName}
                </Text>
                {stageSets.map((set) => {
                  const top = setTop(set.starts_at);
                  const height = setHeight(set.starts_at, set.ends_at);
                  const picked = pickedIds.has(set.set_id);
                  return (
                    <TouchableOpacity
                      key={set.set_id}
                      style={[
                        styles.setBlock,
                        { top: top + 24, height },
                        picked && styles.setBlockPicked,
                      ]}
                      onPress={() => onSelectSet(set)}
                      testID={`grid-set-${set.set_id}`}
                    >
                      <Text style={styles.setName} numberOfLines={2}>
                        {set.display_name}
                      </Text>
                    </TouchableOpacity>
                  );
                })}
              </View>
            ))}
          </View>
        </View>
      </ScrollView>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    position: "relative",
    minWidth: "100%",
  },
  columns: {
    flexDirection: "row",
    marginLeft: 46,
    gap: 4,
  },
  column: {
    width: COLUMN_WIDTH,
    position: "relative",
  },
  stageHeader: {
    color: colors.text.secondary,
    fontSize: 11,
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: 1,
    height: 24,
    textAlign: "center",
  },
  setBlock: {
    position: "absolute",
    left: 2,
    right: 2,
    borderRadius: radius.sm,
    backgroundColor: colors.bg.elevated,
    borderWidth: 1,
    borderColor: colors.border.default,
    padding: 4,
    overflow: "hidden",
  },
  setBlockPicked: {
    borderColor: colors.neon.violet,
    backgroundColor: "rgba(166,75,255,0.18)",
  },
  setName: {
    color: colors.text.secondary,
    fontSize: 11,
  },
});

export { COLUMN_WIDTH, spacing };
