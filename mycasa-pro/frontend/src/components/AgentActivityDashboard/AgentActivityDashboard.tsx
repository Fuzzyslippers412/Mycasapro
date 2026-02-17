"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { getApiBaseUrl } from "@/lib/api";
import {
  Box,
  Paper,
  Text,
  Group,
  Stack,
  Progress,
  Divider,
  Badge,
  Tooltip,
  Loader,
  ScrollArea,
  ThemeIcon,
} from "@mantine/core";
import {
  IconCheck,
  IconHourglass,
  IconBulb,
  IconCircleFilled,
  IconFile,
  IconTerminal,
  IconCloud,
  IconQuestionMark,
} from "@tabler/icons-react";

const API_URL = getApiBaseUrl();

interface AgentActivity {
  agent_id: string;
  session_id: string | null;
  period_start: string;
  period_end: string;
  total_files: number;
  files_modified: number;
  files_read: number;
  tool_usage: Record<string, number>;
  systems: Record<string, string>;
  decisions_count: number;
  open_questions_count: number;
  files_touched: Array<{ path: string; action: string; timestamp: string }>;
  decisions: string[];
  questions: string[];
  threads: Array<{
    id: string;
    name: string;
    status: string;
    children: Array<{ name: string; status: string }>;
  }>;
  heat_map: Array<{ topic: string; score: number; color: string }>;
  context_percent: number;
  context_used: number;
  context_limit: number;
  runway_tokens: number;
  velocity: number;
}

interface WebSocketMessage {
  type: string;
  agent_id?: string;
  data?: any;
  timestamp?: string;
}

interface Props {
  agentId: string;
  agentName?: string;
  compact?: boolean;
}

const STATUS_ICONS: Record<string, React.ReactNode> = {
  done: <IconCheck size={14} color="#2ee59d" />,
  in_progress: <IconHourglass size={14} color="#ffb347" />,
  idea: <IconBulb size={14} color="#87ceeb" />,
  blocked: <IconCircleFilled size={14} color="#ff4d4d" />,
};

