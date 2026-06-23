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
const mockPlay = jest.fn(async () => undefined);
const mockStop = jest.fn(async () => undefined);
let mockIsPlaying = false;

jest.mock("@/hooks/useArtistDetail", () => ({
  useArtistDetail: (n: string) => mockUseArtistDetail(n),
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
import type { ArtistDetailResponse } from "@/types/api";

const MOCK_ARTIST: ArtistDetailResponse = {
  artist_name: "Above & Beyond",
  genres: ["trance", "progressive"],
  top_track: { name: "Sun & Moon", preview_url: "https://cdn/preview.mp3", external_url: null },
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
});

test("renders_artist_name", () => {
  const { getByTestId } = render(<ArtistDetail />, { wrapper });
  expect(getByTestId("artist-name").props.children).toBe("Above & Beyond");
});

test("renders_genres", () => {
  const { getByText } = render(<ArtistDetail />, { wrapper });
  expect(getByText("trance")).toBeTruthy();
  expect(getByText("progressive")).toBeTruthy();
});

test("renders_top_track", () => {
  const { getByTestId } = render(<ArtistDetail />, { wrapper });
  expect(getByTestId("track-row-0")).toBeTruthy();
});

test("tap_track_with_preview_calls_play", () => {
  const { getByTestId } = render(<ArtistDetail />, { wrapper });
  fireEvent.press(getByTestId("track-row-0"));
  expect(mockPlay).toHaveBeenCalledWith("https://cdn/preview.mp3");
});

test("no_track_section_when_top_track_is_null", () => {
  const noTrack = { ...MOCK_ARTIST, top_track: null };
  mockUseArtistDetail.mockReturnValue({ data: noTrack, isLoading: false, error: null });
  const { queryByTestId } = render(<ArtistDetail />, { wrapper });
  expect(queryByTestId("track-row-0")).toBeNull();
});

test("tap_similar_artist_pushes_artist_detail", () => {
  const { getByTestId } = render(<ArtistDetail />, { wrapper });
  fireEvent.press(getByTestId("similar-Armin van Buuren"));
  expect(mockPush).toHaveBeenCalledWith("ArtistDetail", { artist_name: "Armin van Buuren" });
});

test("shows_loading_indicator_when_loading", () => {
  mockUseArtistDetail.mockReturnValue({ data: undefined, isLoading: true, error: null });
  const { UNSAFE_getByType } = render(<ArtistDetail />, { wrapper });
  expect(UNSAFE_getByType(require("react-native").ActivityIndicator)).toBeTruthy();
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
