import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, clearToken, getToken, setToken } from "@/api/client";
import type { User } from "@/api/types";

interface Token {
  access_token: string;
  token_type: string;
}

export function useCurrentUser() {
  return useQuery({
    queryKey: ["me"],
    queryFn: () => api.get<User>("/auth/me"),
    enabled: !!getToken(),
    retry: false,
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { email: string; password: string }) => api.post<Token>("/auth/login", payload),
    onSuccess: (token) => {
      setToken(token.access_token);
      queryClient.invalidateQueries({ queryKey: ["me"] });
    },
  });
}

export function useRegister() {
  return useMutation({
    mutationFn: (payload: { email: string; password: string; full_name?: string }) =>
      api.post<User>("/auth/register", payload),
  });
}

export function logout(): void {
  clearToken();
  window.location.href = "/login";
}
