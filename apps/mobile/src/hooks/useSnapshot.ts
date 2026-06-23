import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { fetchWithAuth } from "@/api/client";
import type { GroupSnapshotResponse } from "@/types/api";

export function useSnapshot(inviteCode: string, at?: string): UseQueryResult<GroupSnapshotResponse> {
  const params = at != null ? `?at=${encodeURIComponent(at)}` : "";
  return useQuery<GroupSnapshotResponse>({
    queryKey: ["snapshot", inviteCode, at ?? "now"],
    queryFn: () => fetchWithAuth<GroupSnapshotResponse>(`/api/groups/${inviteCode}/snapshot${params}`),
    staleTime: 30_000,
  });
}
