import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { fetchWithAuth, type ApiError } from "@/api/client";
import type { AppleMusicArtistDetail } from "@/types/api";

export function useAppleMusicArtist(artistName: string): UseQueryResult<AppleMusicArtistDetail, ApiError> {
  const encoded = encodeURIComponent(artistName);
  return useQuery<AppleMusicArtistDetail, ApiError>({
    queryKey: ["artist-apple-music", artistName],
    queryFn: () =>
      fetchWithAuth<AppleMusicArtistDetail>(`/api/artists/${encoded}/apple-music`),
    staleTime: 24 * 60 * 60 * 1000, // 24 h — matches artist_cache_ttl_seconds
    retry: false,
    enabled: artistName.length > 0,
  });
}
