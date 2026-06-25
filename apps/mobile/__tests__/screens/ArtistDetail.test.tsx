import React from "react";
import { render, fireEvent } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// ─── Navigation ──────────────────────────────────────────────────────────────

const mockPush = jest.fn();
const mockGoBack = jest.fn();

jest.mock("@react-navigation/native", () => {
  const RN = require("react-native");
  return {
    useNavigation: () => ({ push: mockPush, goBack: mockGoBack }),
    useRoute: () => ({ params: { artist_name: "Above & Beyond" } }),
    NavigationContainer: ({ children }: { children: unknown }) =>
      require("react").createElement(RN.View, null, children),
  };
});

// ─── Hook mocks ──────────────────────────────────────────────────────────────

const mockUseArtistDetail = jest.fn();
const mockUseArtistSpotify = jest.fn();
const mockUseAppleMusicArtist = jest.fn();
const mockPlay = jest.fn(async () => undefined);
const mockStop = jest.fn(async () => undefined);
let mockIsPlaying = false;

jest.mock("@/hooks/useArtistDetail", () => ({
  useArtistDetail: (n: string) => mockUseArtistDetail(n),
}));
jest.mock("@/hooks/useArtistSpotify", () => ({
  useArtistSpotify: (n: string) => mockUseArtistSpotify(n),
}));
jest.mock("@/hooks/useAppleMusicArtist", () => ({
  useAppleMusicArtist: (n: string) => mockUseAppleMusicArtist(n),
}));
jest.mock("@/hooks/useAudioPreview", () => ({
  useAudioPreview: () => ({ isPlaying: mockIsPlaying, play: mockPlay, stop: mockStop }),
}));
jest.mock("expo-secure-store", () => ({
  getItemAsync: jest.fn(async () => null),
  setItemAsync: jest.fn(async () => undefined),
  deleteItemAsync: jest.fn(async () => undefined),
}));

// ─── Subject ─────────────────────────────────────────────────────────────────

import { ArtistDetail } from "@/screens/artist/ArtistDetail";
import type { ArtistDetailResponse, SpotifyArtistDetail, TopTrack } from "@/types/api";

const MOCK_ARTIST: ArtistDetailResponse = {
  artist_name: "Above & Beyond",
  spotify_url: "https://open.spotify.com/artist/xyz",
  genres: ["trance", "progressive"],
  top_track: {
    name: "Sun & Moon",
    preview_url: "https://cdn/preview.mp3",
    external_url: null,
    spotify_url: null,
    apple_music_url: null,
    duration_ms: null,
  },
  similar_artists: [
    { name: "Armin van Buuren", similarity: 0.9 },
    { name: "Ferry Corsten", similarity: 0.8 },
  ],
  spotify_artist_id: "sp1",
  image_url: null,
  cache_status: "fresh",
  similarity_source: null,
  fetched_at: null,
};

const MOCK_SPOTIFY: SpotifyArtistDetail = {
  artist_name: "Above & Beyond",
  image_url: "https://img.example.com/ab.jpg",
  genres: ["trance", "progressive"],
  top_tracks: [
    {
      name: "Sun & Moon",
      preview_url: "https://cdn/preview.mp3",
      external_url: null,
      spotify_url: "https://open.spotify.com/t/1",
      apple_music_url: null,
      duration_ms: 240_000,
    },
    {
      name: "Northern Soul",
      preview_url: null,
      external_url: null,
      spotify_url: "https://open.spotify.com/t/2",
      apple_music_url: null,
      duration_ms: 300_000,
    },
    {
      name: "Thing Called Love",
      preview_url: null,
      external_url: null,
      spotify_url: null,
      apple_music_url: null,
      duration_ms: 280_000,
    },
  ],
};

const SPOTIFY_LOADING = { data: undefined, isLoading: true };
const SPOTIFY_ERROR = { data: undefined, isLoading: false };

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return React.createElement(QueryClientProvider, { client: qc }, children);
}

