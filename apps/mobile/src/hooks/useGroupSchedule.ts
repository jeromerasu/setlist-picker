import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { fetchWithAuth } from "@/api/client";
import type { GroupScheduleResponse } from "@/types/api";

export function useGroupSchedule(
  groupCode: string,
  dayLabel: string,
): UseQueryResult<GroupScheduleResponse> {
  return useQuery<GroupScheduleResponse>({
    queryKey: ["group-schedule", groupCode, dayLabel],
    queryFn: () =>
      fetchWithAuth<GroupScheduleResponse>(
        `/api/groups/${groupCode}/schedule?day_label=${encodeURIComponent(dayLabel)}`,
      ),
    staleTime: 30_000,
    enabled: groupCode.length > 0 && dayLabel.length > 0,
  });
}
