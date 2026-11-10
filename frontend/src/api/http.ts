/**
 * Shared Axios client with bearer injection and 401 broadcast.
 */
import axios from "axios";
import { clearSession, getToken, UNAUTHORIZED_EVENT } from "@/lib/auth";

export const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE ?? "/api",
  timeout: 180000,
});

http.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

http.interceptors.response.use(
  (resp) => resp.data,
  (err) => {
    const url = String(err?.config?.url ?? "");
    const isLoginRequest = url.includes("/auth/login");
    const status = err?.response?.status;
    if (status === 401 && !isLoginRequest) {
      clearSession();
      window.dispatchEvent(new CustomEvent(UNAUTHORIZED_EVENT));
    }
    const detail = err?.response?.data?.detail;
    return Promise.reject(
      new Error(detail ? String(detail) : err?.message ?? "Request failed"),
    );
  },
);
