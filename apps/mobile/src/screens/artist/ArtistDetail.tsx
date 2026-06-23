import { ActivityIndicator, ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { useRoute, useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp, NativeStackScreenProps } from "@react-navigation/native-stack";
import { BackChip } from "@/components/BackChip";
import { useArtistDetail } from "@/hooks/useArtistDetail";
import { useAudioPreview } from "@/hooks/useAudioPreview";
import { cyberColors } from "@/theme/cyber";
import { spacing } from "@/theme/tokens";
import type { HomeStackParamList } from "@/navigation/types";
import type { TopTrack, ArtistDetailResponse } from "@/types/api";

type Props = NativeStackScreenProps<HomeStackParamList, "ArtistDetail">;
type Nav = NativeStackNavigationProp<HomeStackParamList, "ArtistDetail">;

export function ArtistDetail() {
  const route = useRoute<Props["route"]>();
  const navigation = useNavigation<Nav>();
  const { artist_name } = route.params;

  const { data, isLoading, error } = useArtistDetail(artist_name);
  const { isPlaying, play, stop } = useAudioPreview();

  if (isLoading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={cyberColors.neonCyan} />
      </View>
    );
  }

  if (error != null || data == null) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>Artist not found</Text>
      </View>
    );
  }

  const handleTrackPress = async (track: TopTrack) => {
    if (track.preview_url == null) return;
    if (isPlaying) {
      await stop();
    } else {
      await play(track.preview_url);
    }
  };

  return (
    <View style={styles.screen}>
      <View style={styles.header}>
        <BackChip onPress={() => navigation.goBack()} />
      </View>

      <ScrollView style={styles.scroll} contentContainerStyle={styles.scrollContent}>
        <Text style={styles.name} testID="artist-name">
          {data.artist_name}
        </Text>

        {data.genres.length > 0 && (
          <View style={styles.genres}>
            {data.genres.map((g) => (
              <Text key={g} style={styles.genrePill}>
                {g}
              </Text>
            ))}
          </View>
        )}

        {data.top_track != null && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>TOP TRACK</Text>
            <TouchableOpacity
              style={styles.trackRow}
              onPress={() => void handleTrackPress(data.top_track as TopTrack)}
              testID="track-row-0"
            >
              <Text style={styles.trackNum}>01</Text>
              <Text style={styles.trackName} numberOfLines={1}>
                {data.top_track.name}
              </Text>
              {data.top_track.preview_url != null && (
                <Text style={styles.playIcon}>{isPlaying ? "■" : "▶"}</Text>
              )}
            </TouchableOpacity>
          </View>
        )}

        {data.similar_artists.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>SIMILAR ARTISTS</Text>
            <View style={styles.similarGrid}>
              {data.similar_artists.map((a) => (
                <TouchableOpacity
                  key={a.name}
                  style={styles.similarPill}
                  onPress={() => navigation.push("ArtistDetail", { artist_name: a.name })}
                  testID={`similar-${a.name}`}
                >
                  <Text style={styles.similarName}>{a.name}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: cyberColors.bg,
    paddingTop: spacing[9],
  },
  header: {
    paddingHorizontal: spacing.screenPad,
    marginBottom: spacing[5],
  },
  scroll: { flex: 1 },
  scrollContent: {
    paddingHorizontal: spacing.screenPad,
    paddingBottom: spacing[12],
    gap: spacing[6],
  },
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: cyberColors.bg,
  },
  name: {
    color: cyberColors.neonCyan,
    fontSize: 36,
    fontWeight: "700",
  },
  genres: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing[3],
  },
  genrePill: {
    color: cyberColors.neonPink,
    fontSize: 12,
    borderWidth: 1,
    borderColor: cyberColors.neonPink,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 4,
  },
  bio: {
    color: cyberColors.text,
    fontSize: 14,
    lineHeight: 22,
  },
  section: { gap: spacing[4] },
  sectionTitle: {
    color: cyberColors.textAcid,
    fontSize: 13,
    fontWeight: "700",
    letterSpacing: 2,
  },
  trackRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing[4],
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: cyberColors.border,
  },
  trackNum: {
    color: cyberColors.textMuted,
    fontSize: 13,
    width: 24,
    fontFamily: "monospace",
  },
  trackName: {
    flex: 1,
    color: cyberColors.text,
    fontSize: 14,
  },
  playIcon: {
    color: cyberColors.neonGreen,
    fontSize: 14,
  },
  similarGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing[3],
  },
  similarPill: {
    borderWidth: 1,
    borderColor: cyberColors.border,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 4,
  },
  similarName: {
    color: cyberColors.textMuted,
    fontSize: 13,
  },
  errorText: {
    color: cyberColors.neonPink,
    fontSize: 15,
  },
});
