"use client";

import { useState, useEffect } from "react";
import {
  Box,
  Stack,
  Text,
  Loader,
  Progress,
  Paper,
  ThemeIcon,
  Group,
  Button,
} from "@mantine/core";
import { IconRocket, IconAlertCircle } from "@tabler/icons-react";
import { MyCasaLogo } from "./MyCasaLogo";
import { getApiBaseUrl } from "@/lib/api";

interface LaunchScreenProps {
  onLaunch: () => void;
}

export function LaunchScreen({ onLaunch }: LaunchScreenProps) {
  const [status, setStatus] = useState<"checking" | "ready" | "offline">("checking");
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState("Initializing MyCasa Pro...");
  const [backendReady, setBackendReady] = useState(false);

  useEffect(() => {
    const checkBackend = async () => {
      try {
        setMessage("Checking backend connection...");
        setProgress(25);

        // Add timeout to prevent hanging
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);

        const res = await fetch(`${getApiBaseUrl()}/status`, {
          signal: controller.signal
        });
        clearTimeout(timeoutId);

        if (!res.ok) {
          setStatus("offline");
          setMessage("Backend returned error");
          setProgress(0);
          return;
        }

        const data = await res.json();
        // Check if backend is actually responding with valid data
        if (!data || typeof data !== 'object') {
          setStatus("offline");
          setMessage("Backend not responding correctly");
          setProgress(0);
          return;
        }

        setProgress(100);
        setMessage("System ready to launch");
        setStatus("ready");
        setBackendReady(true);

      } catch (error) {
        setStatus("offline");
        if ((error as Error).name === 'AbortError') {
          setMessage("Backend connection timeout");
        } else {
          setMessage("Backend not running");
        }
        setProgress(0);
      }
    };

    checkBackend();
  }, [onLaunch]);

  const handleManualLaunch = () => {
    onLaunch();
  };

  return (
    <Box
      style={{
        position: "fixed",
        inset: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "linear-gradient(135deg, #1a1b1e 0%, #2c2e33 100%)",
        zIndex: 9999,
      }}
    >
      <Paper
        p="xl"
        radius="lg"
        withBorder
        style={{
          width: "90%",
          maxWidth: 500,
          background: "rgba(255, 255, 255, 0.05)",
          backdropFilter: "blur(10px)",
          border: "1px solid rgba(255, 255, 255, 0.1)",
        }}
      >
        <Stack align="center" gap="xl">
          {/* Logo */}
          <Box
            style={{
              padding: 20,
              borderRadius: 16,
              background: "linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)",
            }}
          >
            <MyCasaLogo size={64} />
          </Box>

          {/* Title */}
          <Stack align="center" gap="xs">
            <Text size="xl" fw={700} c="white">
              MyCasa Pro
            </Text>
            <Text size="sm" c="dimmed">
              Home Operating System
            </Text>
          </Stack>

          {/* Status */}
          {status === "checking" && (
            <>
              <Stack align="center" gap="md" style={{ width: "100%" }}>
                <Group gap="sm">
                  <Loader size="sm" color="violet" />
                  <Text size="sm" c="white">
                    {message}
                  </Text>
                </Group>
                <Progress value={progress} size="sm" radius="xl" style={{ width: "100%" }} />
              </Stack>
            </>
          )}

          {status === "ready" && backendReady && (
            <>
              <Stack align="center" gap="md">
                <ThemeIcon size="xl" color="green" variant="light">
                  <IconRocket size={24} />
                </ThemeIcon>
                <Text size="sm" c="green" fw={600}>
                  {message}
                </Text>
                <Button
                  size="lg"
                  variant="gradient"
                  gradient={{ from: "indigo", to: "violet" }}
                  onClick={handleManualLaunch}
                  leftSection={<IconRocket size={20} />}
                >
                  Launch System
                </Button>
              </Stack>
            </>
          )}

          {status === "offline" && (
            <>
              <Stack align="center" gap="md">
                <ThemeIcon size="xl" color="red" variant="light">
                  <IconAlertCircle size={24} />
                </ThemeIcon>
                <Stack align="center" gap={4}>
                  <Text size="sm" c="red" fw={600}>
                    {message}
                  </Text>
                  <Text size="xs" c="dimmed" ta="center">
                    Start the backend server to continue
                  </Text>
                  <Text size="xs" c="dimmed" ta="center" style={{ fontFamily: "monospace" }}>
                    python -m uvicorn backend.api.main:app --reload
                  </Text>
                </Stack>
                <Button
                  variant="light"
                  color="violet"
                  onClick={handleManualLaunch}
                  mt="md"
                >
                  Continue Anyway
                </Button>
              </Stack>
            </>
          )}
        </Stack>
      </Paper>
    </Box>
  );
}
