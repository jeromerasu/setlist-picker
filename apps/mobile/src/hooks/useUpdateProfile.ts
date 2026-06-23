import { useMutation, type UseMutationResult } from "@tanstack/react-query";
import { fetchWithAuth, type ApiError } from "@/api/client";

interface UpdateProfileInput {
  display_name: string;
  avatar_color: string;
}

interface UpdateProfileResponse {
  member_id: string;
  display_name: string;
  avatar_color: string;
}

export function useUpdateProfile(): UseMutationResult<UpdateProfileResponse, ApiError, UpdateProfileInput> {
  return useMutation<UpdateProfileResponse, ApiError, UpdateProfileInput>({
    mutationFn: (input: UpdateProfileInput) =>
      fetchWithAuth<UpdateProfileResponse>("/api/profile", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
      }),
  });
}
