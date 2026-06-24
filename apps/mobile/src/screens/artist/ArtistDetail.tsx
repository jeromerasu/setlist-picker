import {
  ActivityIndicator,
  Image,
  Linking,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { ScreenContainer } from "@/components/ScreenContainer";
import { useRoute, useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp, NativeStackScreenProps } from "@react-navigation/native-stack";
import { BackChip } from "@/components/BackChip";
import { useArtistDetail } from "@/hooks/useArtistDetail";
import { useArtistSpotify } from "@/hooks/useArtistSpotify";
import { useAudioPreview } from "@/hooks/useAudioPreview";
import { colors, radius, spacing } from "@/theme/tokens";
import type { HomeStackParamList } from "@/navigation/types";
import type { TopTrack } from "@/types/api";

type Props = NativeStackScreenProps<HomeStackParamList, "ArtistDetail">;
type Nav = NativeStackNavigationProp<HomeStackParamList, "ArtistDetail">;

function toTitleCase(s: string): string {
  return s.replace(/\b\w/g, (c) => c.toUpperCase());
}

function fmtDuration(ms: number | null): string {
  if (ms == null) return "";
  const total = Math.floor(ms / 1000);
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

export function ArtistDetail() {
  const route = useRoute<Props["route"]>();
  const navigation = useNavigation<Nav>();
  const { artist_name } = route.params;

  const { data, isLoading, error } = useArtistDetail(artist_name);
  const { data: spotifyData, isLoading: spotifyLoading } = useArtistSpotify(artist_name);
  const { isPlaying, play, stop } = useAudioPreview();

  const handleTrackPress = async (track: TopTrack) => {
    if (track.preview_url == null) return;
    if (isPlaying) {
      await stop();
    } else {
      await play(track.preview_url);
    }
  };

  const handleSpotifyLink = (url: string | null) => {
    if (url == null) return;
    void Linking.openURL(url);
  };

  if (isLoading) {
    return (
      <ScreenContainer style={styles.center}>
        <ActivityIndicator color={colors.neon.violet} testID="artist-loading" />
      </ScreenContainer>
    );
  }

  if (error != null || data == null) {
    return (
      <ScreenContainer style={styles.center}>
        <Text style={styles.errorText}>Artist not found</Text>
      </ScreenContainer>
    );
  }

  // Prefer Spotify-sourced image if available; fall back to existing detail image
  const heroImage = spotifyData?.image_url ?? data.image_url;
  // Use Spotify genres list when available (more complete); fall back to detail genres
  const genres =
    spotifyData != null && spotifyData.genres.length > 0 ? spotifyData.genres : data.genres;
  // Top 5 tracks from Spotify endpoint; single track fallback from detail
  const topTracks: TopTrack[] =
    spotifyData != null && spotifyData.top_tracks.length > 0
      ? spotifyData.top_tracks
      : data.top_track != null
        ? [data.top_track]
        : [];

  return (
    <ScreenContainer style={styles.screen}>
      {/* Hero image + back chip */}
      <View style={styles.heroContainer}>
        {heroImage != null ? (
          <Image
            source={{ uri: heroImage }}
            style={styles.heroImage}
            resizeMode="cover"
            testID="artist-hero-image"
          />
        ) : (
          <View style={styles.heroPlaceholder} />
        )}
        {/* Gradient scrim over hero */}
        <View style={styles.heroScrim} />
        <View style={styles.headerRow}>
          <BackChip onPress={() => navigation.goBack()} />
        </View>
        {/* Artist name overlaid on hero */}
        <View style={styles.heroNameContainer}>
          <Text style={styles.name} testID="artist-name" numberOfLines={2}>
            {data.artist_name}
          </Text>
        </View>
      </View>

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {/* Genre hierarchy: primary pill (gradient) + sub-genre chips */}
        {genres.length > 0 && (
          <View style={styles.genreSection}>
            <LinearGradient
              colors={["#ff2d9b", "#a64bff", "#28e0ff"]}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={styles.primaryGenrePill}
              testID="primary-genre-chip"
            >
              <Text style={styles.primaryGenreText}>{toTitleCase(genres[0])}</Text>
            </LinearGradient>
            {genres.length > 1 && (
              <View style={styles.subGenreRow}>
                {genres.slice(1).map((g, i) => (
                  <View key={g} style={styles.subGenrePill} testID={`subgenre-chip-${i}`}>
                    <Text style={styles.subGenreText}>{toTitleCase(g)}</Text>
                  </View>
                ))}
              </View>
            )}
          </View>
        )}

        {/* Top tracks section */}
        <View style={styles.section}>
          <View style={styles.sectionHeaderRow}>
            <Text style={styles.sectionTitle}>TOP TRACKS</Text>
            {spotifyLoading && (
              <ActivityIndicator size="small" color={colors.neon.violet} testID="tracks-loading" />
            )}
          </View>

          {!spotifyLoading && topTracks.length === 0 && (
            <Text style={styles.emptyText}>More info coming soon</Text>
          )}

          {topTracks.map((track, i) => (
            <TouchableOpacity
              key={`${track.name}-${i}`}
              style={styles.trackRow}
              onPress={() => void handleTrackPress(track)}
              testID={`track-row-${i}`}
              activeOpacity={track.preview_url != null ? 0.7 : 1}
            >
              <Text style={styles.trackNum}>{String(i + 1).padStart(2, "0")}</Text>
              <Text style={styles.trackName} numberOfLines={1}>
                {track.name}
              </Text>
              <Text style={styles.trackDuration}>{fmtDuration(track.duration_ms)}</Text>
              {track.preview_url != null && (
                <Text style={styles.playIcon} testID={`play-icon-${i}`}>
                  {isPlaying ? "■" : "▶"}
                </Text>
              )}
              {track.spotify_url != null && (
                <TouchableOpacity
                  onPress={() => handleSpotifyLink(track.spotify_url)}
                  hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
                  testID={`spotify-link-${i}`}
                >
                  <Text style={styles.spotifyIcon}>↗</Text>
                </TouchableOpacity>
              )}
            </TouchableOpacity>
          ))}
        </View>

        {/* Similar artists */}
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
    </ScreenContainer>
  );
}

const HERO_H = 260;

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.bg.canvas,
  },
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.bg.canvas,
  },
  // Hero
  heroContainer: {
    height: HERO_H,
    backgroundColor: colors.bg.deep,
    position: "relative",
  },
  heroImage: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
  },
  heroPlaceholder: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: colors.bg.surfaceWeak,
  },
  heroScrim: {
    position: "absolute",
    left: 0,
    right: 0,
    bottom: 0,
    height: HERO_H,
    // Gradient-style scrim: near-opaque at bottom, transparent at top
    backgroundColor: "rgba(10,7,18,0.6)",
  },
  headerRow: {
    position: "absolute",
    top: spacing[9],
    left: spacing.screenPad,
    right: spacing.screenPad,
  },
  heroNameContainer: {
    position: "absolute",
    bottom: spacing[8],
    left: spacing.screenPad,
    right: spacing.screenPad,
  },
  name: {
    fontFamily: "PlayfairDisplay-Bold",
    fontSize: 32,
    color: colors.text.primary,
    lineHeight: 38,
  },
  // Scroll content
  scroll: { flex: 1 },
  scrollContent: {
    paddingHorizontal: spacing.screenPad,
    paddingTop: spacing[7],
    paddingBottom: spacing[12],
    gap: spacing[8],
  },
  // Genres
  genreSection: { gap: spacing[3] },
  primaryGenrePill: {
    alignSelf: "flex-start",
    borderRadius: radius.full,
    paddingHorizontal: spacing[6],
    paddingVertical: spacing[5],
  },
  primaryGenreText: {
    fontFamily: "Manrope-Bold",
    fontSize: 16,
    color: colors.text.invertedDark,
  },
  subGenreRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing[3],
  },
  subGenrePill: {
    backgroundColor: colors.bg.surfaceMed,
    borderRadius: radius.full,
    borderWidth: 1,
    borderColor: colors.border.default,
    paddingHorizontal: spacing[5],
    paddingVertical: spacing[4],
  },
  subGenreText: {
    fontFamily: "Manrope-SemiBold",
    fontSize: 13,
    color: colors.text.iconAccent,
  },
  // Sections
  section: { gap: spacing[4] },
  sectionHeaderRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  sectionTitle: {
    fontFamily: "Manrope-Bold",
    fontSize: 12,
    letterSpacing: 1.2,
    color: colors.text.secondary,
    textTransform: "uppercase",
  },
  emptyText: {
    fontFamily: "Manrope-Regular",
    fontSize: 14,
    color: colors.text.muted,
  },
  // Tracks
  trackRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing[4],
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: colors.border.subtle,
  },
  trackNum: {
    fontFamily: "SpaceMono-Regular",
    fontSize: 12,
    color: colors.text.muted,
    width: 22,
  },
  trackName: {
    flex: 1,
    fontFamily: "Manrope-SemiBold",
    fontSize: 15,
    color: colors.text.primary,
  },
  trackDuration: {
    fontFamily: "SpaceMono-Regular",
    fontSize: 11,
    color: colors.text.muted,
  },
  playIcon: {
    fontFamily: "Manrope-Regular",
    fontSize: 13,
    color: colors.neon.violet,
  },
  spotifyIcon: {
    fontFamily: "Manrope-Bold",
    fontSize: 14,
    color: colors.text.success,
  },
  // Similar artists
  similarGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing[3],
  },
  similarPill: {
    borderWidth: 1,
    borderColor: colors.border.default,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: radius.sm,
    backgroundColor: colors.bg.surfaceWeak,
  },
  similarName: {
    fontFamily: "Manrope-Medium",
    fontSize: 13,
    color: colors.text.secondary,
  },
  errorText: {
    fontFamily: "Manrope-Regular",
    fontSize: 15,
    color: colors.neon.pink,
  },
});
