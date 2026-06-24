import { useMutation, type UseMutationResult } from "@tanstack/react-query";
import { fetchWithAuth, type ApiError } from "@/api/client";
import type { UserOut } from "@/types/api";

interface UpdateProfileInput {
  display_name: string;
  avatar_color: string;
}

export function useUpdateProfile(): UseMutationResult<UserOut, ApiError, UpdateProfileInput> {
  return useMutation<UserOut, ApiError, UpdateProfileInput>({
    mutationFn: (input: UpdateProfileInput) =>
      fetchWithAuth<UserOut>("/api/users/me", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
      }),
  });
}
