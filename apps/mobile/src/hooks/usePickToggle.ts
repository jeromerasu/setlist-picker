import { useMutation, useQueryClient, type UseMutationResult } from "@tanstack/react-query";
import { fetchWithAuth, type ApiError } from "@/api/client";
import type { PickResult, PickSummary, GroupStateResponse } from "@/types/api";

interface PickToggleInput {
  invite_code: string;
  set_id: string;
  is_picked: boolean; // true = currently picked → DELETE; false = not picked → POST
  member_id: string;  // caller must supply — needed for same-frame optimistic add
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
    onMutate: async ({ invite_code, set_id, is_picked, member_id }) => {
      const context: PickToggleContext = { prev: undefined };
      // Skip optimistic update for adds when member_id is unknown (edge case: group not yet loaded)
      if (!is_picked && !member_id) return context;
      await queryClient.cancelQueries({ queryKey: ["group", invite_code] });
      context.prev = queryClient.getQueryData<GroupStateResponse>(["group", invite_code]);
      queryClient.setQueryData<GroupStateResponse>(["group", invite_code], (old) => {
        if (!old) return old;
        if (is_picked) {
          return { ...old, picks: old.picks.filter((p) => p.set_id !== set_id) };
        }
        const newPick: PickSummary = {
          member_id,
          set_id,
          state: "active",
          state_clock_ms: Date.now(),
        };
        return { ...old, picks: [...old.picks, newPick] };
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
      // Refetch group schedule for all days when picks change
      void queryClient.invalidateQueries({ queryKey: ["group-schedule", variables.invite_code] });
    },
  });
}