export function AgentActivityDashboard({ agentId, agentName, compact = false }: Props) {
  const [activity, setActivity] = useState<AgentActivity | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const fetchActivity = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/agent-activity/${agentId}/activity`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setActivity(data);
      setError(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [agentId]);

  // Polling-only updates (WebSocket disabled)
  useEffect(() => {
    fetchActivity(); // Initial fetch
    const interval = setInterval(() => {
      if (document.visibilityState === "visible") {
        fetchActivity();
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [agentId]);

  if (loading) {
    return (
      <Box p="md" ta="center">
        <Loader size="sm" />
      </Box>
    );
  }

  if (error || !activity) {
    return (
      <Box p="md">
        <Text c="dimmed" size="sm">No activity data available</Text>
      </Box>
    );
  }

  const sortedTools = Object.entries(activity.tool_usage)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6);

  const maxToolCount = sortedTools.length > 0 ? sortedTools[0][1] : 1;

  return (
    <Box
      style={{
        background: "linear-gradient(180deg, rgba(11,15,20,0.95), rgba(15,22,32,0.98))",
        borderRadius: 16,
        border: "1px solid rgba(255,255,255,0.06)",
        padding: compact ? 12 : 20,
        fontFamily: "ui-sans-serif, system-ui, -apple-system, sans-serif",
      }}
    >
      {/* Header */}
      <Group justify="space-between" mb="md">
        <Box>
          <Text
            size={compact ? "sm" : "md"}
            fw={700}
            c="white"
            tt="uppercase"
            style={{ letterSpacing: 1 }}
          >
            {agentName || agentId.toUpperCase()}
          </Text>
          {activity.session_id && (
            <Text size="xs" c="dimmed">
              session {activity.session_id.slice(0, 12)}
            </Text>
          )}
        </Box>
        <Group gap={8}>
          <Box ta="right">
            <Text size="xs" c="dimmed">ctx</Text>
            <Progress
              value={activity.context_percent}
              size="sm"
              w={80}
              color={activity.context_percent > 80 ? "red" : activity.context_percent > 50 ? "yellow" : "cyan"}
            />
          </Box>
          <Text size="xs" c="cyan" fw={600}>
            {activity.context_percent.toFixed(0)}%{" "}
            <Text span c="dimmed">({(activity.context_used / 1000).toFixed(0)}k/{(activity.context_limit / 1000).toFixed(0)}k)</Text>
          </Text>
        </Group>
      </Group>

      {/* Velocity & Runway */}
      <Group gap="xl" mb="md">
        <Group gap={4}>
          <Box
            style={{
              width: 60,
              height: 8,
              background: "linear-gradient(90deg, #6366f1, #a855f7)",
              borderRadius: 4,
            }}
          />
          <Text size="xs" c="dimmed">velocity</Text>
        </Group>
        <Text size="xs" c="#2ee59d" fw={600}>
          runway: ~{(activity.runway_tokens / 1000).toFixed(0)}k tokens
        </Text>
      </Group>

      <Divider color="rgba(255,255,255,0.06)" mb="md" />

      {/* Main Grid */}
      <Box
        style={{
          display: "grid",
          gridTemplateColumns: compact ? "1fr" : "1fr 1fr",
          gap: 16,
        }}
      >
        {/* Left Column: Threads + Heat */}
        <Stack gap="md">
          {/* Threads */}
          {activity.threads.length > 0 && (
            <Box>
              <Text size="xs" c="dimmed" fw={700} mb={8} tt="uppercase" style={{ letterSpacing: 1 }}>
                Threads
              </Text>
              <Box
                style={{
                  border: "1px solid rgba(255,255,255,0.08)",
                  borderRadius: 8,
                  padding: 10,
                  background: "rgba(0,0,0,0.2)",
                }}
              >
                {activity.threads.slice(0, 3).map((thread) => (
                  <Box key={thread.id} mb={8}>
                    <Group gap={6} mb={4}>
                      <Text size="xs" c="#ffb347" fw={600}>
                        {thread.name}
                      </Text>
                    </Group>
                    <Stack gap={2} pl={12}>
                      {thread.children.slice(0, 4).map((child, idx) => (
                        <Group key={idx} gap={6}>
                          <Text size="xs" c="dimmed" style={{ fontSize: 10 }}>├─</Text>
                          {STATUS_ICONS[child.status] || STATUS_ICONS.in_progress}
                          <Text size="xs" c="gray.4">{child.name}</Text>
                        </Group>
                      ))}
                    </Stack>
                  </Box>
                ))}
              </Box>
            </Box>
          )}

          {/* Heat Map */}
          {activity.heat_map.length > 0 && (
            <Box>
              <Text size="xs" c="dimmed" fw={700} mb={8} tt="uppercase" style={{ letterSpacing: 1 }}>
                Heat <Text span c="gray.6">(recent → stale)</Text>
              </Text>
              <Stack gap={4}>
                {activity.heat_map.slice(0, 6).map((item, idx) => (
                  <Group key={idx} gap={8}>
                    <Box
                      style={{
                        width: Math.max(20, item.score * 100),
                        height: 12,
                        background: item.color,
                        borderRadius: 2,
                        transition: "width 0.3s",
                      }}
                    />
                    <Text size="xs" c="gray.4">{item.topic}</Text>
                  </Group>
                ))}
              </Stack>
            </Box>
          )}
        </Stack>

        {/* Right Column: Files + Tools + Systems */}
        <Stack gap="md">
          {/* Files Touched */}
          <Box>
            <Text size="xs" c="dimmed" fw={700} mb={8} tt="uppercase" style={{ letterSpacing: 1 }}>
              Files Touched
            </Text>
            <ScrollArea h={compact ? 80 : 120}>
              <Stack gap={2}>
                {activity.files_touched.slice(-10).map((file, idx) => (
                  <Group key={idx} gap={6}>
                    <ThemeIcon
                      size="sm"
                      radius="xl"
                      variant="light"
                      color={file.action === "modified" ? "orange" : "gray"}
                    >
                      <IconFile size={10} />
                    </ThemeIcon>
                    <Text size="xs" c={file.action === "modified" ? "orange.4" : "gray.5"}>
                      {file.path.split("/").slice(-2).join("/")}
                    </Text>
                    <Text size="xs" c="dimmed" style={{ fontSize: 10 }}>
                      {file.action === "modified" ? "◆" : "◇"}
                    </Text>
                  </Group>
                ))}
                {activity.files_touched.length === 0 && (
                  <Text size="xs" c="dimmed">No files touched yet</Text>
                )}
              </Stack>
            </ScrollArea>
            <Group gap="xs" mt={4}>
              <Text size="xs" c="dimmed" style={{ fontSize: 10 }}>◆ = modified</Text>
              <Text size="xs" c="dimmed" style={{ fontSize: 10 }}>◇ = read</Text>
            </Group>
          </Box>

          {/* Tools Used */}
          <Box>
            <Text size="xs" c="dimmed" fw={700} mb={8} tt="uppercase" style={{ letterSpacing: 1 }}>
              Tools Used
            </Text>
            <Stack gap={4}>
              {sortedTools.map(([tool, count]) => (
                <Group key={tool} gap={8}>
                  <Text size="xs" c="gray.3" w={50}>{tool}</Text>
                  <Box
                    style={{
                      width: `${(count / maxToolCount) * 100}%`,
                      maxWidth: 100,
                      height: 10,
                      background: "linear-gradient(90deg, #6366f1, #8b5cf6)",
                      borderRadius: 2,
                    }}
                  />
                  <Text size="xs" c="gray.5">{count}</Text>
                </Group>
              ))}
              {sortedTools.length === 0 && (
                <Text size="xs" c="dimmed">No tools used yet</Text>
              )}
            </Stack>
          </Box>

          {/* Systems */}
          <Box>
            <Text size="xs" c="dimmed" fw={700} mb={8} tt="uppercase" style={{ letterSpacing: 1 }}>
              Systems
            </Text>
            <Group gap={8}>
              {Object.entries(activity.systems).map(([sys, status]) => (
                <Badge
                  key={sys}
                  size="sm"
                  variant="outline"
                  color={status === "ok" ? "green" : status === "error" ? "red" : "yellow"}
                  leftSection={<IconCloud size={10} />}
                >
                  {sys}
                </Badge>
              ))}
              {Object.keys(activity.systems).length === 0 && (
                <Text size="xs" c="dimmed">No external systems accessed</Text>
              )}
            </Group>
          </Box>
        </Stack>
      </Box>

      <Divider color="rgba(255,255,255,0.06)" my="md" />

      {/* Bottom: Decisions & Questions */}
      <Box
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 16,
        }}
      >
        {/* Decisions Made */}
        <Box>
          <Text size="xs" c="dimmed" fw={700} mb={8} tt="uppercase" style={{ letterSpacing: 1 }}>
            Decisions Made
          </Text>
          <Stack gap={4}>
            {activity.decisions.slice(-5).map((decision, idx) => (
              <Group key={idx} gap={6} align="flex-start">
                <IconCheck size={12} color="#2ee59d" style={{ marginTop: 2 }} />
                <Text size="xs" c="gray.3" style={{ flex: 1 }}>{decision}</Text>
              </Group>
            ))}
            {activity.decisions.length === 0 && (
              <Text size="xs" c="dimmed">No decisions recorded</Text>
            )}
          </Stack>
        </Box>

        {/* Open Questions */}
        <Box>
          <Text size="xs" c="dimmed" fw={700} mb={8} tt="uppercase" style={{ letterSpacing: 1 }}>
            Open Questions
          </Text>
          <Stack gap={4}>
            {activity.questions.slice(-5).map((question, idx) => (
              <Group key={idx} gap={6} align="flex-start">
                <IconQuestionMark size={12} color="#87ceeb" style={{ marginTop: 2 }} />
                <Text size="xs" c="gray.4" style={{ flex: 1 }}>{question}</Text>
              </Group>
            ))}
            {activity.questions.length === 0 && (
              <Text size="xs" c="dimmed">No open questions</Text>
            )}
          </Stack>
        </Box>
      </Box>
    </Box>
  );
}

export default AgentActivityDashboard;
