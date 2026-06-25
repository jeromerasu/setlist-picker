import { useMutation, useQueryClient, type UseMutationResult } from "@tanstack/react-query";
import { fetchWithAuth } from "@/api/client";
import type { ApiError } from "@/api/client";
import { enqueuePickOp, removePickOp } from "@/lib/offlinePickQueue";
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

// Any error that isn't an HTTP response from the BE is treated as a transient
// network failure — optimistic state is preserved and the op stays in the queue
// for retry on reconnect.
// Use name-based check (not instanceof) so it works correctly in Jest where
// class identity can differ across mock factory boundaries.
function isNetworkError(error: unknown): boolean {
  if (!(error instanceof Error)) return false;
  return error.name !== "ApiError" && error.name !== "UnauthenticatedError";
}

export function usePickToggle(): UseMutationResult<PickResult, ApiError, PickToggleInput, PickToggleContext> {
  const queryClient = useQueryClient();
  return useMutation<PickResult, ApiError, PickToggleInput, PickToggleContext>({
    mutationKey: ["pick-toggle"],
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
      if (!is_picked && !member_id) return context;

      // Await enqueue so the op is durably queued before the network request fires.
      await enqueuePickOp({ invite_code, set_id, is_picked, member_id, queued_at: Date.now() });

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
    onError: (err, variables, context) => {
      if (isNetworkError(err)) {
        console.info("[pick-toggle] queued offline", { set_id: variables.set_id, member_id: variables.member_id });
        // Queue entry stays in AsyncStorage — React Query will auto-retry when
        // onlineManager signals reconnect; drain hook replays it on next app launch.
        return;
      }
      // Permanent server error (4xx/5xx): remove from queue and rollback.
      void removePickOp(variables.invite_code, variables.set_id);
      if (context?.prev != null) {
        queryClient.setQueryData(["group", variables.invite_code], context.prev);
      }
    },
    onSuccess: (_result, variables) => {
      void removePickOp(variables.invite_code, variables.set_id);
      void queryClient.invalidateQueries({ queryKey: ["group", variables.invite_code] });
      void queryClient.invalidateQueries({ queryKey: ["group-schedule", variables.invite_code] });
    },
  });
}
