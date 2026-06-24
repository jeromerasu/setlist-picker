import { useGroupState } from "@/hooks/useGroupState";
import { useEventLineup } from "@/hooks/useEventLineup";
import { useMyGroups } from "@/hooks/useMyGroups";
import { stageColorByIndex } from "@/utils/stageColors";
import type { SetDetail, StageDetail } from "@/types/api";

export interface StageInfo {
  name: string;
  color: string;
}

export interface UseScheduleDataResult {
  sets: SetDetail[];
  stages: StageDetail[];
  stageBySetId: Map<string, StageInfo>;
  eventName: string;
  myMemberId: string | undefined;
  isLoading: boolean;
}

export function useScheduleData(inviteCode: string): UseScheduleDataResult {
  const { data: group, isLoading: groupLoading } = useGroupState(inviteCode);
  const eventId = group?.event.event_id ?? "";
  const { data: lineup, isLoading: lineupLoading } = useEventLineup(eventId);
  const { data: myGroups } = useMyGroups();

  const stages = lineup?.stages ?? [];
  const stageBySetId = new Map<string, StageInfo>();
  stages.forEach((stage) => {
    const color = stageColorByIndex(stage.display_order);
    stage.sets.forEach((set) => {
      stageBySetId.set(set.set_id, { name: stage.name, color });
    });
  });

  const myMemberId = myGroups?.groups.find((g) => g.invite_code === inviteCode)?.member_id;

  return {
    sets: lineup?.sets ?? [],
    stages,
    stageBySetId,
    eventName: group?.event.name ?? "",
    myMemberId,
    isLoading: groupLoading || lineupLoading,
  };
}
