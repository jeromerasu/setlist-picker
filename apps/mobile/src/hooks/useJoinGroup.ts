import { useMutation, type UseMutationResult } from "@tanstack/react-query";
import { fetchWithAuth, type ApiError } from "@/api/client";
import { normalizeCode } from "@/utils/inviteCode";
import type { GroupJoinResponse } from "@/types/api";

interface JoinGroupInput {
  invite_code: string;
  display_name_override?: string;
}

export function useJoinGroup(): UseMutationResult<GroupJoinResponse, ApiError, JoinGroupInput> {
  return useMutation<GroupJoinResponse, ApiError, JoinGroupInput>({
    mutationFn: (input: JoinGroupInput) =>
      fetchWithAuth<GroupJoinResponse>("/api/groups/join", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...input, invite_code: normalizeCode(input.invite_code) }),
      }),
  });
}