beforeEach(() => {
  mockPush.mockReset();
  mockGoBack.mockReset();
  mockPlay.mockReset();
  mockStop.mockReset();
  mockIsPlaying = false;
  mockUseArtistDetail.mockReturnValue({ data: MOCK_ARTIST, isLoading: false, error: null });
  mockUseArtistSpotify.mockReturnValue({ data: MOCK_SPOTIFY, isLoading: false });
  mockUseAppleMusicArtist.mockReturnValue({ data: undefined, isLoading: false });
});

// ─── Cosmic-Neon palette: cyberColors must be gone ───────────────────────────

test("no_cyber_import_in_screen", () => {
  // The screen must not import or reference cyberColors at all
  const source = require("fs").readFileSync(
    require.resolve("@/screens/artist/ArtistDetail"),
    "utf-8",
  );
  expect(source).not.toContain("cyberColors");
  expect(source).not.toContain("cyber");
});

// ─── Base rendering ──────────────────────────────────────────────────────────

test("renders_artist_name", () => {
  const { getByTestId } = render(<ArtistDetail />, { wrapper });
  expect(getByTestId("artist-name").props.children).toBe("Above & Beyond");
});

test("renders_genres_from_spotify_when_available", () => {
  const { getByText } = render(<ArtistDetail />, { wrapper });
  // Genres are title-cased for display
  expect(getByText("Trance")).toBeTruthy();
  expect(getByText("Progressive")).toBeTruthy();
});

test("renders_genres_from_detail_when_spotify_not_loaded", () => {
  mockUseArtistSpotify.mockReturnValue(SPOTIFY_ERROR);
  const { getByText } = render(<ArtistDetail />, { wrapper });
  expect(getByText("Trance")).toBeTruthy();
});

test("primary_genre_chip_rendered_as_gradient_pill", () => {
  const { getByTestId } = render(<ArtistDetail />, { wrapper });
  expect(getByTestId("primary-genre-chip")).toBeTruthy();
});

test("sub_genre_chips_rendered_for_remaining_genres", () => {
  const { getByTestId } = render(<ArtistDetail />, { wrapper });
  // genres[1] = "progressive" → subgenre-chip-0
  expect(getByTestId("subgenre-chip-0")).toBeTruthy();
});

test("no_genre_section_when_genres_empty", () => {
  mockUseArtistDetail.mockReturnValue({
    data: { ...MOCK_ARTIST, genres: [] },
    isLoading: false,
    error: null,
  });
  mockUseArtistSpotify.mockReturnValue({ data: { ...MOCK_SPOTIFY, genres: [] }, isLoading: false });
  const { queryByTestId } = render(<ArtistDetail />, { wrapper });
  expect(queryByTestId("primary-genre-chip")).toBeNull();
});

test("renders_top_five_tracks_from_spotify", () => {
  const { getByTestId } = render(<ArtistDetail />, { wrapper });
  expect(getByTestId("track-row-0")).toBeTruthy();
  expect(getByTestId("track-row-1")).toBeTruthy();
  expect(getByTestId("track-row-2")).toBeTruthy();
});

test("falls_back_to_single_track_when_spotify_not_loaded", () => {
  mockUseArtistSpotify.mockReturnValue(SPOTIFY_ERROR);
  const { getByTestId, queryByTestId } = render(<ArtistDetail />, { wrapper });
  expect(getByTestId("track-row-0")).toBeTruthy();
  expect(queryByTestId("track-row-1")).toBeNull();
});

test("tap_track_with_preview_calls_play", () => {
  const { getByTestId } = render(<ArtistDetail />, { wrapper });
  fireEvent.press(getByTestId("track-row-0"));
  expect(mockPlay).toHaveBeenCalledWith("https://cdn/preview.mp3");
});

test("no_track_section_play_when_no_preview_url", () => {
  const { getByTestId } = render(<ArtistDetail />, { wrapper });
  fireEvent.press(getByTestId("track-row-1")); // Northern Soul has no preview
  expect(mockPlay).not.toHaveBeenCalled();
});

