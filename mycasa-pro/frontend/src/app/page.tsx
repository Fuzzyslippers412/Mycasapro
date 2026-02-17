"use client";

import { useEffect, useState } from "react";
import type { ElementType } from "react";
import { useRouter } from "next/navigation";
import { Shell } from "@/components/layout/Shell";
import { Page } from "@/components/layout/Page";
import {
  Alert,
  Avatar,
  Badge,
  Box,
  Button,
  Card,
  Center,
  Group,
  ScrollArea,
  SimpleGrid,
  Skeleton,
  Stack,
  Text,
  ThemeIcon,
} from "@mantine/core";
import {
  IconActivity,
  IconAlertCircle,
  IconAlertTriangle,
  IconChecklist,
  IconCircleCheck,
  IconClock,
  IconInbox,
  IconPlus,
  IconRefresh,
  IconRobot,
  IconSettings,
  IconShieldLock,
  IconSparkles,
  IconWallet,
  IconX,
} from "@tabler/icons-react";
import { useAuth } from "@/contexts/AuthContext";
import { apiFetch, getApiBaseUrl } from "@/lib/api";
import { useDashboardData, useJanitorWizardHistory, useSystemStatus } from "@/lib/hooks";
import { tokens } from "@/theme/tokens";

// Types from API
interface Activity {
  id: number;
  title: string;
  description?: string;
  time: string;
  type: "success" | "warning" | "info" | "error";
  agent?: string;
}

function StatusHeader({
  userName = "there",
  pendingTasks,
  unreadMessages,
  portfolioChange,
  loading,
  isOnline,
  janitorRun,
  janitorLoading,
  janitorError,
  onAddTask,
  onInbox,
  onJanitor,
}: {
  userName?: string;
  pendingTasks: number | null;
  unreadMessages: number | null;
  portfolioChange: number | null;
  loading: boolean;
  isOnline: boolean;
  janitorRun: { health_score: number; findings_count: number; status: string; timestamp: string } | null;
  janitorLoading: boolean;
  janitorError: boolean;
  onAddTask: () => void;
  onInbox: () => void;
  onJanitor: () => void;
}) {
  const [greeting, setGreeting] = useState("Welcome");

  useEffect(() => {
    const hour = new Date().getHours();
    if (hour < 12) setGreeting("Good morning");
    else if (hour < 17) setGreeting("Good afternoon");
    else setGreeting("Good evening");
  }, []);

  const hasCounts = typeof pendingTasks === "number" && typeof unreadMessages === "number";
  const headline = !isOnline
    ? "Backend offline"
    : loading
      ? "Checking system status"
      : !hasCounts
        ? "System data unavailable"
        : pendingTasks === 0 && unreadMessages === 0
          ? "Your home is running smoothly"
          : "You have items that need attention";

  const badgeLabel = loading
    ? "Checking"
    : !hasCounts
      ? "Unavailable"
      : pendingTasks === 0 && unreadMessages === 0
        ? "All clear"
        : "Needs attention";

  const badgeColor = loading || !hasCounts
    ? "gray"
    : pendingTasks === 0 && unreadMessages === 0
      ? "success"
      : "warning";

  const janitorLabel = janitorLoading
    ? "Janitor audit loading"
    : janitorError
      ? "Janitor unavailable"
      : janitorRun
        ? `Janitor ${janitorRun.health_score}% • ${janitorRun.findings_count} findings`
        : "Janitor not run";

  const portfolioLabel =
    portfolioChange === null
      ? "Portfolio change unavailable"
      : `Portfolio ${portfolioChange >= 0 ? "+" : ""}${portfolioChange.toFixed(1)}%`;

  const MetricItem = ({ icon: Icon, text }: { icon: ElementType; text: string }) => (
    <Group gap={6} wrap="nowrap">
      <ThemeIcon variant="light" size="sm" radius="md" color="primary">
        <Icon size={14} />
      </ThemeIcon>
      <Text size="sm">{text}</Text>
    </Group>
  );

  return (
    <Card radius="lg" withBorder padding="md" className="status-hero">
      <Group justify="space-between" align="flex-start" wrap="wrap">
        <Stack gap={6} style={{ flex: 1, minWidth: 260 }}>
          <Text size="sm" c="dimmed">
            {greeting}, {userName}
          </Text>
          <Group gap="xs" align="center" wrap="wrap">
            <Text fw={600} size="lg">
              {headline}
            </Text>
            <Badge size="sm" variant="light" color={badgeColor}>
              {badgeLabel}
            </Badge>
          </Group>
          <Group gap="md" mt="xs" wrap="wrap">
            {loading ? (
              <>
                <Skeleton width={140} height={18} />
                <Skeleton width={160} height={18} />
                <Skeleton width={160} height={18} />
              </>
            ) : (
              <>
                <MetricItem
                  icon={IconChecklist}
                  text={
                    typeof pendingTasks === "number"
                      ? `${pendingTasks} tasks pending`
                      : "Tasks unavailable"
                  }
                />
                <MetricItem
                  icon={IconInbox}
                  text={
                    typeof unreadMessages === "number"
                      ? `${unreadMessages} messages unread`
                      : "Messages unavailable"
                  }
                />
                <MetricItem icon={IconActivity} text={portfolioLabel} />
                <MetricItem icon={IconSparkles} text={janitorLabel} />
              </>
            )}
          </Group>
        </Stack>
        <Group gap="xs" mt="xs" wrap="wrap">
          <Button
            variant="light"
            size="xs"
            leftSection={<IconPlus size={14} />}
            onClick={onAddTask}
          >
            Add task
          </Button>
          <Button
            variant="light"
            size="xs"
            leftSection={<IconInbox size={14} />}
            onClick={onInbox}
          >
            Inbox
          </Button>
          <Button
            variant="light"
            size="xs"
            leftSection={<IconSparkles size={14} />}
            onClick={onJanitor}
          >
            Janitor
          </Button>
        </Group>
      </Group>
    </Card>
  );
}

