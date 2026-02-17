"use client";

import { useState, useEffect } from "react";
import { getApiBaseUrl } from "@/lib/api";
import {
  Modal,
  Stack,
  Text,
  Progress,
  Group,
  ThemeIcon,
  Box,
  Paper,
  Badge,
  Center,
  Loader,
} from "@mantine/core";
import {
  IconCoin,
  IconTool,
  IconUsers,
  IconFolders,
  IconShield,
  IconDatabase,
  IconCheck,
  IconRocket,
  IconSparkles,
} from "@tabler/icons-react";

const API_URL = getApiBaseUrl();

interface Agent {
  id: string;
  name: string;
  icon: React.ElementType;
  color: string;
  description: string;
}

const DEFAULT_AGENTS: Agent[] = [
  { id: "finance", name: "Finance Manager", icon: IconCoin, color: "green", description: "Portfolio & bills" },
  { id: "maintenance", name: "Maintenance", icon: IconTool, color: "blue", description: "Home tasks" },
  { id: "contractors", name: "Contractors", icon: IconUsers, color: "orange", description: "Service providers" },
  { id: "security", name: "Security", icon: IconShield, color: "red", description: "Threat monitoring" },
  { id: "janitor", name: "Janitor", icon: IconDatabase, color: "gray", description: "System cleanup" },
  { id: "projects", name: "Projects", icon: IconFolders, color: "indigo", description: "Project oversight" },
];

const AGENT_META: Record<string, Agent> = DEFAULT_AGENTS.reduce((acc, agent) => {
  acc[agent.id] = agent;
  return acc;
}, {} as Record<string, Agent>);

interface LaunchModalProps {
  opened: boolean;
  onClose: () => void;
  onComplete: (success: boolean) => void;
}

