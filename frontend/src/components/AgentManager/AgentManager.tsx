"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch, isNetworkError } from "@/lib/api";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  rectSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import {
  Box,
  Card,
  Group,
  Text,
  Avatar,
  Modal,
  TextInput,
  Select,
  Textarea,
  Button,
  Tabs,
  Stack,
  ActionIcon,
  Tooltip,
  Paper,
  SimpleGrid,
  Divider,
  Loader,
  Collapse,
  ScrollArea,
  Badge,
} from "@mantine/core";
import {
  IconSettings,
  IconX,
  IconCheck,
  IconGripVertical,
  IconPlayerPlay,
  IconPlayerPause,
  IconChevronDown,
  IconChevronUp,
  IconTerminal2,
  IconDotsVertical,
  IconActivity,
  IconMessageCircle,
} from "@tabler/icons-react";
import { AgentActivityDashboard } from "../AgentActivityDashboard";
import { notifications } from "@mantine/notifications";
import { sendAgentChat, sendManagerChat } from "@/lib/api";
import { useAgentContext } from "@/lib/AgentContext";

const FLEET_ID_ALIASES: Record<string, string> = {
  security: "security-manager",
  backup: "backup-recovery",
  mail: "mail-skill",
};

const resolveFleetId = (agentId: string) => FLEET_ID_ALIASES[agentId] || agentId;

interface Agent {
  id: string;
  name: string;
  displayName: string;
  role: string;
  model: string;
  thinking: string;
  status: "active" | "idle" | "error" | "offline";
  color: string;
  description: string;
  pendingTasks: number;
  errorCount: number;
  alwaysOn?: boolean;
}

interface ActivityLog {
  timestamp: string;
  action: string;
  details?: string;
}

// API functions
async function fetchSystemMonitor(): Promise<any> {
  try {
    return await apiFetch<any>("/api/system/monitor");
  } catch (e) {
    if (!isNetworkError(e)) {
      console.error("Failed to fetch system monitor:", e);
    }
  }
  return null;
}

async function fetchFleetAgents(): Promise<any[]> {
  try {
    const data = await apiFetch<any>("/api/fleet/agents");
    return data.agents || [];
  } catch (e) {
    if (!isNetworkError(e)) {
      console.error("Failed to fetch fleet agents:", e);
    }
  }
  return [];
}

async function fetchAgentActivity(agentId: string): Promise<ActivityLog[]> {
  try {
    const data = await apiFetch<any>(`/api/agents/${agentId}/activity`);
    return data.activity || [];
  } catch (e) {
    // API may not exist yet - return empty
  }
  return [];
}

async function fetchAgentWorkspace(agentId: string): Promise<Record<string, string>> {
  try {
    const data = await apiFetch<any>(`/api/memory/agents/${agentId}/workspace`);
    return data.files || {};
  } catch (e) {
    if (!isNetworkError(e)) {
      console.error("Failed to fetch workspace:", e);
    }
  }
  return {};
}