function KpiCard({
  title,
  value,
  subtitle,
  icon: Icon,
  loading,
  color = "primary",
  onClick,
}: {
  title: string;
  value: string;
  subtitle: string;
  icon: ElementType;
  loading: boolean;
  color?: string;
  onClick?: () => void;
}) {
  return (
    <Card
      radius="lg"
      withBorder
      onClick={onClick}
      className="kpi-card"
      style={{ cursor: onClick ? "pointer" : "default" }}
    >
      <Group justify="space-between" align="flex-start">
        <Stack gap={4}>
          <Text size="sm" c="dimmed">
            {title}
          </Text>
          {loading ? (
            <Skeleton height={18} width={80} />
          ) : (
            <Text fw={700} size="lg">
              {value}
            </Text>
          )}
          <Text size="xs" c="dimmed">
            {subtitle}
          </Text>
        </Stack>
        <ThemeIcon variant="light" color={color} radius="md">
          <Icon size={18} />
        </ThemeIcon>
      </Group>
    </Card>
  );
}

function ActivityFeed({
  activities,
  loading,
  onRefresh,
}: {
  activities: Activity[];
  loading: boolean;
  onRefresh: () => void;
}) {
  const getActivityIcon = (type: Activity["type"]) => {
    switch (type) {
      case "success":
        return <IconCircleCheck size={14} />;
      case "warning":
        return <IconAlertTriangle size={14} />;
      case "error":
        return <IconX size={14} />;
      default:
        return <IconActivity size={14} />;
    }
  };

  const getActivityColor = (type: Activity["type"]) => {
    switch (type) {
      case "success":
        return tokens.colors.success[500];
      case "warning":
        return tokens.colors.warn[500];
      case "error":
        return tokens.colors.error[500];
      default:
        return tokens.colors.primary[500];
    }
  };

  return (
    <Card radius="lg" withBorder padding="md" className="activity-card">
      <Group justify="space-between" mb="md">
        <Group gap="xs">
          <ThemeIcon variant="light" color="primary" size="sm" radius="md">
            <IconActivity size={14} />
          </ThemeIcon>
          <Text fw={600} size="sm">
            Recent Activity
          </Text>
        </Group>
        <Button variant="light" size="xs" leftSection={<IconRefresh size={14} />} onClick={onRefresh}>
          Refresh
        </Button>
      </Group>

      {loading ? (
        <Stack gap="sm">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} height={50} />
          ))}
        </Stack>
      ) : activities.length === 0 ? (
        <Center py="lg">
          <Stack gap={6} align="center">
            <IconClock size={28} stroke={1.5} style={{ color: "var(--mantine-color-dimmed)" }} />
            <Text c="dimmed" size="sm">
              No recent activity
            </Text>
          </Stack>
        </Center>
      ) : (
        <ScrollArea h={320}>
          <Stack gap={0}>
            {activities.map((activity, index) => (
              <Box
                key={activity.id}
                py="sm"
                style={{
                  borderBottom:
                    index < activities.length - 1 ? "1px solid var(--border-1)" : undefined,
                }}
              >
                <Group gap="sm" align="flex-start">
                  <Box
                    style={{
                      width: 24,
                      height: 24,
                      borderRadius: "50%",
                      backgroundColor: getActivityColor(activity.type),
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      color: "white",
                      flexShrink: 0,
                    }}
                  >
                    {getActivityIcon(activity.type)}
                  </Box>
                  <Stack gap={2} style={{ flex: 1 }}>
                    <Group gap="xs" justify="space-between" wrap="wrap">
                      <Text size="sm" fw={600}>
                        {activity.title}
                      </Text>
                      <Badge size="xs" variant="light">
                        {activity.type}
                      </Badge>
                    </Group>
                    {activity.description && (
                      <Text size="xs" c="dimmed">
                        {activity.description}
                      </Text>
                    )}
                    <Group gap="xs">
                      <IconClock size={12} style={{ opacity: 0.5 }} />
                      <Text size="xs" c="dimmed">
                        {activity.time}
                      </Text>
                      {activity.agent && (
                        <Badge size="xs" variant="light">
                          {activity.agent}
                        </Badge>
                      )}
                    </Group>
                  </Stack>
                </Group>
              </Box>
            ))}
          </Stack>
        </ScrollArea>
      )}
    </Card>
  );
}

