import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { fetchWithAuth } from "@/api/client";
import type { MyGroupListResponse } from "@/types/api";

const STALE_TIME = 15_000;

export function useMyGroups(): UseQueryResult<MyGroupListResponse> {
  return useQuery<MyGroupListResponse>({
    queryKey: ["my-groups"],
    queryFn: () => fetchWithAuth<MyGroupListResponse>("/api/users/me/groups"),
    staleTime: STALE_TIME,
    refetchOnWindowFocus: true,
  });
}