test("track_duration_displayed", () => {
  const { getByText } = render(<ArtistDetail />, { wrapper });
  expect(getByText("4:00")).toBeTruthy(); // 240_000ms
});

test("spotify_link_icon_shown_when_spotify_url_present", () => {
  const { getByTestId } = render(<ArtistDetail />, { wrapper });
  expect(getByTestId("spotify-link-0")).toBeTruthy(); // Sun & Moon has spotify_url
});

test("no_spotify_link_icon_when_no_url", () => {
  const { queryByTestId } = render(<ArtistDetail />, { wrapper });
  // Track 2 (Thing Called Love) has no spotify_url
  expect(queryByTestId("spotify-link-2")).toBeNull();
});

test("hero_image_shown_when_spotify_image_available", () => {
  const { getByTestId } = render(<ArtistDetail />, { wrapper });
  expect(getByTestId("artist-hero-image")).toBeTruthy();
});

test("empty_state_shown_when_no_tracks_and_not_loading", () => {
  mockUseArtistDetail.mockReturnValue({
    data: { ...MOCK_ARTIST, top_track: null },
    isLoading: false,
    error: null,
  });
  mockUseArtistSpotify.mockReturnValue({ data: { ...MOCK_SPOTIFY, top_tracks: [] }, isLoading: false });
  const { getByText } = render(<ArtistDetail />, { wrapper });
  expect(getByText("More info coming soon")).toBeTruthy();
});

test("tracks_loading_spinner_shown_while_apple_music_loading", () => {
  mockUseAppleMusicArtist.mockReturnValue({ data: undefined, isLoading: true });
  const { getByTestId } = render(<ArtistDetail />, { wrapper });
  expect(getByTestId("tracks-loading")).toBeTruthy();
});

test("no_track_section_when_top_track_is_null_and_no_spotify", () => {
  const noTrack = { ...MOCK_ARTIST, top_track: null };
  mockUseArtistDetail.mockReturnValue({ data: noTrack, isLoading: false, error: null });
  mockUseArtistSpotify.mockReturnValue(SPOTIFY_ERROR);
  const { queryByTestId } = render(<ArtistDetail />, { wrapper });
  expect(queryByTestId("track-row-0")).toBeNull();
});

test("tap_similar_artist_pushes_artist_detail", () => {
  const { getByTestId } = render(<ArtistDetail />, { wrapper });
  fireEvent.press(getByTestId("similar-Armin van Buuren"));
  expect(mockPush).toHaveBeenCalledWith("ArtistDetail", { artist_name: "Armin van Buuren" });
});

test("shows_loading_indicator_when_detail_loading", () => {
  mockUseArtistDetail.mockReturnValue({ data: undefined, isLoading: true, error: null });
  const { getByTestId } = render(<ArtistDetail />, { wrapper });
  expect(getByTestId("artist-loading")).toBeTruthy();
});

test("shows_error_when_artist_not_found", () => {
  mockUseArtistDetail.mockReturnValue({ data: undefined, isLoading: false, error: new Error("404") });
  const { getByText } = render(<ArtistDetail />, { wrapper });
  expect(getByText(/Artist not found/)).toBeTruthy();
});

test("back_chip_navigates_back", () => {
  const { getByLabelText } = render(<ArtistDetail />, { wrapper });
  fireEvent.press(getByLabelText("Go back"));
  expect(mockGoBack).toHaveBeenCalled();
});

// ─── Spotify external link ────────────────────────────────────────────────────

test("spotify_external_link_shown_when_url_present", () => {
  const { getByTestId } = render(<ArtistDetail />, { wrapper });
  expect(getByTestId("spotify-external-link")).toBeTruthy();
});

test("spotify_external_link_hidden_when_url_null", () => {
  mockUseArtistDetail.mockReturnValue({
    data: { ...MOCK_ARTIST, spotify_url: null },
    isLoading: false,
    error: null,
  });
  const { queryByTestId } = render(<ArtistDetail />, { wrapper });
  expect(queryByTestId("spotify-external-link")).toBeNull();
});