function AgentCard({
  agent,
  onClick,
}: {
  agent: { id: string; name: string; status: string; description: string };
  onClick: () => void;
}) {
  const statusColors: Record<string, string> = {
    online: tokens.colors.success[500],
    running: tokens.colors.success[500],
    busy: tokens.colors.warn[500],
    offline: tokens.colors.neutral[400],
    not_loaded: tokens.colors.neutral[400],
    idle: tokens.colors.primary[400],
  };

  const displayStatus = agent.status === "not_loaded" ? "idle" : agent.status;

  return (
    <Card withBorder p="sm" radius="md" className="agent-card" style={{ cursor: "pointer" }} onClick={onClick}>
      <Group justify="space-between" align="center">
        <Group gap="sm">
          <Avatar
            size="sm"
            color={displayStatus === "online" || displayStatus === "running" ? "primary" : "gray"}
            radius="xl"
          >
            <IconRobot size={16} />
          </Avatar>
          <Stack gap={2}>
            <Text size="sm" fw={600}>
              {agent.name}
            </Text>
            <Text size="xs" c="dimmed" lineClamp={2}>
              {agent.description}
            </Text>
          </Stack>
        </Group>
        <Badge
          size="xs"
          variant="light"
          color={
            displayStatus === "online" || displayStatus === "running"
              ? "success"
              : displayStatus === "busy"
                ? "warning"
                : "gray"
          }
        >
          {displayStatus}
        </Badge>
      </Group>
    </Card>
  );
}

