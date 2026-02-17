"use client";

import { useState, useEffect } from "react";
import { getApiBaseUrl } from "@/lib/api";
import {
  Card,
  Group,
  Stack,
  Text,
  Badge,
  SimpleGrid,
  ThemeIcon,
  Progress,
  Paper,
  Title,
  ActionIcon,
  Tooltip,
  Box,
  Divider,
  List,
  Loader,
  Alert,
  RingProgress,
  Center,
  ScrollArea,
} from "@mantine/core";
import {
  IconRobot,
  IconBrain,
  IconPlugConnected,
  IconMessage,
  IconDatabase,
  IconClock,
  IconRefresh,
  IconCheck,
  IconX,
  IconAlertTriangle,
  IconFileText,
  IconUsers,
  IconBrandWhatsapp,
  IconMail,
  IconCalendar,
  IconActivity,
} from "@tabler/icons-react";

const API_URL = getApiBaseUrl();

interface LiveStatus {
  timestamp: string;
  agents: {
    agents: Record<string, any>;
    stats: { total: number; active: number; available: number };
  };
  secondbrain: {
    status: string;
    stats: { total_notes: number; folders: Record<string, number> };
    recent_notes: Array<{ id: string; folder: string; modified: string }>;
  };
  connectors: {
    connectors: Record<string, any>;
    stats: { total: number; healthy: number };
  };
  chat: {
    active_sessions: number;
    total_messages: number;
  };
  shared_context: {
    status: string;
    sources: Record<string, any>;
  };
  memory: {
    core_files: Record<string, boolean>;
    daily_memory: { total_files: number; today_exists: boolean; today_chars: number };
  };
  scheduled_jobs: {
    active_jobs: number;
    jobs: Array<any>;
  };
}

function StatusBadge({ status }: { status: string }) {
  const color = status === "healthy" || status === "active" ? "green" 
    : status === "available" ? "blue"
    : status === "error" ? "red" 
    : "gray";
  
  return (
    <Badge size="sm" color={color} variant="light">
      {status}
    </Badge>
  );
}

function StatCard({ 
  title, 
  value, 
  icon: Icon, 
  color, 
  subtitle 
}: { 
  title: string; 
  value: string | number; 
  icon: React.ElementType; 
  color: string;
  subtitle?: string;
}) {
  return (
    <Card withBorder p="md" radius="md">
      <Group justify="space-between">
        <div>
          <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
            {title}
          </Text>
          <Text size="xl" fw={700}>
            {value}
          </Text>
          {subtitle && (
            <Text size="xs" c="dimmed">{subtitle}</Text>
          )}
        </div>
        <ThemeIcon size="xl" variant="light" color={color}>
          <Icon size={24} />
        </ThemeIcon>
      </Group>
    </Card>
  );
}

