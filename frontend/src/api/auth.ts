import { apiRequest, clearSession, setSession } from "./client";

export type AuthUser = {
  id: string;
  username: string;
  display_name: string;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
  user: AuthUser;
};

export const authApi = {
  register: (payload: { username: string; password: string; display_name?: string }) =>
    apiRequest<TokenResponse>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  login: (payload: { username: string; password: string }) =>
    apiRequest<TokenResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  me: () => apiRequest<AuthUser>("/api/auth/me"),

  applySession(resp: TokenResponse) {
    setSession(resp.access_token, resp.user);
  },

  logout() {
    clearSession();
  },
};