function SystemHealthCard({
  status,
  loading,
  error,
}: {
  status: { cpu_usage: number; memory_usage: number; disk_usage: number; uptime: number } | null;
  loading: boolean;
  error: Error | null;
}) {
  const rows = [
    { label: "CPU usage", value: formatPercent(status?.cpu_usage) },
    { label: "Memory usage", value: formatPercent(status?.memory_usage) },
    { label: "Disk usage", value: formatPercent(status?.disk_usage) },
    { label: "Uptime", value: formatUptime(status?.uptime) },
  ];

  return (
    <Card radius="lg" withBorder padding="md" className="system-health-card">
      <Group justify="space-between" mb="md">
        <Group gap="xs">
          <ThemeIcon variant="light" color="primary" size="sm" radius="md">
            <IconShieldLock size={14} />
          </ThemeIcon>
          <Text fw={600} size="sm">
            System Health
          </Text>
        </Group>
        <Badge size="sm" variant="light" color={error ? "gray" : "success"}>
          {error ? "Offline" : "Live"}
        </Badge>
      </Group>

      {error ? (
        <Text size="sm" c="dimmed">
          System metrics unavailable right now.
        </Text>
      ) : (
        <Stack gap="xs">
          {rows.map((row) => (
            <Group key={row.label} justify="space-between">
              <Text size="sm" c="dimmed">
                {row.label}
              </Text>
              {loading ? (
                <Skeleton height={12} width={60} />
              ) : (
                <Text size="sm" fw={600}>
                  {row.value}
                </Text>
              )}
            </Group>
          ))}
        </Stack>
      )}
    </Card>
  );
}