export function LiveSystemDashboard() {
  const [status, setStatus] = useState<LiveStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${API_URL}/api/system/live`);
      if (res.ok) {
        const data = await res.json();
        setStatus(data);
        setLastUpdate(new Date());
        setError(null);
      } else {
        setError("Failed to fetch status");
      }
    } catch (e) {
      setError("Backend offline");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000); // Refresh every 5s
    return () => clearInterval(interval);
  }, []);

  if (loading && !status) {
    return (
      <Center py="xl">
        <Stack align="center" gap="md">
          <Loader size="lg" />
          <Text c="dimmed">Loading system status...</Text>
        </Stack>
      </Center>
    );
  }

  if (error && !status) {
    return (
      <Alert color="red" icon={<IconAlertTriangle />} title="Connection Error">
        {error}. Make sure the backend is running.
      </Alert>
    );
  }

  if (!status) return null;

  const agentStats = status.agents.stats;
  const sbStats = status.secondbrain.stats;
  const connectorStats = status.connectors.stats;

  return (
    <Stack gap="md">
      {/* Header with refresh */}
      <Group justify="space-between">
        <Group gap="xs">
          <ThemeIcon size="lg" variant="light" color="green">
            <IconActivity size={20} />
          </ThemeIcon>
          <div>
            <Text fw={600}>Live System Status</Text>
            <Text size="xs" c="dimmed">
              Last updated: {lastUpdate?.toLocaleTimeString() || "—"}
            </Text>
          </div>
        </Group>
        <Tooltip label="Refresh now">
          <ActionIcon variant="light" onClick={fetchStatus} loading={loading}>
            <IconRefresh size={18} />
          </ActionIcon>
        </Tooltip>
      </Group>

      {/* Quick Stats */}
      <SimpleGrid cols={{ base: 2, sm: 4 }}>
        <StatCard
          title="Agents"
          value={`${agentStats.active}/${agentStats.total}`}
          icon={IconRobot}
          color="blue"
          subtitle={`${agentStats.available} available`}
        />
        <StatCard
          title="SecondBrain"
          value={sbStats.total_notes}
          icon={IconBrain}
          color="violet"
          subtitle="notes in vault"
        />
        <StatCard
          title="Connectors"
          value={`${connectorStats.healthy}/${connectorStats.total}`}
          icon={IconPlugConnected}
          color="green"
          subtitle="healthy"
        />
        <StatCard
          title="Chat Messages"
          value={status.chat.total_messages}
          icon={IconMessage}
          color="cyan"
          subtitle={`${status.chat.active_sessions} sessions`}
        />
      </SimpleGrid>

      {/* Detail Sections */}
      <SimpleGrid cols={{ base: 1, md: 2 }}>
        {/* Agents */}
        <Card withBorder p="md" radius="md">
          <Group justify="space-between" mb="md">
            <Group gap="xs">
              <IconRobot size={20} />
              <Title order={5}>Agents</Title>
            </Group>
            <Badge color="blue" variant="light">
              {agentStats.active} active
            </Badge>
          </Group>
          <Stack gap="xs">
            {Object.entries(status.agents.agents).map(([name, agent]) => (
              <Group key={name} justify="space-between">
                <Group gap="xs">
                  <Text size="sm" fw={500} tt="capitalize">{name}</Text>
                </Group>
                <Group gap="xs">
                  <StatusBadge status={agent.status} />
                  {agent.loaded && (
                    <Badge size="xs" variant="outline" color="green">loaded</Badge>
                  )}
                </Group>
              </Group>
            ))}
          </Stack>
        </Card>

        {/* SecondBrain Vault */}
        <Card withBorder p="md" radius="md">
          <Group justify="space-between" mb="md">
            <Group gap="xs">
              <IconBrain size={20} />
              <Title order={5}>SecondBrain Vault</Title>
            </Group>
            <StatusBadge status={status.secondbrain.status} />
          </Group>
          
          <SimpleGrid cols={3} mb="md">
            {Object.entries(sbStats.folders).slice(0, 6).map(([folder, count]) => (
              <Paper key={folder} p="xs" withBorder radius="sm">
                <Text size="xs" c="dimmed">{folder}/</Text>
                <Text fw={600}>{count}</Text>
              </Paper>
            ))}
          </SimpleGrid>
          
          <Text size="xs" c="dimmed" mb="xs">Recent Notes:</Text>
          <Stack gap={4}>
            {status.secondbrain.recent_notes.slice(0, 3).map((note) => (
              <Group key={note.id} justify="space-between">
                <Text size="xs" ff="monospace">{note.id}</Text>
                <Text size="xs" c="dimmed">{note.folder}</Text>
              </Group>
            ))}
          </Stack>
        </Card>

        {/* Connectors */}
        <Card withBorder p="md" radius="md">
          <Group justify="space-between" mb="md">
            <Group gap="xs">
              <IconPlugConnected size={20} />
              <Title order={5}>Connectors</Title>
            </Group>
          </Group>
          <Stack gap="sm">
            {Object.entries(status.connectors.connectors).map(([name, conn]) => (
              <Group key={name} justify="space-between">
                <Group gap="xs">
                  {name === "whatsapp" && <IconBrandWhatsapp size={16} color="green" />}
                  {name === "gmail" && <IconMail size={16} color="red" />}
                  {name === "calendar" && <IconCalendar size={16} color="blue" />}
                  <Text size="sm" fw={500} tt="capitalize">{name}</Text>
                </Group>
                <Group gap="xs">
                  <StatusBadge status={conn.status} />
                  {conn.contacts_loaded && (
                    <Badge size="xs" variant="outline">
                      {conn.contacts_loaded} contacts
                    </Badge>
                  )}
                </Group>
              </Group>
            ))}
          </Stack>
        </Card>

        {/* Shared Context */}
        <Card withBorder p="md" radius="md">
          <Group justify="space-between" mb="md">
            <Group gap="xs">
              <IconDatabase size={20} />
              <Title order={5}>Shared Context</Title>
            </Group>
            <StatusBadge status={status.shared_context.status} />
          </Group>
          
          <Stack gap="xs">
            {status.shared_context.sources && (
              <>
                <Group justify="space-between">
                  <Text size="sm">User Profile</Text>
                  <Badge size="xs" color={status.shared_context.sources.user_profile ? "green" : "gray"}>
                    {status.shared_context.sources.user_profile_chars || 0} chars
                  </Badge>
                </Group>
                <Group justify="space-between">
                  <Text size="sm">Long-term Memory</Text>
                  <Badge size="xs" color={status.shared_context.sources.long_term_memory ? "green" : "gray"}>
                    {status.shared_context.sources.memory_chars || 0} chars
                  </Badge>
                </Group>
                <Group justify="space-between">
                  <Text size="sm">Contacts</Text>
                  <Badge size="xs" color="blue">
                    {status.shared_context.sources.contacts || 0}
                  </Badge>
                </Group>
                <Group justify="space-between">
                  <Text size="sm">Recent Memory</Text>
                  <Badge size="xs" color="violet">
                    {status.shared_context.sources.recent_memory_days || 0} days
                  </Badge>
                </Group>
              </>
            )}
          </Stack>
        </Card>

        {/* Memory Files */}
        <Card withBorder p="md" radius="md">
          <Group justify="space-between" mb="md">
            <Group gap="xs">
              <IconFileText size={20} />
              <Title order={5}>Memory Files</Title>
            </Group>
          </Group>
          
          <Stack gap="xs">
            {Object.entries(status.memory.core_files).map(([file, exists]) => (
              <Group key={file} justify="space-between">
                <Text size="sm" ff="monospace">{file}</Text>
                <ThemeIcon size="sm" variant="light" color={exists ? "green" : "red"}>
                  {exists ? <IconCheck size={12} /> : <IconX size={12} />}
                </ThemeIcon>
              </Group>
            ))}
            <Divider my="xs" />
            <Group justify="space-between">
              <Text size="sm">Daily Memory Files</Text>
              <Badge size="xs">{status.memory.daily_memory.total_files}</Badge>
            </Group>
            <Group justify="space-between">
              <Text size="sm">Today's Memory</Text>
              <Badge size="xs" color={status.memory.daily_memory.today_exists ? "green" : "gray"}>
                {status.memory.daily_memory.today_chars} chars
              </Badge>
            </Group>
          </Stack>
        </Card>

        {/* Scheduled Jobs */}
        <Card withBorder p="md" radius="md">
          <Group justify="space-between" mb="md">
            <Group gap="xs">
              <IconClock size={20} />
              <Title order={5}>Scheduled Jobs</Title>
            </Group>
            <Badge color="blue" variant="light">
              {status.scheduled_jobs.active_jobs} active
            </Badge>
          </Group>
          
          {status.scheduled_jobs.jobs.length > 0 ? (
            <Stack gap="xs">
              {status.scheduled_jobs.jobs.slice(0, 5).map((job) => (
                <Group key={job.id} justify="space-between">
                  <Text size="sm">{job.name}</Text>
                  <Text size="xs" c="dimmed" ff="monospace">{job.schedule}</Text>
                </Group>
              ))}
            </Stack>
          ) : (
            <Text size="sm" c="dimmed" ta="center">No scheduled jobs</Text>
          )}
        </Card>
      </SimpleGrid>
    </Stack>
  );
}
