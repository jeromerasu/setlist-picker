import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { fetchWithAuth } from "@/api/client";
import type { EventLineupResponse } from "@/types/api";

export function useEventLineup(eventId: string): UseQueryResult<EventLineupResponse> {
  return useQuery<EventLineupResponse>({
    queryKey: ["lineup", eventId],
    queryFn: () => fetchWithAuth<EventLineupResponse>(`/api/events/${eventId}/lineup`),
    staleTime: Infinity,
    enabled: eventId.length > 0,
  });
}
