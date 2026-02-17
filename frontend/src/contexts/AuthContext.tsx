"use client";

import { createContext, useContext, useState, ReactNode, useEffect } from "react";
import { apiFetch, isNetworkError } from "@/lib/api";

interface User {
  id: number;
  username: string;
  email: string;
  is_admin: boolean;
  display_name?: string | null;
  status?: string | null;
  org_id?: string | null;
  avatar_url?: string | null;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  avatarVersion: number;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<User | null>;
  bumpAvatarVersion: () => void;
  isAuthenticated: boolean;
  isAdmin: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [avatarVersion, setAvatarVersion] = useState<number>(0);

  useEffect(() => {
    // Load session from cookie or stored token on mount
    const stored =
      typeof window !== "undefined" ? localStorage.getItem("token") : null;
    if (stored) {
      validateToken(stored);
    } else {
      refreshUser();
    }
  }, []);

  const validateToken = async (token?: string | null): Promise<User | null> => {
    try {
      const headers = token ? { Authorization: `Bearer ${token}` } : undefined;
      const userData = await apiFetch<User>("/api/auth/me", headers ? { headers } : {});
      setUser(userData);
      setToken(token || null);
      if (typeof window !== "undefined" && token) {
        localStorage.setItem("token", token);
      }
      return userData;
    } catch (error) {
      if (typeof window !== "undefined") {
        localStorage.removeItem("token");
      }
      setToken(null);
      setUser(null);
      return null;
    }
  };

  const login = async (username: string, password: string) => {
    try {
      const data = await apiFetch<{ token: string; user: User }>("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      const { token, user } = data;

      setToken(token);
      setUser(user);
      if (typeof window !== "undefined" && token) {
        localStorage.setItem("token", token);
      }
      try {
        await apiFetch("/api/clawdbot/sessions/cleanup", {
          method: "POST",
          body: JSON.stringify({ prefix: "mycasa_" }),
        });
      } catch {
        // Ignore cleanup errors
      }
    } catch (error: any) {
      if (isNetworkError(error)) {
        throw new Error(error?.message || "Unable to reach backend. Start the server and try again.");
      }
      if (error?.status === 401) {
        throw new Error("Invalid credentials");
      }
      throw new Error(error?.detail || error?.message || "Login failed");
    }
  };

  const register = async (username: string, email: string, password: string) => {
    try {
      const data = await apiFetch<{ token: string; user: User }>("/api/auth/register", {
        method: "POST",
        body: JSON.stringify({ username, email, password }),
      });
      const { token, user } = data;
      setToken(token);
      setUser(user);
      if (typeof window !== "undefined" && token) {
        localStorage.setItem("token", token);
      }
      try {
        await apiFetch("/api/clawdbot/sessions/cleanup", {
          method: "POST",
          body: JSON.stringify({ prefix: "mycasa_" }),
        });
      } catch {
        // Ignore cleanup errors
      }
    } catch (error: any) {
      if (isNetworkError(error)) {
        throw new Error(error?.message || "Unable to reach backend. Start the server and try again.");
      }
      throw new Error(error?.detail || error?.message || "Registration failed");
    }
  };

  const logout = async () => {
    try {
      await apiFetch("/backup/export", { method: "POST" }, 15000);
    } catch (error) {
      // Ignore backup errors; logout should still proceed
    }
    try {
      await apiFetch("/api/clawdbot/sessions/cleanup", {
        method: "POST",
        body: JSON.stringify({ prefix: "mycasa_" }),
      });
    } catch (error) {
      // Ignore cleanup errors; logout should still proceed
    }
    try {
      await apiFetch("/api/auth/logout", { method: "POST" });
    } catch (error) {
      // Ignore logout errors; still clear local state
    }
    setToken(null);
    setUser(null);
    if (typeof window !== "undefined") {
      const prefixes = [
        "mycasa_chat_history_v3",
        "mycasa_manager_conversation_id",
        "mycasa_global_chat_history_v1",
        "mycasa_conversation",
        "mycasa_console_conversation_",
        "mycasa_agent_manager_conversation_",
        "mycasa_dashboard_conversation_",
      ];
      const keys = Object.keys(localStorage);
      for (const key of keys) {
        if (prefixes.some((prefix) => key.startsWith(prefix))) {
          localStorage.removeItem(key);
        }
      }
      localStorage.removeItem("token");
    }
  };

  const refreshUser = async () => {
    return await validateToken(null);
  };

  const bumpAvatarVersion = () => {
    setAvatarVersion(Date.now());
  };

  const isAuthenticated = !!user;
  const isAdmin = user?.is_admin || false;

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        avatarVersion,
        login,
        register,
        logout,
        refreshUser,
        bumpAvatarVersion,
        isAuthenticated,
        isAdmin,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
