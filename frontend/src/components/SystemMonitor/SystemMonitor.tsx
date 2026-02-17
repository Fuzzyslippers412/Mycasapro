"use client";

import { useState, useEffect } from "react";
import { getApiBaseUrl } from "@/lib/api";
import {
  Box,
  Group,
  Stack,
  Text,
  Badge,
  Progress,
  Table,
  Paper,
  Title,
  ActionIcon,
  Tooltip,
  Tabs,
  ScrollArea,
  Timeline,
  ThemeIcon,
  Divider,
  Card,
  SimpleGrid,
} from "@mantine/core";
import {
  IconRefresh,
  IconPlayerPlay,
  IconPlayerStop,
  IconReload,
  IconCheck,
  IconX,
  IconClock,
  IconActivity,
  IconRobot,
  IconAlertTriangle,
  IconChartBar,
} from "@tabler/icons-react";

const API_URL = getApiBaseUrl();

interface AgentLog {
  id: number;
  action: string;
  details: string | null;
  status: string;
  created_at: string;
}

interface AgentProcess {
  id: string;
  name: string;
  state: string;
  uptime: number;
  memory_mb: number;
  cpu_percent: number;
  pending_tasks: number;
  error_count: number;
  last_heartbeat: string;
  recent_logs?: AgentLog[];
  metrics?: Record<string, any>;
}

interface SystemResources {
  cpu_percent: number;
  memory_percent: number;
  agents_active: number;
  agents_total: number;
  cost_today: number;
}

