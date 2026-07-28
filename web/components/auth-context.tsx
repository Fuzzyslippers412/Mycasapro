"use client";

import { createContext, FormEvent, ReactNode, useContext, useEffect, useState } from "react";
import { apiError, apiFetch } from "@/lib/api";
import type { User } from "@/lib/types";

type AccountRole = "homeowner" | "contractor";

type AuthContextValue = {
  user: User;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("useAuth must be used inside AuthGate");
  }
  return value;
}

export function AuthGate({ requiredRole, children }: { requiredRole: AccountRole; children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [mode, setMode] = useState<"register" | "login">("register");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void apiFetch("/api/v1/auth/me")
      .then(async (response) => {
        if (!response.ok) return null;
        return (await response.json()) as { user: User };
      })
      .then((payload) => {
        if (active && payload) setUser(payload.user);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    setSubmitting(true);
    setError(null);
    try {
      const response = await apiFetch(`/api/v1/auth/${mode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          display_name: mode === "register" ? formData.get("display_name") : undefined,
          email: formData.get("email"),
          password: formData.get("password"),
          role: mode === "register" ? requiredRole : undefined,
        }),
      });
      if (!response.ok) {
        throw new Error(await apiError(response, "Unable to continue"));
      }
      const payload = (await response.json()) as { user: User };
      setUser(payload.user);
      form.reset();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to continue");
    } finally {
      setSubmitting(false);
    }
  }

  async function logout() {
    await apiFetch("/api/v1/auth/logout", { method: "POST" });
    setUser(null);
    setMode("login");
  }

  if (loading) {
    return (
      <main className="auth-page" aria-busy="true">
        <div className="auth-loading-card">
          <span className="brand-name">MyCasa</span><span className="brand-pro">Pro</span>
          <div className="skeleton skeleton-title" />
          <div className="skeleton skeleton-line" />
        </div>
      </main>
    );
  }

  if (!user) {
    return (
      <main className="auth-page">
        <section className="auth-story" aria-label="MyCasaPro introduction">
          <a className="auth-brand" href="/">
            <span className="brand-name">MyCasa</span>
            <span className="brand-pro">Pro</span>
          </a>
          <div className="auth-story-copy">
            <p className="kicker">{requiredRole === "homeowner" ? "The home register" : "The professional work desk"}</p>
            <h1>{requiredRole === "homeowner" ? "Care for the place that is yours." : "Good work deserves a clean record."}</h1>
            <p>
              {requiredRole === "homeowner"
                ? "Keep repairs, visits, decisions, and documents with the home—not scattered across messages and folders."
                : "Keep the scope, schedule, updates, and payment history clear for every client and every address."}
            </p>
          </div>
          <p className="auth-aside-note">Private by default. Shared only when the work requires it.</p>
        </section>

        <section className="auth-panel">
          <div className="auth-panel-inner">
            <p className="kicker">{requiredRole === "homeowner" ? "Home access" : "Professional access"}</p>
            <h2>{mode === "register" ? "Begin your record" : "Welcome back"}</h2>
            <p className="auth-subtitle">
              {mode === "register" ? "Nothing is pre-filled. Add only what belongs to you." : "Sign in to continue where you left off."}
            </p>

            <div className="auth-tabs" role="tablist" aria-label="Account access">
              <button className={mode === "register" ? "is-active" : ""} type="button" onClick={() => setMode("register")}>Create account</button>
              <button className={mode === "login" ? "is-active" : ""} type="button" onClick={() => setMode("login")}>Sign in</button>
            </div>

            {error ? <div className="form-error" role="alert">{error}</div> : null}

            <form className="auth-form" onSubmit={submit}>
              {mode === "register" ? (
                <label>
                  <span>Your name</span>
                  <input name="display_name" autoComplete="name" required minLength={2} />
                </label>
              ) : null}
              <label>
                <span>Email address</span>
                <input name="email" type="email" autoComplete="email" required />
              </label>
              <label>
                <span>Password</span>
                <input name="password" type="password" autoComplete={mode === "register" ? "new-password" : "current-password"} minLength={10} required />
                {mode === "register" ? <small>Use at least 10 characters.</small> : null}
              </label>
              <button className="primary-button" type="submit" disabled={submitting}>
                {submitting ? "Please wait..." : mode === "register" ? "Create account" : "Sign in"}
              </button>
            </form>

            <a className="role-switch-link" href={requiredRole === "homeowner" ? "/contractor" : "/homeowner"}>
              {requiredRole === "homeowner" ? "I work as a contractor" : "I am a homeowner"}
            </a>
          </div>
        </section>
      </main>
    );
  }

  const roleMatches = requiredRole === "homeowner" ? user.role === "homeowner" : user.role !== "homeowner";
  if (!roleMatches) {
    return (
      <main className="auth-page auth-page-centered">
        <section className="account-mismatch-card">
          <span className="brand-name">MyCasa</span><span className="brand-pro">Pro</span>
          <p className="kicker">Different workspace</p>
          <h1>This account belongs to the {user.role === "homeowner" ? "homeowner" : "contractor"} workspace.</h1>
          <a className="primary-button" href={user.role === "homeowner" ? "/homeowner" : "/contractor"}>Open the correct workspace</a>
          <button className="text-button" type="button" onClick={() => void logout()}>Sign out</button>
        </section>
      </main>
    );
  }

  return <AuthContext.Provider value={{ user, logout }}>{children}</AuthContext.Provider>;
}
