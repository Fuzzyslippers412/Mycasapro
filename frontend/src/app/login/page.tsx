"use client";

import { Stack, Title, Text, Card, Group, Button, Modal, TextInput, PasswordInput, Alert, Divider } from "@mantine/core";
import { LoginForm } from "@/components/forms/LoginForm";
import { RegisterForm } from "@/components/forms/RegisterForm";
import { useAuth } from "@/contexts/AuthContext";
import { getApiBaseUrl } from "@/lib/api";
import { notifications } from "@mantine/notifications";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export default function LoginPage() {
  const auth = useAuth();
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const apiBase = getApiBaseUrl();
  const [resetOpen, setResetOpen] = useState(false);
  const [resetEmail, setResetEmail] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [resetPassword, setResetPassword] = useState("");
  const [resetStatus, setResetStatus] = useState<"idle" | "sending" | "ready" | "saving" | "done" | "error">("idle");
  const [resetError, setResetError] = useState<string | null>(null);
  const [personalMode, setPersonalMode] = useState<boolean | null>(null);
  const [guestLoading, setGuestLoading] = useState(false);

  useEffect(() => {
    const checkPersonalMode = async () => {
      try {
        const res = await fetch(`${apiBase}/api/system/status`);
        if (!res.ok) return;
        const data = await res.json();
        setPersonalMode(Boolean(data.personal_mode));
      } catch {
        setPersonalMode(null);
      }
    };
    checkPersonalMode();
  }, [apiBase]);

  useEffect(() => {
    if (auth.user) {
      router.replace("/dashboard");
    }
  }, [auth.user, router]);

  const handleLogin = async (data: { username: string; password: string }) => {
    try {
      setLoading(true);
      setError(null);
      await auth.login(data.username, data.password);
      notifications.show({
        title: "Login Successful",
        message: "Welcome back!",
        color: "green",
      });
      router.push("/dashboard");
    } catch (error: any) {
      setError(error.message || "Invalid credentials");
      notifications.show({
        title: "Login Failed",
        message: error.message || "Invalid credentials",
        color: "red",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (data: { username: string; email: string; password: string }) => {
    try {
      setLoading(true);
      setError(null);
      await auth.register(data.username, data.email, data.password);
      notifications.show({
        title: "Account Created",
        message: "You're signed in.",
        color: "green",
      });
      router.push("/dashboard");
    } catch (error: any) {
      setError(error.message || "Registration failed");
      notifications.show({
        title: "Registration Failed",
        message: error.message || "Registration failed",
        color: "red",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleResetRequest = async () => {
    if (!resetEmail.trim()) {
      setResetError("Email is required.");
      return;
    }
    setResetStatus("sending");
    setResetError(null);
    try {
      const res = await fetch(`${apiBase}/api/auth/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ email: resetEmail.trim() }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.detail || "Reset request failed.");
      }
      setResetToken(data.reset_token || "");
      setResetStatus("ready");
      notifications.show({
        title: "Reset token issued",
        message: "Use the token to set a new password.",
        color: "green",
      });
    } catch (err: any) {
      setResetStatus("error");
      setResetError(err?.message || "Reset request failed.");
    }
  };

  const handleResetPassword = async () => {
    if (!resetToken.trim() || !resetPassword.trim()) {
      setResetError("Token and new password are required.");
      return;
    }
    setResetStatus("saving");
    setResetError(null);
    try {
      const res = await fetch(`${apiBase}/api/auth/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ token: resetToken.trim(), new_password: resetPassword }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.detail || "Password reset failed.");
      }
      setResetStatus("done");
      notifications.show({
        title: "Password reset",
        message: "You can now sign in with the new password.",
        color: "green",
      });
    } catch (err: any) {
      setResetStatus("error");
      setResetError(err?.message || "Password reset failed.");
    }
  };

  const handleGuest = async () => {
    setGuestLoading(true);
    setError(null);
    try {
      const user = await auth.refreshUser();
      if (!user) {
        throw new Error("Personal mode is not available on this server.");
      }
      router.push("/dashboard");
    } catch (err: any) {
      setError(err?.message || "Personal mode is not available.");
    } finally {
      setGuestLoading(false);
    }
  };

  return (
    <div style={{ 
      minHeight: "100vh", 
      display: "flex", 
      alignItems: "center", 
      justifyContent: "center",
      background: "var(--mantine-color-dark-9)"
    }}>
      <Card withBorder radius="md" p="xl" w={400}>
        <Stack gap="md">
          <Group gap="xs" justify="center">
            <Title order={2}>MyCasa Pro</Title>
          </Group>
          <Text c="dimmed" size="sm" ta="center">
            {mode === "login" ? "Sign in to your account" : "Create your account"}
          </Text>
          
          {mode === "login" ? (
            <LoginForm onSubmit={handleLogin} error={error || undefined} loading={loading} />
          ) : (
            <RegisterForm onSubmit={handleRegister} error={error || undefined} loading={loading} />
          )}
          {mode === "login" && (
            <Button variant="subtle" onClick={() => setResetOpen(true)}>
              Forgot password?
            </Button>
          )}
          {mode === "login" && personalMode && (
            <>
              <Divider />
              <Button variant="light" onClick={handleGuest} loading={guestLoading}>
                Continue without an account
              </Button>
              <Text size="xs" c="dimmed" ta="center">
                Personal mode stores everything locally and can be personalized later in Settings.
              </Text>
            </>
          )}
          <Button
            variant="subtle"
            onClick={() => setMode(mode === "login" ? "register" : "login")}
          >
            {mode === "login" ? "Create an account" : "Back to sign in"}
          </Button>
        </Stack>
      </Card>
      <Modal opened={resetOpen} onClose={() => setResetOpen(false)} title="Reset password" centered>
        <Stack gap="sm">
          <Text size="sm" c="dimmed">
            Enter your email to generate a reset token, then set a new password.
          </Text>
          <TextInput
            label="Email"
            placeholder="you@example.com"
            value={resetEmail}
            onChange={(e) => setResetEmail(e.currentTarget.value)}
          />
          <Group grow>
            <Button onClick={handleResetRequest} loading={resetStatus === "sending"}>
              Get reset token
            </Button>
          </Group>
          <TextInput
            label="Reset token"
            placeholder="Paste token here"
            value={resetToken}
            onChange={(e) => setResetToken(e.currentTarget.value)}
          />
          <PasswordInput
            label="New password"
            value={resetPassword}
            onChange={(e) => setResetPassword(e.currentTarget.value)}
          />
          {resetError && (
            <Alert color="red" title="Reset failed">
              {resetError}
            </Alert>
          )}
          <Button onClick={handleResetPassword} loading={resetStatus === "saving"}>
            Set new password
          </Button>
          {resetStatus === "done" && (
            <Alert color="green" title="Password updated">
              You can now sign in with the new password.
            </Alert>
          )}
        </Stack>
      </Modal>
    </div>
  );
}