export default function HomePage() {
  const router = useRouter();
  const { user } = useAuth();
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(true);
  const {
    status,
    tasks,
    bills,
    unreadCount,
    loading,
    error,
    statusError,
    tasksError,
    billsError,
    unreadError,
    degraded,
    refetch,
  } = useDashboardData(30000, autoRefreshEnabled);
  const janitorHistory = useJanitorWizardHistory(1);
  const janitorRun = janitorHistory.data?.runs?.[0] || null;
  const janitorLoading = janitorHistory.loading;
  const janitorError = Boolean(janitorHistory.error);
  const systemStatus = useSystemStatus(30000);
  const [portfolioChange, setPortfolioChange] = useState<number | null>(null);
  const [portfolioLoading, setPortfolioLoading] = useState(true);
  const apiBase = getApiBaseUrl();
  const isOnline = !statusError;
  const statusErrorStatus = (statusError as any)?.status;
  const statusErrorDetail = (statusError as any)?.detail;

  useEffect(() => {
    let active = true;
    const fetchAutoRefresh = async () => {
      try {
        const data = await apiFetch<any>("/api/settings/system");
        if (active && typeof data.auto_refresh === "boolean") {
          setAutoRefreshEnabled(data.auto_refresh);
        }
      } catch {
        // ignore
      } finally {
        // no-op
      }
    };
    fetchAutoRefresh();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const handler = () => {
      apiFetch<any>("/api/settings/system")
        .then((data) => {
          if (typeof data.auto_refresh === "boolean") setAutoRefreshEnabled(data.auto_refresh);
        })
        .catch(() => {});
    };
    window.addEventListener("mycasa-settings-sync", handler as EventListener);
    return () => window.removeEventListener("mycasa-settings-sync", handler as EventListener);
  }, []);

  useEffect(() => {
    let active = true;
    const fetchPortfolio = async () => {
      try {
        const data = await apiFetch<any>("/portfolio");
        const direct = typeof data?.day_change_pct === "number" ? data.day_change_pct : null;
        if (direct !== null && Number.isFinite(direct)) {
          if (active) setPortfolioChange(direct);
        } else {
          const holdings = data?.holdings || [];
          const totalValue = holdings.reduce((sum: number, h: any) => sum + (h.value || 0), 0);
          const dayChange = holdings.reduce((sum: number, h: any) => {
            const pct =
              typeof h.change_pct === "number"
                ? h.change_pct
                : typeof h.changePercent === "number"
                  ? h.changePercent
                  : null;
            if (pct === null || typeof h.value !== "number") return sum;
            return sum + (h.value * pct) / 100;
          }, 0);
          const pct = totalValue > 0 ? (dayChange / totalValue) * 100 : null;
          if (active) {
            setPortfolioChange(typeof pct === "number" && Number.isFinite(pct) ? pct : null);
          }
        }
      } catch {
        if (active) setPortfolioChange(null);
      } finally {
        if (active) setPortfolioLoading(false);
      }
    };
    fetchPortfolio();
    return () => {
      active = false;
    };
  }, []);

  const activities: Activity[] = [];

  const statusData = statusError ? null : status;
  if (statusData?.facts?.recent_changes) {
    statusData.facts.recent_changes.slice(0, 5).forEach((change, index) => {
      const timeAgo = formatTimeAgo(change.time);
      activities.push({
        id: index + 1,
        title: formatAction(change.action),
        description: change.details,
        time: timeAgo,
        type: change.status === "success" ? "success" : change.status === "error" ? "error" : "info",
        agent: change.agent,
      });
    });
  }

  const agentList = statusData?.facts?.agents
    ? Object.entries(statusData.facts.agents).map(([id, data]) => ({
        id,
        name: getAgentName(id),
        status: data.state || "offline",
        description: getAgentDescription(id),
      }))
    : [];

  const pendingTaskCount = loading || tasksError ? null : tasks?.length ?? null;
  const unreadMessageCount = loading || unreadError ? null : unreadCount?.total ?? null;
  const upcomingBillsTotal = loading || billsError
    ? null
    : bills?.reduce((sum: number, b: any) => sum + (b.amount || 0), 0) ?? null;

  const onlineAgents = agentList.filter(
    (a) => a.status === "online" || a.status === "running"
  ).length;

  return (
    <Shell>
      <Page title="Dashboard" subtitle="Your AI-powered home operating system">
        <Stack gap="lg" pb={100}>
          {error && (
            <Alert icon={<IconAlertCircle size={16} />} title="Connection Error" color="red" radius="md">
              <Group justify="space-between" align="center" wrap="wrap">
                <Text size="sm">
                  {typeof statusErrorStatus === "number"
                    ? `Backend error (${statusErrorStatus}). ${statusErrorDetail || "Please retry."}`
                    : `Unable to reach backend at ${apiBase}. Check the server and try again.`}
                </Text>
                <Button
                  size="xs"
                  variant="light"
                  color="red"
                  leftSection={<IconRefresh size={14} />}
                  onClick={refetch}
                >
                  Retry
                </Button>
              </Group>
            </Alert>
          )}
          {!error && degraded && (
            <Alert icon={<IconAlertTriangle size={16} />} title="Partial Data" color="yellow" radius="md">
              <Group justify="space-between" align="center" wrap="wrap">
                <Text size="sm">
                  Some sources are unavailable right now. Your data will refresh when they recover.
                </Text>
                <Button
                  size="xs"
                  variant="light"
                  color="yellow"
                  leftSection={<IconRefresh size={14} />}
                  onClick={refetch}
                >
                  Retry
                </Button>
              </Group>
            </Alert>
          )}

          <StatusHeader
            userName={user?.username || "there"}
            pendingTasks={pendingTaskCount}
            unreadMessages={unreadMessageCount}
            portfolioChange={portfolioChange}
            loading={loading || portfolioLoading}
            isOnline={isOnline}
            janitorRun={janitorRun}
            janitorLoading={janitorLoading}
            janitorError={janitorError}
            onAddTask={() => router.push("/maintenance")}
            onInbox={() => router.push("/inbox")}
            onJanitor={() => router.push("/janitor")}
          />

          <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} spacing="md">
            <KpiCard
              title="Open Tasks"
              value={loading ? "..." : pendingTaskCount === null ? "—" : String(pendingTaskCount)}
              subtitle={
                tasksError
                  ? "Unavailable"
                  : `${tasks?.filter((t: any) => t.priority === "high")?.length || 0} high priority`
              }
              icon={IconChecklist}
              color="primary"
              loading={loading}
              onClick={() => router.push("/maintenance")}
            />
            <KpiCard
              title="Upcoming Bills"
              value={
                loading
                  ? "..."
                  : upcomingBillsTotal === null
                    ? "—"
                    : `$${upcomingBillsTotal.toLocaleString()}`
              }
              subtitle={billsError ? "Unavailable" : `${bills?.length || 0} bills due`}
              icon={IconWallet}
              color="warning"
              loading={loading}
              onClick={() => router.push("/finance")}
            />
            <KpiCard
              title="Unread Messages"
              value={loading ? "..." : unreadMessageCount === null ? "—" : String(unreadMessageCount)}
              subtitle={
                unreadError
                  ? "Unavailable"
                  : `${unreadCount?.gmail || 0} Gmail, ${unreadCount?.whatsapp || 0} WhatsApp`
              }
              icon={IconInbox}
              color="info"
              loading={loading}
              onClick={() => router.push("/inbox")}
            />
            <KpiCard
              title="System Health"
              value={loading ? "..." : statusError ? "—" : `${onlineAgents}/${agentList.length}`}
              subtitle={
                statusError
                  ? "Offline"
                  : onlineAgents === agentList.length
                    ? "All agents ready"
                    : "Some agents idle"
              }
              icon={IconShieldLock}
              color="success"
              loading={loading}
              onClick={() => router.push("/system")}
            />
          </SimpleGrid>

          <SimpleGrid cols={{ base: 1, lg: 2 }} spacing="lg">
            <Card radius="md" withBorder padding="md">
              <Group justify="space-between" mb="md">
                <Group gap="xs">
                  <ThemeIcon variant="light" color="primary" size="sm" radius="md">
                    <IconRobot size={14} />
                  </ThemeIcon>
                  <Text fw={600} size="sm">
                    AI Agents
                  </Text>
                </Group>
                <Group gap="xs">
                  <Badge
                    variant="light"
                    color={onlineAgents === agentList.length ? "success" : "warning"}
                  >
                    {onlineAgents}/{agentList.length} active
                  </Badge>
                  <Button
                    variant="subtle"
                    size="xs"
                    leftSection={<IconSettings size={14} />}
                    onClick={() => router.push("/settings")}
                  >
                    Manage
                  </Button>
                </Group>
              </Group>

              {loading ? (
                <Stack gap="sm">
                  {[1, 2, 3, 4].map((i) => (
                    <Skeleton key={i} height={64} radius="md" />
                  ))}
                </Stack>
              ) : agentList.length === 0 ? (
                <Box py="xl" style={{ textAlign: "center" }}>
                  <IconRobot size={40} stroke={1.5} style={{ color: "var(--mantine-color-dimmed)" }} />
                  <Text c="dimmed" mt="sm" size="sm">
                    No agents configured
                  </Text>
                </Box>
              ) : (
                <Stack gap="sm">
                  {agentList.map((agent) => (
                    <AgentCard key={agent.id} agent={agent} onClick={() => router.push("/settings")} />
                  ))}
                </Stack>
              )}
            </Card>

            <SystemHealthCard
              status={systemStatus.data}
              loading={systemStatus.loading}
              error={systemStatus.error}
            />
          </SimpleGrid>

          <ActivityFeed activities={activities} loading={loading} onRefresh={refetch} />
        </Stack>
      </Page>
    </Shell>
  );
}