export function LaunchModal({ opened, onClose, onComplete }: LaunchModalProps) {
  const [phase, setPhase] = useState<"starting" | "launching" | "complete" | "error">("starting");
  const [currentAgentIndex, setCurrentAgentIndex] = useState(-1);
  const [agentStatuses, setAgentStatuses] = useState<Record<string, "waiting" | "launching" | "online" | "error">>({});
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState("Initializing system...");
  const [agents, setAgents] = useState<Agent[]>(DEFAULT_AGENTS);
  const [agentCounts, setAgentCounts] = useState({ total: 0, active: 0 });
  const [hasMonitorData, setHasMonitorData] = useState(false);

  useEffect(() => {
    if (!opened) {
      // Reset state when closed
      setPhase("starting");
      setCurrentAgentIndex(-1);
      setAgentStatuses({});
      setProgress(0);
      setMessage("Initializing system...");
      setAgents(DEFAULT_AGENTS);
      setAgentCounts({ total: 0, active: 0 });
      setHasMonitorData(false);
      return;
    }

    let cancelled = false;
    const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

    const fetchMonitor = async () => {
      try {
        const res = await fetch(`${API_URL}/api/system/monitor`);
        if (!res.ok) return null;
        return await res.json();
      } catch (e) {
        return null;
      }
    };

    const buildAgentList = (processes: any[]) => {
      if (!processes || processes.length === 0) return DEFAULT_AGENTS;
      return processes.map((proc: any) => {
        const meta = AGENT_META[proc.id];
        if (meta) return meta;
        return {
          id: proc.id,
          name: proc.name || proc.id,
          icon: IconRocket,
          color: "gray",
          description: "Agent",
        };
      });
    };

    const applyMonitor = (monitor: any, launching: boolean) => {
      if (!monitor) return { total: 0, active: 0, running: false, hasData: false };
      setHasMonitorData(true);
      const processes = monitor.processes || [];
      if (processes.length > 0) {
        setAgents(buildAgentList(processes));
      }

      const active = monitor.resources?.agents_active ?? processes.filter((p: any) => p.state === "running").length;
      const total = monitor.resources?.agents_total ?? processes.length;
      setAgentCounts({ total, active });

      const nextStatuses: Record<string, "waiting" | "launching" | "online" | "error"> = {};
      processes.forEach((proc: any) => {
        if (proc.state === "running") {
          nextStatuses[proc.id] = "online";
        } else if (launching && proc.state === "idle") {
          nextStatuses[proc.id] = "launching";
        } else {
          nextStatuses[proc.id] = "waiting";
        }
      });
      setAgentStatuses(nextStatuses);

      const progressValue = total > 0
        ? Math.round((active / total) * 100)
        : (monitor.running ? 100 : 0);
      setProgress(progressValue);

      return { total, active, running: Boolean(monitor.running), hasData: true };
    };

    // Start the launch sequence
    const startLaunch = async () => {
      try {
        setPhase("launching");
        setProgress(5);
        setMessage("Connecting to backend...");

        const initial = await fetchMonitor();
        if (cancelled) return;
        applyMonitor(initial, false);

        const res = await fetch(`${API_URL}/api/system/startup`, { method: "POST" });
        const payload = res.ok ? await res.json() : null;
        if (!res.ok || payload?.success === false) {
          throw new Error(payload?.error || "Backend returned error");
        }

        window.dispatchEvent(new CustomEvent("mycasa-system-sync"));
        setMessage(payload?.already_running ? "System already running — syncing status..." : "Starting agents...");

        let status = { total: 0, active: 0, running: false, hasData: false };
        for (let i = 0; i < 6; i++) {
          const monitor = await fetchMonitor();
          if (cancelled) return;
          status = applyMonitor(monitor, true);
          const done = status.running && (status.total === 0 || status.active >= status.total);
          if (done) break;
          await delay(500);
        }

        setProgress(100);
        setPhase("complete");
        if (!status.hasData) {
          setMessage("System online (status pending)");
        } else if (status.total === 0) {
          setMessage("System online (no agents enabled)");
        } else if (status.active >= status.total) {
          setMessage("All enabled agents are online");
        } else {
          setMessage(`System online (${status.active}/${status.total} agents running)`);
        }

        await delay(1200);
        onComplete(true);
        
      } catch (error) {
        setPhase("error");
        setMessage("Failed to launch system");
        
        // Still close after error
        await delay(2000);
        onComplete(false);
      }
    };

    // Small delay before starting
    setTimeout(startLaunch, 500);
    return () => {
      cancelled = true;
    };
  }, [opened, onComplete]);

  const getAgentStatusIcon = (status: "waiting" | "launching" | "online" | "error") => {
    switch (status) {
      case "waiting":
        return null;
      case "launching":
        return <Loader size={14} color="yellow" />;
      case "online":
        return <IconCheck size={16} color="var(--mantine-color-green-6)" />;
      case "error":
        return <Text size="xs" c="red">✗</Text>;
    }
  };

  const getAgentStatusColor = (status: "waiting" | "launching" | "online" | "error") => {
    switch (status) {
      case "waiting": return "gray";
      case "launching": return "yellow";
      case "online": return "green";
      case "error": return "red";
    }
  };

  return (
    <Modal
      opened={opened}
      onClose={() => {}}
      centered
      size="lg"
      withCloseButton={false}
      overlayProps={{ blur: 10, opacity: 0.8 }}
      transitionProps={{ transition: "scale-y", duration: 300 }}
      styles={{
        content: {
          background: "linear-gradient(180deg, var(--mantine-color-dark-8) 0%, var(--mantine-color-dark-9) 100%)",
          border: "1px solid var(--mantine-color-dark-5)",
        },
      }}
    >
      <Stack gap="xl" py="md">
        {/* Header */}
        <Center>
          <Stack align="center" gap="xs">
            <Box
              style={{
                padding: 16,
                borderRadius: 16,
                background: phase === "complete" 
                  ? "linear-gradient(135deg, #22c55e 0%, #16a34a 100%)"
                  : "linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)",
                transition: "all 0.3s ease",
                boxShadow: phase === "complete" 
                  ? "0 0 30px rgba(34, 197, 94, 0.5)" 
                  : phase === "launching" 
                    ? "0 0 20px rgba(99, 102, 241, 0.5)" 
                    : "none",
              }}
            >
              {phase === "complete" ? (
                <IconSparkles size={40} color="white" />
              ) : (
                <IconRocket size={40} color="white" />
              )}
            </Box>
            <Text size="xl" fw={700} c="white" mt="sm">
              {phase === "complete" ? "System Online" : "Launching MyCasa Pro"}
            </Text>
            <Text size="sm" c="dimmed">
              {message}
            </Text>
          </Stack>
        </Center>

        {/* Progress Bar */}
        <Progress
          value={progress}
          size="lg"
          radius="xl"
          color={phase === "complete" ? "green" : phase === "error" ? "red" : "violet"}
          animated={phase === "launching"}
          striped={phase === "launching"}
          style={{ transition: "all 0.3s ease" }}
        />

        {/* Agent Grid */}
        <Box
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gap: 12,
          }}
        >
          {agents.map((agent, index) => {
            const status = agentStatuses[agent.id] || "waiting";
            const isActive = index === currentAgentIndex && status === "launching";
            const Icon = agent.icon;

            return (
              <Paper
                key={agent.id}
                p="sm"
                radius="md"
                withBorder
                style={{
                  background: status === "online" 
                    ? "rgba(34, 197, 94, 0.1)"
                    : isActive 
                      ? "rgba(99, 102, 241, 0.1)"
                      : "transparent",
                  borderColor: status === "online"
                    ? "rgba(34, 197, 94, 0.3)"
                    : isActive
                      ? "rgba(99, 102, 241, 0.3)"
                      : "var(--mantine-color-dark-5)",
                  opacity: status === "waiting" ? 0.5 : 1,
                  transition: "all 0.3s ease",
                  boxShadow: status === "online" ? "0 0 15px rgba(34, 197, 94, 0.3)" : "none",
                }}
              >
                <Group justify="space-between" wrap="nowrap">
                  <Group gap="xs" wrap="nowrap">
                    <ThemeIcon
                      size="md"
                      variant={status === "online" ? "filled" : "light"}
                      color={status === "online" ? "green" : agent.color}
                    >
                      <Icon size={16} />
                    </ThemeIcon>
                    <div style={{ minWidth: 0 }}>
                      <Text size="xs" fw={600} truncate c={status === "online" ? "green" : undefined}>
                        {agent.name}
                      </Text>
                      <Text size="xs" c="dimmed" truncate>
                        {agent.description}
                      </Text>
                    </div>
                  </Group>
                  <Box style={{ flexShrink: 0 }}>
                    {getAgentStatusIcon(status) || (
                      <Badge
                        size="xs"
                        variant="dot"
                        color={getAgentStatusColor(status)}
                      />
                    )}
                  </Box>
                </Group>
              </Paper>
            );
          })}
        </Box>

        {/* Status Message */}
        {phase === "complete" && (
          <Center>
            <Badge color="green" variant="light" size="lg">
              {!hasMonitorData
                ? "✓ System online"
                : agentCounts.total === 0
                  ? "✓ System online (no agents enabled)"
                  : `✓ ${agentCounts.active}/${agentCounts.total} agents online`}
            </Badge>
          </Center>
        )}

        {phase === "error" && (
          <Center>
            <Badge color="red" variant="light" size="lg">
              ✗ Launch failed - check backend
            </Badge>
          </Center>
        )}
      </Stack>
    </Modal>
  );
}
