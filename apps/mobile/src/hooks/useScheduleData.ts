import { useGroupState } from "@/hooks/useGroupState";
import { useEventLineup } from "@/hooks/useEventLineup";
import type { SetDetail } from "@/types/api";

interface UseScheduleDataResult {
  sets: SetDetail[];
  eventName: string;
  isLoading: boolean;
}

export function useScheduleData(inviteCode: string): UseScheduleDataResult {
  const { data: group, isLoading: groupLoading } = useGroupState(inviteCode);
  const eventId = group?.event.event_id ?? "";
  const { data: lineup, isLoading: lineupLoading } = useEventLineup(eventId);

  return {
    sets: lineup?.sets ?? [],
    eventName: group?.event.name ?? "",
    isLoading: groupLoading || lineupLoading,
  };
}
