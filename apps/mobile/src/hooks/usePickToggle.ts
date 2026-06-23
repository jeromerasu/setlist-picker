import { useMutation, useQueryClient, type UseMutationResult } from "@tanstack/react-query";
import { fetchWithAuth, type ApiError } from "@/api/client";
import type { PickResult } from "@/types/api";

interface PickToggleInput {
  invite_code: string;
  set_id: string;
  is_picked: boolean;
}

export function usePickToggle(): UseMutationResult<PickResult, ApiError, PickToggleInput> {
  const queryClient = useQueryClient();
  return useMutation<PickResult, ApiError, PickToggleInput>({
    mutationFn: ({ invite_code, set_id, is_picked }: PickToggleInput) =>
      fetchWithAuth<PickResult>(`/api/groups/${invite_code}/picks/${set_id}`, {
        method: is_picked ? "DELETE" : "POST",
      }),
    onSuccess: (_result, variables) => {
      void queryClient.invalidateQueries({ queryKey: ["group", variables.invite_code] });
    },
  });
}
