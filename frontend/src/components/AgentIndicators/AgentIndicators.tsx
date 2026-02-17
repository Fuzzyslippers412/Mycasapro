"use client";

import { useState, useEffect } from "react";
import {
  Group,
  Tooltip,
  Avatar,
  Box,
  Text,
  Popover,
  Stack,
  Badge,
  Paper,
  Indicator,
} from "@mantine/core";
import { useSystemStatus } from "@/lib/useSystemStatus";

interface AgentStatus {
  id: string;
  name: string;
  displayName: string;
  state: "running" | "active" | "idle" | "error" | "offline";
  currentTask?: string;
  pendingTasks: number;
}

// Agent definitions with display names
const AGENT_DEFS: { id: string; displayName: string; name: string; emoji: string }[] = [
  { id: "manager", displayName: "Galidima", name: "Manager", emoji: "👔" },
  { id: "finance", displayName: "Mamadou", name: "Finance", emoji: "💰" },
  { id: "maintenance", displayName: "Ousmane", name: "Maintenance", emoji: "🔧" },
  { id: "security", displayName: "Aïcha", name: "Security", emoji: "🛡️" },
  { id: "contractors", displayName: "Malik", name: "Contractors", emoji: "👷" },
  { id: "projects", displayName: "Zainab", name: "Projects", emoji: "📋" },
  { id: "janitor", displayName: "Salimata", name: "Janitor", emoji: "🧹" },
  { id: "mail", displayName: "Amina", name: "Mail", emoji: "✉️" },
  { id: "backup", displayName: "Backup", name: "Backup", emoji: "🗄️" },
];

// Avatar images (grayscale portraits)
const AVATAR_IMAGES: Record<string, string> = {
  manager: "https://images.unsplash.com/photo-1560250097-0b93528c311a?w=80&h=80&fit=crop&crop=face&sat=-100",
  finance: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=80&h=80&fit=crop&crop=face&sat=-100",
  maintenance: "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=80&h=80&fit=crop&crop=face&sat=-100",
  security: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=80&h=80&fit=crop&crop=face&sat=-100",
  contractors: "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=80&h=80&fit=crop&crop=face&sat=-100",
  projects: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=80&h=80&fit=crop&crop=face&sat=-100",
  janitor: "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=80&h=80&fit=crop&crop=face&sat=-100",
  mail: "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=80&h=80&fit=crop&crop=face&sat=-100",
  backup: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=80&h=80&fit=crop&crop=face&sat=-100",
};

const STATUS_COLORS: Record<string, string> = {
  running: "#22c55e",
  active: "#22c55e",
  idle: "#6366f1",
  error: "#ef4444",
  offline: "#6b7280",
};

