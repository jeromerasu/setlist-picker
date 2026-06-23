import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { fetchWithAuth } from "@/api/client";
import type { ArtistDetailResponse } from "@/types/api";

export function useArtistDetail(artistName: string): UseQueryResult<ArtistDetailResponse> {
  const encoded = encodeURIComponent(artistName);
  return useQuery<ArtistDetailResponse>({
    queryKey: ["artist", artistName],
    queryFn: () => fetchWithAuth<ArtistDetailResponse>(`/api/artists/${encoded}`),
    staleTime: Infinity,
    enabled: artistName.length > 0,
  });
}
