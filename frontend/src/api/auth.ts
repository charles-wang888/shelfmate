import { http } from "./http";

export interface LoginResult {
  token: string;
  username: string;
  role: string;
  display_name: string;
}

export const authApi = {
  login: (username: string, password: string) =>
    http.post<unknown, LoginResult>("/auth/login", { username, password }),
  logout: () => http.post("/auth/logout"),
};
