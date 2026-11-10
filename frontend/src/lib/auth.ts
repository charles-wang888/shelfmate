/**
 * Frontend auth state for ShelfMate.
 * Token is issued by the backend; this module only stores and broadcasts it.
 */
import { useSyncExternalStore } from "react";

const TOKEN_KEY = "shelfmate-token";
const USER_KEY = "shelfmate-user";
const ROLE_KEY = "shelfmate-role";
const NAME_KEY = "shelfmate-display-name";

export const UNAUTHORIZED_EVENT = "shelfmate:unauthorized";

interface AuthState {
  token: string | null;
  username: string | null;
  role: string | null;
  displayName: string | null;
}

let state: AuthState = {
  token: null,
  username: null,
  role: null,
  displayName: null,
};
const listeners = new Set<() => void>();
let loggingOut = false;

function readStorage(): AuthState {
  try {
    return {
      token: localStorage.getItem(TOKEN_KEY),
      username: localStorage.getItem(USER_KEY),
      role: localStorage.getItem(ROLE_KEY),
      displayName: localStorage.getItem(NAME_KEY),
    };
  } catch {
    return { token: null, username: null, role: null, displayName: null };
  }
}

function writeStorage(next: AuthState) {
  try {
    if (next.token) localStorage.setItem(TOKEN_KEY, next.token);
    else localStorage.removeItem(TOKEN_KEY);
    if (next.username) localStorage.setItem(USER_KEY, next.username);
    else localStorage.removeItem(USER_KEY);
    if (next.role) localStorage.setItem(ROLE_KEY, next.role);
    else localStorage.removeItem(ROLE_KEY);
    if (next.displayName) localStorage.setItem(NAME_KEY, next.displayName);
    else localStorage.removeItem(NAME_KEY);
  } catch {
    /* ignore quota / private mode */
  }
}

function emit() {
  state = readStorage();
  listeners.forEach((l) => l());
}

function subscribe(cb: () => void) {
  listeners.add(cb);
  return () => listeners.delete(cb);
}

// Hydrate once on module load
state = readStorage();

export function getToken(): string | null {
  return readStorage().token;
}

export function setSession(input: {
  token: string;
  username: string;
  role: string;
  displayName: string;
}) {
  writeStorage({
    token: input.token,
    username: input.username,
    role: input.role,
    displayName: input.displayName,
  });
  emit();
}

export function clearSession() {
  writeStorage({
    token: null,
    username: null,
    role: null,
    displayName: null,
  });
  emit();
}

export function isLoggingOut() {
  return loggingOut;
}

export function logout() {
  loggingOut = true;
  clearSession();
  queueMicrotask(() => {
    loggingOut = false;
  });
}

export function useAuth() {
  const snap = useSyncExternalStore(subscribe, () => state, () => state);
  return {
    ...snap,
    isAuthenticated: Boolean(snap.token),
  };
}