function AgentDot({ agent, onHover }: { agent: AgentStatus; onHover?: () => void }) {
  const [opened, setOpened] = useState(false);
  const color = STATUS_COLORS[agent.state] || "#6b7280";
  const isActive = agent.state === "running" || agent.state === "active";
  const hasIssue = agent.state === "error";
  const hasPending = agent.pendingTasks > 0;

  return (
    <Popover 
      opened={opened} 
      onChange={setOpened}
      position="bottom"
      withArrow
      shadow="lg"
      radius="md"
    >
      <Popover.Target>
        <Box
          onMouseEnter={() => setOpened(true)}
          onMouseLeave={() => setOpened(false)}
          style={{ cursor: "pointer", position: "relative" }}
        >
          <Indicator
            inline
            processing={isActive}
            color={hasIssue ? "red" : hasPending ? "orange" : "transparent"}
            size={hasPending || hasIssue ? 8 : 0}
            offset={2}
            position="top-end"
          >
            <Avatar
              src={AVATAR_IMAGES[agent.id]}
              size={32}
              radius="xl"
              style={{
                border: `2px solid ${color}`,
                filter: agent.state === "offline" ? "grayscale(100%) brightness(0.7)" : "grayscale(40%)",
                opacity: agent.state === "offline" ? 0.5 : 1,
                boxShadow: isActive ? `0 0 12px ${color}60` : undefined,
                transition: "all 0.2s ease",
              }}
            />
          </Indicator>
          
          {/* Pulse ring for active agents */}
          {isActive && (
            <Box
              style={{
                position: "absolute",
                inset: -3,
                borderRadius: "50%",
                border: `1.5px solid ${color}`,
                animation: "agentPulse 2s infinite",
                opacity: 0.4,
                pointerEvents: "none",
              }}
            />
          )}
        </Box>
      </Popover.Target>

      <Popover.Dropdown
        style={{
          background: "rgba(25, 25, 30, 0.98)",
          border: "1px solid rgba(255,255,255,0.1)",
          backdropFilter: "blur(12px)",
        }}
      >
        <Stack gap="xs" miw={180}>
          <Group gap="sm">
            <Avatar
              src={AVATAR_IMAGES[agent.id]}
              size={40}
              radius="xl"
              style={{
                border: `2px solid ${color}`,
                filter: "grayscale(20%)",
              }}
            />
            <Box>
              <Text size="sm" fw={600} c="white">
                {agent.displayName}
              </Text>
              <Text size="xs" c="dimmed">
                {agent.name}
              </Text>
            </Box>
          </Group>

          <Box
            style={{
              height: 1,
              background: "rgba(255,255,255,0.08)",
            }}
          />

          <Group justify="space-between">
            <Text size="xs" c="dimmed">Status</Text>
            <Badge
              size="xs"
              variant="dot"
              color={agent.state === "running" ? "green" : agent.state === "error" ? "red" : agent.state === "idle" ? "blue" : "gray"}
            >
              {agent.state.charAt(0).toUpperCase() + agent.state.slice(1)}
            </Badge>
          </Group>

          {agent.pendingTasks > 0 && (
            <Group justify="space-between">
              <Text size="xs" c="dimmed">Pending</Text>
              <Badge size="xs" variant="light" color="orange">
                {agent.pendingTasks} tasks
              </Badge>
            </Group>
          )}

          {agent.currentTask && (
            <Paper p="xs" radius="sm" bg="rgba(0,0,0,0.3)">
              <Text size="xs" c="dimmed" mb={2}>Current task:</Text>
              <Text size="xs" c="white" lineClamp={2}>
                {agent.currentTask}
              </Text>
            </Paper>
          )}
        </Stack>
      </Popover.Dropdown>

      <style>{`
        @keyframes agentPulse {
          0%, 100% { transform: scale(1); opacity: 0.4; }
          50% { transform: scale(1.15); opacity: 0.1; }
        }
      `}</style>
    </Popover>
  );
}

export function AgentIndicators() {
  const { agents: agentStates, agentDetails, isConnected } = useSystemStatus();
  const [agents, setAgents] = useState<AgentStatus[]>([]);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!isConnected) {
      // Backend offline - all agents offline
      setAgents(
        AGENT_DEFS.map((def) => ({
          id: def.id,
          name: def.name,
          displayName: def.displayName,
          state: "offline" as const,
          pendingTasks: 0,
        }))
      );
      return;
    }

    // Map from unified hook data
    const agentStatuses: AgentStatus[] = AGENT_DEFS.map((def) => {
      const detail = agentDetails[def.id];
      const rawState = detail?.status || agentStates[def.id];
      const state =
        rawState === "running" || rawState === "active" || rawState === "busy"
          ? "running"
          : rawState === "available" || rawState === "idle"
            ? "idle"
            : rawState === "error"
              ? "error"
              : "offline";
      return {
        id: def.id,
        name: def.name,
        displayName: def.displayName,
        state,
        pendingTasks: detail?.pendingTasks ?? 0,
      };
    });

    setAgents(agentStatuses);
  }, [agentDetails, agentStates, isConnected]);

  if (!mounted) {
    // SSR placeholder
    return (
      <Group gap={6}>
        {AGENT_DEFS.map((def) => (
          <Box
            key={def.id}
            w={32}
            h={32}
            style={{
              borderRadius: "50%",
              background: "rgba(255,255,255,0.1)",
            }}
          />
        ))}
      </Group>
    );
  }

  const activeCount = agents.filter((a) => a.state === "running").length;
  const errorCount = agents.filter((a) => a.state === "error").length;

  return (
    <Group gap={8}>
      {/* Agent dots */}
      <Group gap={4}>
        {agents.map((agent) => (
          <AgentDot key={agent.id} agent={agent} />
        ))}
      </Group>

      {/* Summary badge */}
      {activeCount > 0 || errorCount > 0 ? (
        <Box
          px={8}
          py={4}
          style={{
            background: errorCount > 0 
              ? "rgba(239, 68, 68, 0.15)" 
              : "rgba(34, 197, 94, 0.15)",
            borderRadius: 12,
            border: `1px solid ${errorCount > 0 ? "rgba(239, 68, 68, 0.3)" : "rgba(34, 197, 94, 0.3)"}`,
          }}
        >
          <Text size="xs" fw={500} c={errorCount > 0 ? "red.4" : "green.4"}>
            {errorCount > 0 
              ? `${errorCount} error${errorCount > 1 ? "s" : ""}`
              : `${activeCount} active`
            }
          </Text>
        </Box>
      ) : null}
    </Group>
  );
}
