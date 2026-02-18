"use client";

import { useState, useEffect, useMemo, type ReactNode } from "react";
import { getApiBaseUrl, IndicatorDiagnostic } from "@/lib/api";
import { useIndicatorDiagnostics } from "@/lib/hooks";
import {
  Card,
  Button,
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
  IconDatabase,
  IconClock,
  IconRefresh,
  IconCheck,
  IconX,
  IconAlertTriangle,
  IconFileText,
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
  household_heartbeat?: {
    last_run?: string | null;
    next_due?: string | null;
    open_findings?: number;
    last_consolidation?: string | null;
    error?: string;
  };
}

function StatusBadge({ status }: { status: string }) {
  const color = status === "healthy" || status === "active" ? "green" 
    : status === "available" ? "blue"
    : status === "warning" ? "yellow"
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
    <Card withBorder p="md" radius="md" className="live-stat-card">
      <Group justify="space-between">
        <div>
          <Text size="xs" c="dimmed" tt="uppercase" fw={600} className="live-stat-title">
            {title}
          </Text>
          <Text size="xl" fw={700} className="live-stat-value">
            {value}
          </Text>
          {subtitle && (
            <Text size="xs" c="dimmed" className="live-stat-subtitle">{subtitle}</Text>
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
  const [heartbeatRunning, setHeartbeatRunning] = useState(false);
  const indicatorDiagnostics = useIndicatorDiagnostics(60000);
  const indicatorIndex = useMemo(() => {
    const map = new Map<string, IndicatorDiagnostic>();
    indicatorDiagnostics.data?.results?.forEach((item) => {
      map.set(item.id, item);
    });
    return map;
  }, [indicatorDiagnostics.data]);
  const indicatorLookup = (id: string) => indicatorIndex.get(id);
  const indicatorTooltip = (meta?: IndicatorDiagnostic) =>
    meta
      ? `${meta.label} • ${meta.status.toUpperCase()}${meta.last_updated ? ` • Updated ${new Date(meta.last_updated).toLocaleString()}` : ""}${meta.source ? ` • Source: ${meta.source}` : ""}`
      : "";
  const wrapIndicator = (node: ReactNode, meta?: IndicatorDiagnostic) =>
    meta ? (
      <Tooltip label={indicatorTooltip(meta)} withArrow>
        <Box>{node}</Box>
      </Tooltip>
    ) : (
      <>{node}</>
    );

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

  const agentStats = status?.agents?.stats ?? { total: 0, active: 0, available: 0 };
  const agentMap = status?.agents?.agents ?? {};
  const sbStats = status?.secondbrain?.stats ?? { total_notes: 0, folders: {} as Record<string, number> };
  const sbStatus = status?.secondbrain?.status ?? "unavailable";
  const sbRecent = status?.secondbrain?.recent_notes ?? [];
  const connectorStats = status?.connectors?.stats ?? { total: 0, healthy: 0 };
  const connectorMap = status?.connectors?.connectors ?? {};
  const sharedContext = status?.shared_context ?? { status: "unavailable", sources: {} as Record<string, any> };
  const sharedSources = sharedContext.sources || {};
  const memory = status?.memory ?? { core_files: {} as Record<string, boolean>, daily_memory: { total_files: 0, today_exists: false, today_chars: 0 } };
  const scheduled = status?.scheduled_jobs ?? { active_jobs: 0, jobs: [] as Array<any> };
  const heartbeat = status?.household_heartbeat ?? {
    last_run: null,
    next_due: null,
    open_findings: 0,
    last_consolidation: null,
  };
  const heartbeatStatus =
    heartbeat.error
      ? "error"
      : (heartbeat.open_findings || 0) > 0
        ? "warning"
        : heartbeat.last_run
          ? "healthy"
          : "idle";
  const monitorMetrics = status?.system_monitor ?? {
    cpu_usage: null,
    memory_usage: null,
    disk_usage: null,
    uptime: null,
  };
  const cpuMeta = indicatorLookup("system.monitor.cpu");
  const memoryMeta = indicatorLookup("system.monitor.memory");
  const diskMeta = indicatorLookup("system.monitor.disk");
  const uptimeMeta = indicatorLookup("system.monitor.uptime");
  const cpuValue = typeof cpuMeta?.value === "number" ? cpuMeta.value : monitorMetrics.cpu_usage;
  const memoryValue = typeof memoryMeta?.value === "number" ? memoryMeta.value : monitorMetrics.memory_usage;
  const diskValue = typeof diskMeta?.value === "number" ? diskMeta.value : monitorMetrics.disk_usage;
  const uptimeValue = typeof uptimeMeta?.value === "number" ? uptimeMeta.value : monitorMetrics.uptime;

  const runHeartbeatNow = async () => {
    setHeartbeatRunning(true);
    try {
      await fetch(`${API_URL}/api/heartbeat/household/run`, { method: "POST" });
      fetchStatus();
    } catch (e) {
      // Keep quiet; error shows in status refresh
    } finally {
      setHeartbeatRunning(false);
    }
  };

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
      <SimpleGrid cols={{ base: 2, sm: 4 }} className="live-stat-grid">
        <StatCard
          title="Agents"
          value={`${agentStats.active}/${agentStats.total}`}
          icon={IconRobot}
          color="blue"
          subtitle={`${agentStats.available} available`}
        />
        {wrapIndicator(
          <StatCard
            title="SecondBrain"
            value={sbStats.total_notes}
            icon={IconBrain}
            color="violet"
            subtitle="notes in vault"
          />,
          indicatorLookup("dashboard.identity.ready")
        )}
        <StatCard
          title="Connectors"
          value={`${connectorStats.healthy}/${connectorStats.total}`}
          icon={IconPlugConnected}
          color="green"
          subtitle="healthy"
        />
        <StatCard
          title="Heartbeat"
          value={heartbeat.open_findings || 0}
          icon={IconActivity}
          color={heartbeatStatus === "error" ? "red" : heartbeatStatus === "warning" ? "yellow" : "teal"}
          subtitle={heartbeat.last_run ? "open findings" : "not run yet"}
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
            {Object.entries(agentMap).map(([name, agent]) => (
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

        {/* System Monitor */}
        <Card withBorder p="md" radius="md">
          <Group justify="space-between" mb="md">
            <Group gap="xs">
              <IconActivity size={20} />
              <Title order={5}>System Monitor</Title>
            </Group>
            <StatusBadge status={cpuValue || memoryValue ? "healthy" : "idle"} />
          </Group>
          <Stack gap="xs">
            {wrapIndicator(
              <Group justify="space-between">
                <Text size="sm">CPU usage</Text>
                <Badge size="xs" color={typeof cpuValue === "number" ? "green" : "gray"}>
                  {typeof cpuValue === "number" ? `${Math.round(cpuValue)}%` : "—"}
                </Badge>
              </Group>,
              indicatorLookup("system.monitor.cpu")
            )}
            {wrapIndicator(
              <Group justify="space-between">
                <Text size="sm">Memory usage</Text>
                <Badge size="xs" color={typeof memoryValue === "number" ? "green" : "gray"}>
                  {typeof memoryValue === "number" ? `${Math.round(memoryValue)}%` : "—"}
                </Badge>
              </Group>,
              indicatorLookup("system.monitor.memory")
            )}
            {wrapIndicator(
              <Group justify="space-between">
                <Text size="sm">Disk usage</Text>
                <Badge size="xs" color={typeof diskValue === "number" ? "green" : "gray"}>
                  {typeof diskValue === "number" ? `${Math.round(diskValue)}%` : "—"}
                </Badge>
              </Group>,
              indicatorLookup("system.monitor.disk")
            )}
            {wrapIndicator(
              <Group justify="space-between">
                <Text size="sm">Uptime</Text>
                <Badge size="xs" color={typeof uptimeValue === "number" ? "blue" : "gray"}>
                  {typeof uptimeValue === "number" ? `${Math.round(uptimeValue / 3600)}h` : "—"}
                </Badge>
              </Group>,
              indicatorLookup("system.monitor.uptime")
            )}
          </Stack>
        </Card>

        {/* SecondBrain Vault */}
        <Card withBorder p="md" radius="md">
          <Group justify="space-between" mb="md">
            <Group gap="xs">
              <IconBrain size={20} />
              <Title order={5}>SecondBrain Vault</Title>
            </Group>
            <StatusBadge status={sbStatus} />
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
            {sbRecent.slice(0, 3).map((note) => (
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
            {Object.entries(connectorMap).map(([name, conn]) => (
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
            <StatusBadge status={sharedContext.status} />
          </Group>
          
          <Stack gap="xs">
            {sharedSources && (
              <>
                <Group justify="space-between">
                  <Text size="sm">User Profile</Text>
                  <Badge size="xs" color={sharedSources.user_profile ? "green" : "gray"}>
                    {sharedSources.user_profile_chars || 0} chars
                  </Badge>
                </Group>
                <Group justify="space-between">
                  <Text size="sm">Long-term Memory</Text>
                  <Badge size="xs" color={sharedSources.long_term_memory ? "green" : "gray"}>
                    {sharedSources.memory_chars || 0} chars
                  </Badge>
                </Group>
                <Group justify="space-between">
                  <Text size="sm">Contacts</Text>
                  <Badge size="xs" color="blue">
                    {sharedSources.contacts || 0}
                  </Badge>
                </Group>
                <Group justify="space-between">
                  <Text size="sm">Recent Memory</Text>
                  <Badge size="xs" color="violet">
                    {sharedSources.recent_memory_days || 0} days
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
            {Object.entries(memory.core_files).map(([file, exists]) => (
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
              <Badge size="xs">{memory.daily_memory.total_files}</Badge>
            </Group>
            <Group justify="space-between">
              <Text size="sm">Today's Memory</Text>
              <Badge size="xs" color={memory.daily_memory.today_exists ? "green" : "gray"}>
                {memory.daily_memory.today_chars} chars
              </Badge>
            </Group>
          </Stack>
        </Card>

        {/* Household Heartbeat */}
        <Card withBorder p="md" radius="md">
          <Group justify="space-between" mb="md">
            <Group gap="xs">
              <ThemeIcon variant="light" color="primary" size="sm" radius="md">
                <IconActivity size={14} />
              </ThemeIcon>
              <Text fw={600} size="sm">
                Household Heartbeat
              </Text>
            </Group>
            <StatusBadge status={heartbeatStatus} />
          </Group>
          <Stack gap="xs">
            <Group justify="space-between">
              <Text size="sm">Last run</Text>
              <Text size="xs" c="dimmed">
                {heartbeat.last_run ? new Date(heartbeat.last_run).toLocaleString() : "—"}
              </Text>
            </Group>
            <Group justify="space-between">
              <Text size="sm">Next check due</Text>
              <Text size="xs" c="dimmed">
                {heartbeat.next_due ? new Date(heartbeat.next_due).toLocaleString() : "—"}
              </Text>
            </Group>
            <Group justify="space-between">
              <Text size="sm">Open findings</Text>
              <Badge size="xs" color={(heartbeat.open_findings || 0) > 0 ? "yellow" : "green"}>
                {heartbeat.open_findings || 0}
              </Badge>
            </Group>
            <Group justify="space-between">
              <Text size="sm">Last consolidation</Text>
              <Text size="xs" c="dimmed">
                {heartbeat.last_consolidation ? new Date(heartbeat.last_consolidation).toLocaleString() : "—"}
              </Text>
            </Group>
            <Group justify="flex-end" mt="xs">
              <Button
                size="xs"
                variant="light"
                leftSection={<IconRefresh size={14} />}
                loading={heartbeatRunning}
                onClick={runHeartbeatNow}
              >
                Run now
              </Button>
            </Group>
          </Stack>
        </Card>

        {/* Scheduled Jobs */}
        <Card withBorder p="md" radius="md">
          <Group justify="space-between" mb="md">
            <Group gap="xs">
              <ThemeIcon variant="light" color="primary" size="sm" radius="md">
                <IconClock size={14} />
              </ThemeIcon>
              <Text fw={600} size="sm">
                Scheduled Jobs
              </Text>
            </Group>
            <Badge color="blue" variant="light">
              {scheduled.active_jobs} active
            </Badge>
          </Group>
          
          {scheduled.jobs.length > 0 ? (
            <Stack gap="xs">
              {scheduled.jobs.slice(0, 5).map((job) => (
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
