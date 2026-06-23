import { useMutation, useQueryClient, type UseMutationResult } from "@tanstack/react-query";
import { fetchWithAuth, type ApiError } from "@/api/client";
import type { GroupLeaveResponse } from "@/types/api";

export function useLeaveGroup(): UseMutationResult<GroupLeaveResponse, ApiError, string> {
  const queryClient = useQueryClient();
  return useMutation<GroupLeaveResponse, ApiError, string>({
    mutationFn: (invite_code: string) =>
      fetchWithAuth<GroupLeaveResponse>(`/api/groups/${invite_code}/leave`, {
        method: "DELETE",
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["my-groups"] });
    },
  });
}
