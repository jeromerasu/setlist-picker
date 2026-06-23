import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { fetchWithAuth } from "@/api/client";
import type { SetDetail } from "@/types/api";

interface EventLineupResponse {
  event_id: string;
  sets: SetDetail[];
}

export function useEventLineup(eventId: string): UseQueryResult<EventLineupResponse> {
  return useQuery<EventLineupResponse>({
    queryKey: ["lineup", eventId],
    queryFn: () => fetchWithAuth<EventLineupResponse>(`/api/events/${eventId}/lineup`),
    staleTime: Infinity,
    enabled: eventId.length > 0,
  });
}
