import { useMutation, useQueryClient, type UseMutationResult } from "@tanstack/react-query";
import { fetchWithAuth, type ApiError } from "@/api/client";
import type { PickResult, GroupStateResponse } from "@/types/api";

interface PickToggleInput {
  invite_code: string;
  set_id: string;
  is_picked: boolean; // true = currently picked → DELETE; false = not picked → POST
}

interface PickToggleContext {
  prev: GroupStateResponse | undefined;
}

export function usePickToggle(): UseMutationResult<PickResult, ApiError, PickToggleInput, PickToggleContext> {
  const queryClient = useQueryClient();
  return useMutation<PickResult, ApiError, PickToggleInput, PickToggleContext>({
    mutationFn: ({ invite_code, set_id, is_picked }: PickToggleInput) =>
      is_picked
        ? fetchWithAuth<PickResult>(`/api/groups/${invite_code}/picks/${set_id}`, {
            method: "DELETE",
            body: JSON.stringify({ state_clock_ms: Date.now() }),
          })
        : fetchWithAuth<PickResult>(`/api/groups/${invite_code}/picks`, {
            method: "POST",
            body: JSON.stringify({ set_id, state: "active", state_clock_ms: Date.now() }),
          }),
    onMutate: async ({ invite_code, set_id, is_picked }) => {
      const context: PickToggleContext = { prev: undefined };
      // Only optimistically update for removals — adds need member_id not available locally
      if (!is_picked) return context;
      await queryClient.cancelQueries({ queryKey: ["group", invite_code] });
      context.prev = queryClient.getQueryData<GroupStateResponse>(["group", invite_code]);
      queryClient.setQueryData<GroupStateResponse>(["group", invite_code], (old) => {
        if (!old) return old;
        return { ...old, picks: old.picks.filter((p) => p.set_id !== set_id) };
      });
      return context;
    },
    onError: (_err, variables, context) => {
      if (context?.prev != null) {
        queryClient.setQueryData(["group", variables.invite_code], context.prev);
      }
    },
    onSuccess: (_result, variables) => {
      void queryClient.invalidateQueries({ queryKey: ["group", variables.invite_code] });
    },
  });
}
