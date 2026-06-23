import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { fetchWithAuth } from "@/api/client";
import type { GroupStateResponse } from "@/types/api";

export function useGroupState(inviteCode: string): UseQueryResult<GroupStateResponse> {
  return useQuery<GroupStateResponse>({
    queryKey: ["group", inviteCode],
    queryFn: () => fetchWithAuth<GroupStateResponse>(`/api/groups/${inviteCode}`),
    staleTime: 15_000,
    refetchOnWindowFocus: true,
  });
}
