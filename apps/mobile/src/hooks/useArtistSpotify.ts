import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { fetchWithAuth } from "@/api/client";
import type { SpotifyArtistDetail } from "@/types/api";

export function useArtistSpotify(artistName: string): UseQueryResult<SpotifyArtistDetail> {
  const encoded = encodeURIComponent(artistName);
  return useQuery<SpotifyArtistDetail>({
    queryKey: ["artist-spotify", artistName],
    queryFn: () =>
      fetchWithAuth<SpotifyArtistDetail>(`/api/artists/${encoded}/spotify`),
    staleTime: 24 * 60 * 60 * 1000, // 24h — matches BE artist_cache_ttl
    retry: false,
    enabled: artistName.length > 0,
  });
}