export function SystemMonitor() {
  const [processes, setProcesses] = useState<AgentProcess[]>([]);
  const [allLogs, setAllLogs] = useState<(AgentLog & { agent: string })[]>([]);
  const [resources, setResources] = useState<SystemResources>({
    cpu_percent: 0,
    memory_percent: 0,
    agents_active: 0,
    agents_total: 0,
    cost_today: 0,
  });
  const [loading, setLoading] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);

  const fetchSystemData = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/system/monitor`);
      if (res.ok) {
        const data = await res.json();
        setProcesses(data.processes || []);
        setResources(data.resources || resources);
        
        // Collect all logs from all agents
        const logs: (AgentLog & { agent: string })[] = [];
        for (const proc of data.processes || []) {
          if (proc.recent_logs) {
            for (const log of proc.recent_logs) {
              logs.push({ ...log, agent: proc.id });
            }
          }
        }
        // Sort by created_at descending
        logs.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
        setAllLogs(logs.slice(0, 50)); // Keep last 50
      }
    } catch (error) {
      console.error("Failed to fetch system data:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSystemData();
    const interval = setInterval(fetchSystemData, 5000);
    return () => clearInterval(interval);
  }, []);

  const getStateColor = (state: string) => {
    switch (state) {
      case "running":
      case "active":
        return "green";
      case "idle":
        return "blue";
      case "error":
        return "red";
      case "stopped":
      case "not_loaded":
        return "gray";
      case "pending_intake":
        return "yellow";
      default:
        return "gray";
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "success":
        return <IconCheck size={12} />;
      case "error":
      case "failed":
        return <IconX size={12} />;
      case "started":
        return <IconClock size={12} />;
      default:
        return <IconActivity size={12} />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "success":
        return "green";
      case "error":
      case "failed":
        return "red";
      case "started":
        return "blue";
      default:
        return "gray";
    }
  };

  const formatTime = (ts: string) => {
    try {
      const date = new Date(ts);
      return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    } catch {
      return ts;
    }
  };

  const formatTimeAgo = (ts: string) => {
    try {
      const date = new Date(ts);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffSec = Math.floor(diffMs / 1000);
      
      if (diffSec < 60) return `${diffSec}s ago`;
      if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
      if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
      return date.toLocaleDateString();
    } catch {
      return ts;
    }
  };

  const getAgentEmoji = (id: string) => {
    const emojis: Record<string, string> = {
      finance: "💰",
      maintenance: "🔧",
      contractors: "👷",
      projects: "📋",
      janitor: "🧹",
      security: "🛡️",
      "security-manager": "🛡️",
      manager: "🤖",
    };
    return emojis[id] || "🔹";
  };

  // Calculate stats
  const totalCompleted = allLogs.filter(l => l.status === "success").length;
  const totalErrors = allLogs.filter(l => l.status === "error" || l.status === "failed").length;
  const totalPending = processes.reduce((sum, p) => sum + (p.pending_tasks || 0), 0);

  return (
    <Stack gap="md">
      {/* Stats Overview */}
      <SimpleGrid cols={{ base: 2, sm: 4 }}>
        <Card withBorder p="md">
          <Group justify="space-between">
            <div>
              <Text size="xs" c="dimmed" tt="uppercase">Agents Active</Text>
              <Text size="xl" fw={700}>{resources.agents_active} / {resources.agents_total}</Text>
            </div>
            <ThemeIcon size="xl" variant="light" color="blue">
              <IconRobot size={24} />
            </ThemeIcon>
          </Group>
        </Card>
        <Card withBorder p="md">
          <Group justify="space-between">
            <div>
              <Text size="xs" c="dimmed" tt="uppercase">Tasks Completed</Text>
              <Text size="xl" fw={700} c="green">{totalCompleted}</Text>
            </div>
            <ThemeIcon size="xl" variant="light" color="green">
              <IconCheck size={24} />
            </ThemeIcon>
          </Group>
        </Card>
        <Card withBorder p="md">
          <Group justify="space-between">
            <div>
              <Text size="xs" c="dimmed" tt="uppercase">Tasks Pending</Text>
              <Text size="xl" fw={700} c="blue">{totalPending}</Text>
            </div>
            <ThemeIcon size="xl" variant="light" color="blue">
              <IconClock size={24} />
            </ThemeIcon>
          </Group>
        </Card>
        <Card withBorder p="md">
          <Group justify="space-between">
            <div>
              <Text size="xs" c="dimmed" tt="uppercase">Errors</Text>
              <Text size="xl" fw={700} c={totalErrors > 0 ? "red" : "dimmed"}>{totalErrors}</Text>
            </div>
            <ThemeIcon size="xl" variant="light" color={totalErrors > 0 ? "red" : "gray"}>
              <IconAlertTriangle size={24} />
            </ThemeIcon>
          </Group>
        </Card>
      </SimpleGrid>

      <Tabs defaultValue="activity">
        <Tabs.List>
          <Tabs.Tab value="activity" leftSection={<IconActivity size={16} />}>
            Live Activity
          </Tabs.Tab>
          <Tabs.Tab value="agents" leftSection={<IconRobot size={16} />}>
            Agents
          </Tabs.Tab>
          <Tabs.Tab value="logs" leftSection={<IconChartBar size={16} />}>
            Full Logs
          </Tabs.Tab>
        </Tabs.List>

        {/* Live Activity Feed */}
        <Tabs.Panel value="activity" pt="md">
          <Paper p="md" withBorder>
            <Group justify="space-between" mb="md">
              <Title order={4}>🔴 Live Agent Activity</Title>
              <ActionIcon variant="light" onClick={fetchSystemData} loading={loading}>
                <IconRefresh size={18} />
              </ActionIcon>
            </Group>

            {allLogs.length === 0 ? (
              <Text c="dimmed" ta="center" py="xl">No recent activity</Text>
            ) : (
              <ScrollArea h={400}>
                <Timeline active={0} bulletSize={24} lineWidth={2}>
                  {allLogs.slice(0, 20).map((log, idx) => (
                    <Timeline.Item
                      key={`${log.agent}-${log.id}`}
                      bullet={
                        <ThemeIcon size={24} radius="xl" color={getStatusColor(log.status)}>
                          {getStatusIcon(log.status)}
                        </ThemeIcon>
                      }
                      title={
                        <Group gap="xs">
                          <Text span>{getAgentEmoji(log.agent)}</Text>
                          <Text span fw={600} tt="capitalize">{log.agent}</Text>
                          <Badge size="xs" color={getStatusColor(log.status)}>{log.status}</Badge>
                          <Text span size="xs" c="dimmed">{formatTimeAgo(log.created_at)}</Text>
                        </Group>
                      }
                    >
                      <Text size="sm" fw={500} mt={4}>{log.action.replace(/_/g, " ")}</Text>
                      {log.details && (
                        <Text size="xs" c="dimmed" mt={2} style={{ wordBreak: "break-word" }}>
                          {log.details.length > 100 ? log.details.slice(0, 100) + "..." : log.details}
                        </Text>
                      )}
                    </Timeline.Item>
                  ))}
                </Timeline>
              </ScrollArea>
            )}
          </Paper>
        </Tabs.Panel>

        {/* Agents Tab */}
        <Tabs.Panel value="agents" pt="md">
          <Paper p="md" withBorder>
            <Group justify="space-between" mb="md">
              <Title order={4}>Agent Status</Title>
              <ActionIcon variant="light" onClick={fetchSystemData} loading={loading}>
                <IconRefresh size={18} />
              </ActionIcon>
            </Group>

            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Agent</Table.Th>
                  <Table.Th>State</Table.Th>
                  <Table.Th>Pending</Table.Th>
                  <Table.Th>Completed</Table.Th>
                  <Table.Th>Errors</Table.Th>
                  <Table.Th>Last Activity</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {processes.map((proc) => {
                  const agentLogs = allLogs.filter(l => l.agent === proc.id);
                  const completed = agentLogs.filter(l => l.status === "success").length;
                  const errors = agentLogs.filter(l => l.status === "error").length;
                  const lastLog = agentLogs[0];
                  
                  return (
                    <Table.Tr key={proc.id}>
                      <Table.Td>
                        <Group gap="xs">
                          <Text>{getAgentEmoji(proc.id)}</Text>
                          <Text fw={600}>{proc.name}</Text>
                        </Group>
                      </Table.Td>
                      <Table.Td>
                        <Badge size="sm" color={getStateColor(proc.state)}>
                          {proc.state}
                        </Badge>
                      </Table.Td>
                      <Table.Td>
                        <Badge size="sm" variant="light" color="blue">
                          {proc.pending_tasks}
                        </Badge>
                      </Table.Td>
                      <Table.Td>
                        <Badge size="sm" variant="light" color="green">
                          {completed}
                        </Badge>
                      </Table.Td>
                      <Table.Td>
                        <Badge size="sm" variant="light" color={errors > 0 ? "red" : "gray"}>
                          {errors}
                        </Badge>
                      </Table.Td>
                      <Table.Td>
                        {lastLog ? (
                          <Text size="xs" c="dimmed">
                            {lastLog.action.replace(/_/g, " ")} ({formatTimeAgo(lastLog.created_at)})
                          </Text>
                        ) : (
                          <Text size="xs" c="dimmed">No activity</Text>
                        )}
                      </Table.Td>
                    </Table.Tr>
                  );
                })}
              </Table.Tbody>
            </Table>
          </Paper>
        </Tabs.Panel>

        {/* Full Logs Tab */}
        <Tabs.Panel value="logs" pt="md">
          <Paper p="md" withBorder>
            <Group justify="space-between" mb="md">
              <Title order={4}>Full Activity Log</Title>
              <ActionIcon variant="light" onClick={fetchSystemData} loading={loading}>
                <IconRefresh size={18} />
              </ActionIcon>
            </Group>

            <ScrollArea h={500}>
              <Table striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Time</Table.Th>
                    <Table.Th>Agent</Table.Th>
                    <Table.Th>Action</Table.Th>
                    <Table.Th>Status</Table.Th>
                    <Table.Th>Details</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {allLogs.map((log) => (
                    <Table.Tr key={`${log.agent}-${log.id}`}>
                      <Table.Td>
                        <Text size="xs" ff="monospace">{formatTime(log.created_at)}</Text>
                      </Table.Td>
                      <Table.Td>
                        <Group gap="xs">
                          <Text>{getAgentEmoji(log.agent)}</Text>
                          <Text size="sm" tt="capitalize">{log.agent}</Text>
                        </Group>
                      </Table.Td>
                      <Table.Td>
                        <Text size="sm">{log.action.replace(/_/g, " ")}</Text>
                      </Table.Td>
                      <Table.Td>
                        <Badge size="xs" color={getStatusColor(log.status)}>
                          {log.status}
                        </Badge>
                      </Table.Td>
                      <Table.Td>
                        <Text size="xs" c="dimmed" style={{ maxWidth: 300, wordBreak: "break-word" }}>
                          {log.details ? (log.details.length > 50 ? log.details.slice(0, 50) + "..." : log.details) : "—"}
                        </Text>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </ScrollArea>
          </Paper>
        </Tabs.Panel>
      </Tabs>
    </Stack>
  );
}
