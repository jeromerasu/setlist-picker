import { useMutation, type UseMutationResult } from "@tanstack/react-query";
import { fetchWithAuth, type ApiError } from "@/api/client";
import type { GroupCreateResponse } from "@/types/api";

interface CreateGroupInput {
  name?: string;
  event_id: string;
}

export function useCreateGroup(): UseMutationResult<GroupCreateResponse, ApiError, CreateGroupInput> {
  return useMutation<GroupCreateResponse, ApiError, CreateGroupInput>({
    mutationFn: (input: CreateGroupInput) =>
      fetchWithAuth<GroupCreateResponse>("/api/groups", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
      }),
  });
}