async function saveWorkspaceFile(agentId: string, filename: string, content: string): Promise<boolean> {
  try {
    await apiFetch<any>(`/api/memory/agents/${agentId}/workspace/${filename}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    });
    return true;
  } catch (e) {
    if (!isNetworkError(e)) {
      console.error("Failed to save workspace:", e);
    }
    return false;
  }
}

async function sendMessageToAgent(agentId: string, message: string, userId?: number | null): Promise<string> {
  try {
    const key = `mycasa_agent_manager_conversation_${agentId}:${userId ?? "anon"}`;
    const storedConversation = typeof window !== "undefined" ? localStorage.getItem(key) || undefined : undefined;
    const data = agentId === "manager"
      ? await sendManagerChat(message, storedConversation)
      : await sendAgentChat(agentId, message, storedConversation);
    if (data?.conversation_id && typeof window !== "undefined") {
      localStorage.setItem(key, data.conversation_id);
    }
    return data.response || "No response.";
  } catch (e) {
    console.error("Failed to send message:", e);
  }
  return "Error: Could not reach agent.";
}

async function startAgent(agentId: string): Promise<boolean> {
  try {
    await apiFetch<any>(`/api/system/agents/${agentId}/start`, { method: "POST" });
    return true;
  } catch (e) {
    return false;
  }
}

async function stopAgent(agentId: string): Promise<boolean> {
  try {
    await apiFetch<any>(`/api/system/agents/${agentId}/stop`, { method: "POST" });
    return true;
  } catch (e) {
    return false;
  }
}

async function updateAgentConfig(agent: Agent): Promise<boolean> {
  const payload = {
    default_model: agent.model,
    max_tier: THINKING_TO_TIER[agent.thinking] || "medium",
  };
  try {
    await apiFetch<any>(`/api/fleet/agents/${resolveFleetId(agent.id)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return true;
  } catch (e) {
    console.error("Failed to update agent config:", e);
    return false;
  }
}

// Agent definitions with Afro-Arabic-Latino names - these are always visible
const AGENT_DEFINITIONS: {
  id: string;
  displayName: string;
  name: string;
  description: string;
  color: string;
  alwaysOn?: boolean;
}[] = [
  {
    id: "manager",
    displayName: "Galidima",
    name: "Manager",
    description: "Your AI home manager - coordinates all agents",
    color: "violet",
    alwaysOn: true,
  },
  {
    id: "finance",
    displayName: "Mamadou",
    name: "Finance Manager",
    description: "Bills, budgets, portfolio tracking",
    color: "teal",
  },
  {
    id: "maintenance",
    displayName: "Ousmane",
    name: "Maintenance Manager",
    description: "Home tasks and schedules",
    color: "blue",
  },
  {
    id: "security",
    displayName: "Aïcha",
    name: "Security Manager",
    description: "Incidents and monitoring",
    color: "red",
  },
  {
    id: "contractors",
    displayName: "Malik",
    name: "Contractors Manager",
    description: "Service provider directory",
    color: "orange",
  },
  {
    id: "projects",
    displayName: "Zainab",
    name: "Projects Manager",
    description: "Home improvement tracking",
    color: "grape",
  },
  {
    id: "janitor",
    displayName: "Salimata",
    name: "Janitor",
    description: "System health, audits, action logging",
    color: "cyan",
    alwaysOn: true,
  },
  {
    id: "mail",
    displayName: "Amina",
    name: "Mail Agent",
    description: "Inbox triage and communications",
    color: "violet",
  },
  {
    id: "backup",
    displayName: "Backup",
    name: "Backup & Recovery",
    description: "Backups, restore drills, retention",
    color: "gray",
  },
];

const MODEL_OPTIONS = [
  { value: "claude-opus-4", label: "Claude Opus 4" },
  { value: "claude-sonnet-4", label: "Claude Sonnet 4" },
  { value: "claude-haiku-3", label: "Claude Haiku 3" },
  { value: "gpt-4o", label: "GPT-4o" },
];

const THINKING_OPTIONS = [
  { value: "off", label: "Off" },
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
];

const THINKING_TO_TIER: Record<string, string> = {
  off: "simple",
  low: "medium",
  medium: "complex",
  high: "reasoning",
};

const TIER_TO_THINKING: Record<string, string> = {
  simple: "off",
  medium: "low",
  complex: "medium",
  reasoning: "high",
};

const WORKSPACE_FILES = ["AGENTS", "SOUL", "IDENTITY", "USER", "TOOLS", "HEARTBEAT", "MEMORY"];

// Realistic portrait-style avatars (grayscale)
const AVATAR_IMAGES: Record<string, string> = {
  manager: "https://images.unsplash.com/photo-1560250097-0b93528c311a?w=200&h=200&fit=crop&crop=face&sat=-100&con=1.1",
  finance: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=200&h=200&fit=crop&crop=face&sat=-100&con=1.1",
  maintenance: "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=200&h=200&fit=crop&crop=face&sat=-100&con=1.1",
  security: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=200&h=200&fit=crop&crop=face&sat=-100&con=1.1",
  contractors: "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=200&h=200&fit=crop&crop=face&sat=-100&con=1.1",
  projects: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200&h=200&fit=crop&crop=face&sat=-100&con=1.1",
  janitor: "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=200&h=200&fit=crop&crop=face&sat=-100&con=1.1",
  mail: "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=200&h=200&fit=crop&crop=face&sat=-100&con=1.1",
  backup: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=200&h=200&fit=crop&crop=face&sat=-100&con=1.1",
};

// Sortable Agent Card Component - Premium Design
function SortableAgentCard({
  agent,
  onSelect,
  onToggleStatus,
  onChatWithAgent,
  onViewActivity,
  activity,
  activityLoading,
}: {
  agent: Agent;
  onSelect: () => void;
  onToggleStatus: () => void;
  onChatWithAgent: () => void;
  onViewActivity: () => void;
  activity: ActivityLog[];
  activityLoading: boolean;
}) {
  const [isHovered, setIsHovered] = useState(false);
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: agent.id });

  const isActive = agent.status === "active";
  const isError = agent.status === "error";
  const isOffline = agent.status === "offline";
  
  // Status colors
  const statusColor = isActive ? "#22c55e" : isError ? "#ef4444" : isOffline ? "#4b5563" : "#fbbf24";
  const statusGlow = isActive ? "0 0 20px rgba(34,197,94,0.3)" : isError ? "0 0 20px rgba(239,68,68,0.3)" : "none";

  const style = {
    transform: CSS.Transform.toString(transform),
    transition: "transform 0.2s ease, box-shadow 0.2s ease",
    opacity: isDragging ? 0.9 : 1,
    zIndex: isDragging ? 1000 : 1,
  };

  // Format timestamp to relative time
  const formatTime = (ts: string) => {
    try {
      const date = new Date(ts);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      if (diffMins < 1) return "just now";
      if (diffMins < 60) return `${diffMins}m ago`;
      const diffHours = Math.floor(diffMins / 60);
      if (diffHours < 24) return `${diffHours}h ago`;
      return `${Math.floor(diffHours / 24)}d ago`;
    } catch {
      return "";
    }
  };

  return (
    <Card
      ref={setNodeRef}
      style={style}
      padding={0}
      radius="lg"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      styles={{
        root: {
          background: isHovered 
            ? "linear-gradient(165deg, rgba(40, 40, 48, 0.98) 0%, rgba(28, 28, 35, 0.98) 100%)"
            : "linear-gradient(165deg, rgba(32, 32, 40, 0.95) 0%, rgba(24, 24, 30, 0.95) 100%)",
          border: `1px solid ${isHovered ? "rgba(255,255,255,0.12)" : "rgba(255,255,255,0.06)"}`,
          boxShadow: isDragging 
            ? "0 20px 40px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.1)"
            : isHovered
              ? "0 8px 32px rgba(0,0,0,0.4), 0 0 0 1px rgba(255,255,255,0.08)"
              : "0 4px 16px rgba(0,0,0,0.3)",
          overflow: "hidden",
          cursor: "pointer",
          transition: "all 0.2s ease",
        }
      }}
    >
      {/* Main clickable area - targets agent in console */}
      <Box onClick={onChatWithAgent}>
        {/* Status indicator bar at top */}
        <Box
          style={{
            height: 3,
            background: `linear-gradient(90deg, ${statusColor} 0%, ${statusColor}88 100%)`,
            boxShadow: statusGlow,
          }}
        />

        {/* Header */}
        <Group justify="space-between" px={20} pt={16} pb={12}>
          <Group gap={14}>
            {/* Drag handle - subtle */}
            <Box
              {...attributes}
              {...listeners}
              style={{ 
                cursor: "grab", 
                opacity: isHovered ? 0.5 : 0.2, 
                display: "flex", 
                alignItems: "center",
                transition: "opacity 0.2s",
              }}
              onClick={(e) => e.stopPropagation()}
            >
              <IconGripVertical size={16} />
            </Box>
            
            {/* Avatar with elegant status ring */}
            <Box style={{ position: "relative" }}>
              <Avatar
                src={AVATAR_IMAGES[agent.id]}
                size={44}
                radius="xl"
                style={{
                  border: `2.5px solid ${statusColor}`,
                  filter: isOffline ? "grayscale(70%) brightness(0.8)" : "grayscale(20%) contrast(1.05)",
                  opacity: isOffline ? 0.7 : 1,
                  boxShadow: isActive ? `0 0 16px ${statusColor}40` : "none",
                  transition: "all 0.2s ease",
                }}
              />
              {/* Pulse animation for active agents */}
              {isActive && (
                <Box
                  style={{
                    position: "absolute",
                    inset: -4,
                    borderRadius: "50%",
                    border: `2px solid ${statusColor}`,
                    animation: "pulse 2s infinite",
                    opacity: 0.4,
                  }}
                />
              )}
              {isError && (
                <Box
                  style={{
                    position: "absolute",
                    top: -2,
                    right: -2,
                    width: 12,
                    height: 12,
                    borderRadius: "50%",
                    background: "#ef4444",
                    border: "2px solid rgba(24, 24, 30, 1)",
                  }}
                />
              )}
            </Box>
            
            {/* Name and status */}
            <Box>
              <Text size="md" fw={600} c="white" lh={1.3}>
                {agent.displayName}
              </Text>
              <Group gap={6} mt={2}>
                <Box
                  style={{
                    width: 6,
                    height: 6,
                    borderRadius: "50%",
                    background: statusColor,
                    boxShadow: isActive ? `0 0 8px ${statusColor}` : "none",
                  }}
                />
                <Text size="xs" c="dimmed" fw={500} tt="uppercase" style={{ letterSpacing: 0.5 }}>
                  {agent.status === "active" ? "Active" : agent.status === "error" ? "Error" : agent.status === "offline" ? "Offline" : "Idle"}
                </Text>
              </Group>
            </Box>
          </Group>

          {/* Action buttons - only show on hover */}
          <Group 
            gap={2} 
            style={{ 
              opacity: isHovered ? 1 : 0, 
              transition: "opacity 0.2s",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <Tooltip label="Full Activity Dashboard" withArrow position="top">
              <ActionIcon
                variant="subtle"
                color="gray"
                size="md"
                radius="md"
                onClick={onViewActivity}
              >
                <IconActivity size={16} />
              </ActionIcon>
            </Tooltip>
            <Tooltip label={isActive ? "Pause Agent" : "Start Agent"} withArrow position="top">
              <ActionIcon
                variant="subtle"
                color="gray"
                size="md"
                radius="md"
                onClick={onToggleStatus}
              >
                {isActive ? <IconPlayerPause size={16} /> : <IconPlayerPlay size={16} />}
              </ActionIcon>
            </Tooltip>
            <Tooltip label="Settings" withArrow position="top">
              <ActionIcon
                variant="subtle"
                color="gray"
                size="md"
                radius="md"
                onClick={onSelect}
              >
                <IconSettings size={16} />
              </ActionIcon>
            </Tooltip>
          </Group>
        </Group>

        {/* Description */}
        <Box px={20} pb={12}>
          <Text size="sm" c="gray.5" lh={1.5}>
            {agent.description}
          </Text>
        </Box>
      </Box>

      {/* Activity feed - always visible */}
      <Box 
        px={20} 
        pb={16}
        style={{ 
          borderTop: "1px solid rgba(255,255,255,0.04)",
          background: "rgba(0,0,0,0.15)",
        }}
      >
        <Group justify="space-between" py={10}>
          <Text size="xs" c="dimmed" fw={600} tt="uppercase" style={{ letterSpacing: 0.8 }}>
            Recent Activity
          </Text>
          {agent.pendingTasks > 0 && (
            <Badge size="xs" variant="light" color="orange" radius="sm">
              {agent.pendingTasks} pending
            </Badge>
          )}
        </Group>
        
        {activityLoading ? (
          <Group gap={8} py={8} justify="center">
            <Loader size="xs" color="gray" />
          </Group>
        ) : activity.length > 0 ? (
          <Stack gap={8}>
            {activity.slice(0, 3).map((log, i) => (
              <Group key={i} gap={10} wrap="nowrap" align="flex-start">
                <Box
                  style={{
                    width: 4,
                    height: 4,
                    borderRadius: "50%",
                    background: i === 0 ? "#22c55e" : i === 1 ? "#6366f1" : "#6b7280",
                    marginTop: 6,
                    flexShrink: 0,
                  }}
                />
                <Box style={{ flex: 1, minWidth: 0 }}>
                  <Text size="xs" c="gray.3" lineClamp={1}>
                    {log.action.replace(/_/g, " ")}
                  </Text>
                </Box>
                <Text size="xs" c="dimmed" style={{ flexShrink: 0, fontSize: 10 }}>
                  {formatTime(log.timestamp)}
                </Text>
              </Group>
            ))}
          </Stack>
        ) : (
          <Text size="xs" c="dimmed" py={8} ta="center" style={{ opacity: 0.5 }}>
            No recent activity
          </Text>
        )}
      </Box>

      {/* CSS for pulse animation */}
      <style>{`
        @keyframes pulse {
          0%, 100% { transform: scale(1); opacity: 0.4; }
          50% { transform: scale(1.1); opacity: 0.1; }
        }
      `}</style>
    </Card>
  );
}

// Settings Modal
function AgentSettingsModal({
  agent,
  opened,
  onClose,
  onSave,
  onToggleStatus,
  defaultTab = "settings",
}: {
  agent: Agent | null;
  opened: boolean;
  onClose: () => void;
  onSave: (agent: Agent) => void;
  onToggleStatus: (agent: Agent) => void;
  defaultTab?: string;
}) {
  const [editedAgent, setEditedAgent] = useState<Agent | null>(null);
  const [activeFile, setActiveFile] = useState("TOOLS");
  const [activeTab, setActiveTab] = useState<string | null>(defaultTab);
  const [fileContent, setFileContent] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState(true);

  // Reset tab when modal opens with new defaultTab
  useEffect(() => {
    if (opened) {
      setActiveTab(defaultTab);
    }
  }, [opened, defaultTab]);

  useEffect(() => {
    if (agent) {
      setEditedAgent({ ...agent });
      fetchAgentWorkspace(agent.id).then((files) => {
        const content: Record<string, string> = {};
        WORKSPACE_FILES.forEach((f) => {
          content[f] = files[`${f}.md`] || `# ${f}\n\nNo content yet.`;
        });
        setFileContent(content);
      });
    }
  }, [agent]);

  if (!editedAgent) return null;

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      size="xl"
      padding={0}
      centered
      withCloseButton={false}
      radius="md"
      styles={{
        content: {
          background: "rgba(25, 25, 30, 0.98)",
          border: "1px solid rgba(255,255,255,0.08)",
        },
      }}
    >
      <Group
        justify="space-between"
        p="md"
        style={{
          borderBottom: "1px solid rgba(255,255,255,0.06)",
        }}
      >
        <Group gap={12}>
          <Avatar
            src={AVATAR_IMAGES[editedAgent.id]}
            size={32}
            radius="xl"
            style={{
              border: `2px solid ${editedAgent.status === "active" ? "#22c55e" : "rgba(255,255,255,0.2)"}`,
              filter: "grayscale(30%)",
            }}
          />
          <Box>
            <Text size="sm" fw={600} c="white">
              {editedAgent.displayName}
            </Text>
            <Text size="xs" c="dimmed">
              {editedAgent.name}
            </Text>
          </Box>
        </Group>
        <ActionIcon variant="subtle" color="gray" onClick={onClose} radius="sm">
          <IconX size={16} />
        </ActionIcon>
      </Group>

      {/* Main tabs: Settings vs Activity */}
      <Tabs value={activeTab} onChange={setActiveTab} variant="outline">
        <Tabs.List px="md" pt={8} style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
          <Tabs.Tab value="settings" leftSection={<IconSettings size={14} />}>
            Settings
          </Tabs.Tab>
          <Tabs.Tab value="activity" leftSection={<IconActivity size={14} />}>
            Activity
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="settings">
          <Box p={24}>
            <Stack gap={24}>
              <SimpleGrid cols={2} spacing={16}>
                <TextInput
                  label="Display Name"
                  value={editedAgent.displayName}
                  onChange={(e) => setEditedAgent({ ...editedAgent, displayName: e.target.value })}
                  size="sm"
                  radius="sm"
                  styles={{ 
                    label: { fontSize: 11, textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 6, color: "var(--mantine-color-dimmed)" },
                    input: { background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)" } 
                  }}
                />
                <TextInput
                  label="Role ID"
                  value={editedAgent.id}
                  disabled
                  size="sm"
                  radius="sm"
                  styles={{ 
                    label: { fontSize: 11, textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 6, color: "var(--mantine-color-dimmed)" },
                    input: { background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)" } 
                  }}
                />
              </SimpleGrid>

              <SimpleGrid cols={2} spacing={16}>
                <Select
                  label="Model"
                  value={editedAgent.model}
                  onChange={(v) => setEditedAgent({ ...editedAgent, model: v || "claude-sonnet-4" })}
                  data={MODEL_OPTIONS}
                  size="sm"
                  radius="sm"
                  styles={{ 
                    label: { fontSize: 11, textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 6, color: "var(--mantine-color-dimmed)" },
                    input: { background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)" } 
                  }}
                />
                <Select
                  label="Thinking"
                  value={editedAgent.thinking}
                  onChange={(v) => setEditedAgent({ ...editedAgent, thinking: v || "low" })}
                  data={THINKING_OPTIONS}
                  size="sm"
                  radius="sm"
                  styles={{ 
                    label: { fontSize: 11, textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 6, color: "var(--mantine-color-dimmed)" },
                    input: { background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)" } 
                  }}
                />
              </SimpleGrid>

              <Divider color="rgba(255,255,255,0.06)" />

              <Box>
                <Group justify="space-between" mb={12}>
                  <Text size="xs" fw={600} c="dimmed" tt="uppercase" style={{ letterSpacing: 0.5 }}>
                    Workspace Files
                  </Text>
                  <Text size="xs" c={saved ? "green" : "orange"} fw={500}>
                    {saved ? "Saved" : "Unsaved"}
                  </Text>
                </Group>

                <Tabs value={activeFile} onChange={(v) => setActiveFile(v || "TOOLS")} variant="pills" radius="sm">
                  <Tabs.List mb={12}>
                    {WORKSPACE_FILES.map((f) => (
                      <Tabs.Tab 
                        key={f} 
                        value={f} 
                        size="xs" 
                        style={{ 
                          fontWeight: 500, 
                          fontSize: 11,
                          padding: "4px 8px",
                        }}
                      >
                        {f}
                      </Tabs.Tab>
                    ))}
                  </Tabs.List>
                </Tabs>

                <Paper 
                  p={12} 
                  radius="sm" 
                  style={{ 
                    background: "rgba(0,0,0,0.3)", 
                    border: "1px solid rgba(255,255,255,0.06)" 
                  }}
                >
                  <Text size="xs" fw={600} c="dimmed" mb={8}>{activeFile}.md</Text>
                  <Textarea
                    value={fileContent[activeFile] || ""}
                    onChange={async (e) => {
                      const newContent = e.target.value;
                      setFileContent({ ...fileContent, [activeFile]: newContent });
                      setSaved(false);
                      if (editedAgent) {
                        const success = await saveWorkspaceFile(editedAgent.id, `${activeFile}.md`, newContent);
                        if (success) setSaved(true);
                      }
                    }}
                    minRows={8}
                    maxRows={12}
                    autosize
                    radius="sm"
                    styles={{ 
                      input: { 
                        fontFamily: "monospace", 
                        fontSize: 12, 
                        background: "transparent", 
                        border: "none",
                        lineHeight: 1.6,
                      } 
                    }}
                  />
                </Paper>
              </Box>

              <Divider color="rgba(255,255,255,0.06)" />

              <Group justify="space-between">
                <Button
                  color={editedAgent.status === "active" ? "red" : "green"}
                  variant="subtle"
                  size="xs"
                  radius="sm"
                  disabled={editedAgent.alwaysOn}
                  onClick={() => {
                    onToggleStatus(editedAgent);
                    onClose();
                  }}
                >
                  {editedAgent.alwaysOn
                    ? "Always On"
                    : editedAgent.status === "active"
                      ? "Stop Agent"
                      : "Start Agent"}
                </Button>
                <Group gap={8}>
                  <Button 
                    variant="subtle" 
                    color="gray" 
                    size="xs"
                    radius="sm"
                    onClick={onClose}
                  >
                    Cancel
                  </Button>
                  <Button 
                    variant="filled" 
                    color="gray" 
                    size="xs"
                    radius="sm"
                    onClick={() => { onSave(editedAgent); setSaved(true); onClose(); }}
                  >
                    Save Changes
                  </Button>
                </Group>
              </Group>
            </Stack>
          </Box>
        </Tabs.Panel>

        <Tabs.Panel value="activity">
          <Box p={16}>
            <AgentActivityDashboard 
              agentId={editedAgent.id} 
              agentName={editedAgent.displayName}
            />
          </Box>
        </Tabs.Panel>
      </Tabs>
    </Modal>
  );
}

// Build default agents from definitions (always visible)
function buildDefaultAgents(): Agent[] {
  return AGENT_DEFINITIONS.map((def) => ({
    id: def.id,
    name: def.name,
    displayName: def.displayName,
    role: def.id,
    model: def.id === "manager" ? "claude-opus-4" : "claude-sonnet-4",
    thinking: def.id === "manager" ? "medium" : "low",
    status: def.alwaysOn ? "active" as const : "offline" as const,
    color: def.color,
    description: def.description,
    pendingTasks: 0,
    errorCount: 0,
    alwaysOn: def.alwaysOn || false,
  }));
}

// Main Component
export function AgentManager() {
  const [agents, setAgents] = useState<Agent[]>(buildDefaultAgents());
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [defaultTab, setDefaultTab] = useState<string>("settings");
  const [agentActivity, setAgentActivity] = useState<Record<string, ActivityLog[]>>({});
  const [activityLoading, setActivityLoading] = useState<Record<string, boolean>>({});
  const [mounted, setMounted] = useState(false);
  const [backendOnline, setBackendOnline] = useState(false);
  
  // Agent targeting context - for clicking agent to talk in main console
  const { selectAgent } = useAgentContext();

  // Fetch real agent data from backend and merge with definitions
  const loadAgents = useCallback(async () => {
    const data = await fetchSystemMonitor();
    const fleetAgents = await fetchFleetAgents();

    const statusMap = data?.processes
      ? new Map<string, any>(data.processes.map((p: any) => [p.id, p]))
      : new Map<string, any>();
    const fleetMap = new Map<string, any>(fleetAgents.map((a: any) => [a.id, a]));

    if (data?.processes || fleetAgents.length > 0) {
      setBackendOnline(true);

      setAgents((prev) =>
        prev.map((agent) => {
          const backendData = statusMap.get(agent.id);
          const fleet = fleetMap.get(resolveFleetId(agent.id)) || fleetMap.get(agent.id);

          let status: "active" | "idle" | "error" | "offline" = "offline";
          if (backendData) {
            status = backendData.state === "running"
              ? "active"
              : backendData.state === "error"
              ? "error"
              : backendData.state === "stopped"
              ? "offline"
              : "idle";
          } else if (fleet) {
            if (!fleet.enabled) status = "offline";
            else if (fleet.state === "running") status = "active";
            else if (fleet.state === "error") status = "error";
            else status = "idle";
          }

          return {
            ...agent,
            status,
            model: fleet?.default_model || agent.model,
            thinking: fleet?.max_tier ? (TIER_TO_THINKING[fleet.max_tier] || agent.thinking) : agent.thinking,
            pendingTasks: backendData?.pending_tasks ?? fleet?.current_requests ?? 0,
            errorCount: backendData?.error_count ?? (fleet?.last_error ? 1 : 0),
          };
        })
      );
    } else {
      setBackendOnline(false);
      setAgents((prev) =>
        prev.map((agent) => ({ ...agent, status: "offline" as const }))
      );
    }
  }, []);

  useEffect(() => {
    setMounted(true);
    loadAgents();
    
    // Poll for updates every 10s
    const interval = setInterval(loadAgents, 10000);
    return () => clearInterval(interval);
  }, [loadAgents]);

  useEffect(() => {
    const handler = () => loadAgents();
    window.addEventListener("mycasa-system-sync", handler as EventListener);
    return () => window.removeEventListener("mycasa-system-sync", handler as EventListener);
  }, [loadAgents]);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (over && active.id !== over.id) {
      setAgents((items) => {
        const oldIndex = items.findIndex((i) => i.id === active.id);
        const newIndex = items.findIndex((i) => i.id === over.id);
        return arrayMove(items, oldIndex, newIndex);
      });
    }
  };

  const handleToggleStatus = useCallback(async (agent: Agent) => {
    if (!backendOnline) {
      notifications.show({ 
        title: "Backend Offline", 
        message: "Start the backend to control agents", 
        color: "orange" 
      });
      return;
    }
    
    if (agent.status === "active") {
      const success = await stopAgent(agent.id);
      if (success) {
        setAgents(prev => prev.map(a => 
          a.id === agent.id ? { ...a, status: "idle" as const } : a
        ));
        notifications.show({ title: "Agent Stopped", message: `${agent.displayName} is now idle`, color: "gray" });
        window.dispatchEvent(new CustomEvent("mycasa-system-sync"));
      }
    } else {
      const success = await startAgent(agent.id);
      if (success) {
        setAgents(prev => prev.map(a => 
          a.id === agent.id ? { ...a, status: "active" as const } : a
        ));
        notifications.show({ title: "Agent Started", message: `${agent.displayName} is now running`, color: "green" });
        window.dispatchEvent(new CustomEvent("mycasa-system-sync"));
      }
    }
  }, [backendOnline]);

  // Fetch activity for an agent when expanded
  const loadActivity = useCallback(async (agentId: string) => {
    if (agentActivity[agentId]) return; // Already loaded
    
    setActivityLoading(prev => ({ ...prev, [agentId]: true }));
    const activity = await fetchAgentActivity(agentId);
    setAgentActivity(prev => ({ ...prev, [agentId]: activity }));
    setActivityLoading(prev => ({ ...prev, [agentId]: false }));
  }, [agentActivity]);

  const handleSelectAgent = (agent: Agent, tab: string = "settings") => {
    setSelectedAgent(agent);
    setDefaultTab(tab);
    setSettingsOpen(true);
    loadActivity(agent.id);
  };

  const handleChatWithAgent = (agent: Agent) => {
    selectAgent(agent.id);
    notifications.show({
      title: `Now talking to ${agent.displayName}`,
      message: `All messages will be sent to ${agent.displayName} (${agent.name})`,
      color: agent.color,
      icon: <IconMessageCircle size={16} />,
      autoClose: 3000,
    });
  };
  
  const handleViewActivity = (agent: Agent) => {
    handleSelectAgent(agent, "activity");
  };

  const handleSaveAgent = async (updated: Agent) => {
    const success = await updateAgentConfig(updated);
    if (!success) {
      notifications.show({
        title: "Update Failed",
        message: "Could not update agent model settings.",
        color: "red",
        icon: <IconX size={16} />,
      });
      return;
    }
    setAgents(agents.map((a) => (a.id === updated.id ? updated : a)));
    notifications.show({ title: "Agent Updated", message: `${updated.displayName} saved`, color: "green", icon: <IconCheck size={16} /> });
  };

  const activeCount = agents.filter((a) => a.status === "active").length;
  const idleCount = agents.filter((a) => a.status === "idle").length;
  const errorCount = agents.filter((a) => a.status === "error").length;
  const offlineCount = agents.filter((a) => a.status === "offline").length;

  return (
    <Box>
      {/* Header */}
      <Group justify="space-between" mb={24}>
        <Box>
          <Text size="lg" fw={600} c="white">
            Agent Fleet
          </Text>
          <Text size="sm" c="dimmed">
            {agents.length} agents configured
          </Text>
        </Box>
        <Group gap={16}>
          {activeCount > 0 && (
            <Group gap={6}>
              <Box w={8} h={8} style={{ borderRadius: "50%", background: "#22c55e" }} />
              <Text size="xs" c="dimmed">{activeCount} running</Text>
            </Group>
          )}
          {idleCount > 0 && (
            <Group gap={6}>
              <Box w={8} h={8} style={{ borderRadius: "50%", background: "rgba(255,255,255,0.3)" }} />
              <Text size="xs" c="dimmed">{idleCount} idle</Text>
            </Group>
          )}
          {errorCount > 0 && (
            <Group gap={6}>
              <Box w={8} h={8} style={{ borderRadius: "50%", background: "#ef4444" }} />
              <Text size="xs" c="dimmed">{errorCount} error</Text>
            </Group>
          )}
          {offlineCount > 0 && (
            <Group gap={6}>
              <Box w={8} h={8} style={{ borderRadius: "50%", background: "#6b7280" }} />
              <Text size="xs" c="dimmed">{offlineCount} offline</Text>
            </Group>
          )}
        </Group>
      </Group>

      {/* Grid container */}
      <Box
        style={{
          background: "rgba(255,255,255,0.01)",
          borderRadius: 12,
          padding: 24,
          minHeight: 500,
          border: "1px solid rgba(255,255,255,0.04)",
          position: "relative",
        }}
      >
        {/* Subtle grid pattern */}
        <Box
          style={{
            position: "absolute",
            inset: 0,
            backgroundImage: "radial-gradient(circle at 1px 1px, rgba(255,255,255,0.03) 1px, transparent 0)",
            backgroundSize: "24px 24px",
            pointerEvents: "none",
            borderRadius: 12,
          }}
        />

        {mounted ? (
          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <SortableContext items={agents.map((a) => a.id)} strategy={rectSortingStrategy}>
              <SimpleGrid cols={{ base: 1, xs: 2, md: 3, lg: 4 }} spacing={16} style={{ position: "relative", zIndex: 1 }}>
                {agents.map((agent) => (
                  <SortableAgentCard
                    key={agent.id}
                    agent={agent}
                    onSelect={() => handleSelectAgent(agent, "settings")}
                    onToggleStatus={() => handleToggleStatus(agent)}
                    onChatWithAgent={() => handleChatWithAgent(agent)}
                    onViewActivity={() => handleViewActivity(agent)}
                    activity={agentActivity[agent.id] || []}
                    activityLoading={activityLoading[agent.id] || false}
                  />
                ))}
              </SimpleGrid>
            </SortableContext>
          </DndContext>
        ) : (
          <SimpleGrid cols={{ base: 1, xs: 2, md: 3, lg: 4 }} spacing={16} style={{ position: "relative", zIndex: 1 }}>
            {agents.map((agent) => (
              <Card 
                key={agent.id} 
                padding="md" 
                radius="md" 
                bg="rgba(30, 30, 35, 0.95)"
                h={240}
                style={{
                  border: "1px solid rgba(255,255,255,0.08)",
                }}
              >
                <Group gap={12}>
                  <Avatar 
                    src={AVATAR_IMAGES[agent.id]} 
                    size={36} 
                    radius="xl"
                    style={{
                      border: `2px solid ${agent.status === "active" ? "#22c55e" : "rgba(255,255,255,0.2)"}`,
                      filter: "grayscale(30%)",
                    }}
                  />
                  <Box>
                    <Text size="sm" fw={600} c="white">{agent.displayName}</Text>
                    <Text size="xs" c="dimmed">{agent.status.toUpperCase()}</Text>
                  </Box>
                </Group>
              </Card>
            ))}
          </SimpleGrid>
        )}
      </Box>

      <AgentSettingsModal
        agent={selectedAgent}
        opened={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        onSave={handleSaveAgent}
        onToggleStatus={handleToggleStatus}
        defaultTab={defaultTab}
      />
    </Box>
  );
}