function formatTimeAgo(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;

  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;

  const diffDays = Math.floor(diffHours / 24);
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays} days ago`;

  return date.toLocaleDateString();
}

function formatAction(action: string): string {
  return action.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
}

function getAgentName(id: string): string {
  const names: Record<string, string> = {
    manager: "Galidima",
    finance: "Mamadou",
    maintenance: "Ousmane",
    contractors: "Malik",
    projects: "Zainab",
    security: "Aicha",
    "security-manager": "Aicha",
    janitor: "Sule",
    mail: "Amina",
    "mail-skill": "Amina",
    backup: "Backup",
    "backup-recovery": "Backup",
  };
  return names[id] || id.charAt(0).toUpperCase() + id.slice(1).replace(/-/g, " ");
}

function getAgentDescription(id: string): string {
  const descriptions: Record<string, string> = {
    manager: "Coordinates all agents and decisions",
    finance: "Budgeting, bills, and portfolio oversight",
    maintenance: "Maintenance tasks and repair planning",
    contractors: "Contractor sourcing and job tracking",
    projects: "Project planning and milestones",
    security: "Safety, incidents, and alerts",
    "security-manager": "Safety, incidents, and alerts",
    janitor: "System hygiene and audits",
    mail: "Inbox triage and summaries",
    "mail-skill": "Inbox triage and summaries",
    backup: "Data backup and recovery",
    "backup-recovery": "Data backup and recovery",
  };
  return descriptions[id] || "Agent services";
}

function formatPercent(value?: number | null): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "—";
  return `${Math.round(value)}%`;
}

function formatUptime(value?: number | null): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "—";
  const hours = Math.floor(value / 3600);
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(hours / 24);
  return `${days}d`;
}
