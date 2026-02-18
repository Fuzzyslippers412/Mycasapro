"use client";

import { useEffect, useMemo, useState } from "react";
import type { ElementType } from "react";
import { useRouter } from "next/navigation";
import { Shell } from "@/components/layout/Shell";
import { Page } from "@/components/layout/Page";
import { GlobalChat } from "@/components/GlobalChat";
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
  Tooltip,
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
import { apiFetch, getApiBaseUrl, isNetworkError, IndicatorDiagnostic } from "@/lib/api";
import { useDashboardData, useIndicatorDiagnostics, useJanitorWizardHistory, useSystemStatus } from "@/lib/hooks";
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
  heartbeat,
  identity,
  loading,
  isOnline,
  janitorRun,
  janitorLoading,
  janitorError,
  indicatorLookup,
  onAddTask,
  onInbox,
  onJanitor,
}: {
  userName?: string;
  pendingTasks: number | null;
  unreadMessages: number | null;
  portfolioChange: number | null;
  heartbeat: { open_findings?: number; last_run?: string | null; error?: string } | null;
  identity: { ready?: boolean; missing_required?: string[]; error?: string } | null;
  loading: boolean;
  isOnline: boolean;
  janitorRun: { health_score: number; findings_count: number; status: string; timestamp: string } | null;
  janitorLoading: boolean;
  janitorError: boolean;
  indicatorLookup?: (id: string) => IndicatorDiagnostic | undefined;
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
        ? `Janitor ${janitorRun.health_score}% / ${janitorRun.findings_count} findings`
        : "Janitor not run";

  const portfolioLabel =
    portfolioChange === null
      ? "Portfolio change unavailable"
      : `Portfolio ${portfolioChange >= 0 ? "+" : ""}${portfolioChange.toFixed(1)}%`;
  const heartbeatLabel = heartbeat?.error
    ? "Heartbeat unavailable"
    : typeof heartbeat?.open_findings === "number"
      ? `${heartbeat.open_findings} heartbeat findings`
      : "Heartbeat not run";
  const identityLabel = identity?.error
    ? "Identity unavailable"
    : identity?.ready
      ? "Identity ready"
      : "Identity incomplete";

  const MetricItem = ({
    icon: Icon,
    text,
    indicatorId,
  }: {
    icon: ElementType;
    text: string;
    indicatorId?: string;
  }) => {
    const meta = indicatorId && indicatorLookup ? indicatorLookup(indicatorId) : undefined;
    const tooltip = meta
      ? `${meta.label} • ${meta.status.toUpperCase()}${meta.last_updated ? ` • Updated ${new Date(meta.last_updated).toLocaleString()}` : ""}${meta.source ? ` • Source: ${meta.source}` : ""}`
      : "";
    const content = (
      <Group gap={6} wrap="nowrap">
        <ThemeIcon variant="light" size="sm" radius="md" color="primary">
          <Icon size={14} />
        </ThemeIcon>
        <Text size="sm">{text}</Text>
      </Group>
    );
    return meta ? (
      <Tooltip label={tooltip} withArrow>
        <Box>{content}</Box>
      </Tooltip>
    ) : (
      content
    );
  };

  return (
    <Card
      radius="lg"
      withBorder
      padding="md"
      className="status-hero"
      style={{ minHeight: 160 }}
    >
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
                  indicatorId="dashboard.tasks.pending_count"
                />
                <MetricItem
                  icon={IconInbox}
                  text={
                    typeof unreadMessages === "number"
                      ? `${unreadMessages} messages unread`
                      : "Messages unavailable"
                  }
                  indicatorId="dashboard.messages.unread_total"
                />
                <MetricItem icon={IconActivity} text={portfolioLabel} indicatorId="dashboard.portfolio.change_pct" />
                <MetricItem icon={IconSparkles} text={janitorLabel} indicatorId="dashboard.janitor.last_run" />
                <MetricItem icon={IconClock} text={heartbeatLabel} indicatorId="dashboard.heartbeat.open_findings" />
                <MetricItem icon={IconShieldLock} text={identityLabel} indicatorId="dashboard.identity.ready" />
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
  indicatorMeta,
  onClick,
}: {
  title: string;
  value: string;
  subtitle: string;
  icon: ElementType;
  loading: boolean;
  color?: string;
  indicatorMeta?: IndicatorDiagnostic;
  onClick?: () => void;
}) {
  const tooltip = indicatorMeta
    ? `${indicatorMeta.label} • ${indicatorMeta.status.toUpperCase()}${indicatorMeta.last_updated ? ` • Updated ${new Date(indicatorMeta.last_updated).toLocaleString()}` : ""}${indicatorMeta.source ? ` • Source: ${indicatorMeta.source}` : ""}`
    : "";
  const card = (
    <Card
      radius="lg"
      withBorder
      onClick={onClick}
      className="kpi-card"
      style={{ cursor: onClick ? "pointer" : "default", minHeight: 110 }}
    >
      <Group justify="space-between" align="flex-start">
        <Stack gap={6}>
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
          <Text size="xs" c="dimmed" className="kpi-subtitle">
            {subtitle}
          </Text>
        </Stack>
        <ThemeIcon variant="light" color={color} radius="md">
          <Icon size={18} />
        </ThemeIcon>
      </Group>
    </Card>
  );
  return indicatorMeta ? (
    <Tooltip label={tooltip} withArrow>
      <Box>{card}</Box>
    </Tooltip>
  ) : (
    card
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
    <Card radius="lg" withBorder padding="md" className="activity-card dashboard-card" style={{ minHeight: 360 }}>
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
        <ScrollArea style={{ flex: 1, minHeight: 0 }} type="auto">
          <Stack gap={0}>
            {activities.map((activity, index) => (
              <Box
                key={activity.id}
                py="sm"
                className="activity-item"
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
                      <Text size="sm" fw={600} className="activity-item-title">
                        {activity.title}
                      </Text>
                      <Badge size="xs" variant="light">
                        {activity.type}
                      </Badge>
                    </Group>
                    {activity.description && (
                      <Text size="xs" c="dimmed" className="activity-item-desc">
                        {activity.description}
                      </Text>
                    )}
                    <Group gap="xs">
                      <IconClock size={12} style={{ opacity: 0.5 }} />
                      <Text size="xs" c="dimmed" className="activity-item-meta">
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
  agent: { id: string; name: string; status: string; description: string; skills?: string[] };
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
    <Card withBorder p="sm" radius="md" className="agent-card dashboard-card" style={{ cursor: "pointer" }} onClick={onClick}>
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
            <Text size="sm" fw={600} className="agent-card-title">
              {agent.name}
            </Text>
            <Text size="xs" c="dimmed" lineClamp={2} className="agent-card-desc">
              {agent.description}
            </Text>
            {agent.skills && agent.skills.length > 0 && (
              <Group gap={6} mt={4} wrap="wrap">
                {agent.skills.slice(0, 3).map((skill) => (
                  <Badge key={skill} size="xs" variant="light" color="gray">
                    {skill}
                  </Badge>
                ))}
              </Group>
            )}
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
  status: {
    cpu_usage?: number | null;
    memory_usage?: number | null;
    disk_usage?: number | null;
    uptime?: number | null;
  } | null;
  loading: boolean;
  error: Error | null;
}) {
  const metrics = [
    {
      label: "CPU usage",
      value: status?.cpu_usage,
      format: formatPercent,
    },
    {
      label: "Memory usage",
      value: status?.memory_usage,
      format: formatPercent,
    },
    {
      label: "Disk usage",
      value: status?.disk_usage,
      format: formatPercent,
    },
    {
      label: "Uptime",
      value: status?.uptime,
      format: formatUptime,
    },
  ];

  const availableMetrics = metrics.filter(
    (m) => typeof m.value === "number" && Number.isFinite(m.value)
  );
  const hasMetrics = availableMetrics.length > 0;

  return (
    <Card radius="lg" withBorder padding="md" className="system-health-card dashboard-card" style={{ minHeight: 360 }}>
      <Group justify="space-between" mb="md">
        <Group gap="xs">
          <ThemeIcon variant="light" color="primary" size="sm" radius="md">
            <IconShieldLock size={14} />
          </ThemeIcon>
          <Text fw={600} size="sm">
            System Health
          </Text>
        </Group>
        <Badge
          size="sm"
          variant="light"
          color={error ? "gray" : hasMetrics ? "success" : "yellow"}
        >
          {error ? "Offline" : hasMetrics ? "Live" : "Unavailable"}
        </Badge>
      </Group>

      {error ? (
        <Text size="sm" c="dimmed">
          System metrics unavailable right now.
        </Text>
      ) : !hasMetrics ? (
        <Text size="sm" c="dimmed">
          Live telemetry is not available on this host.
        </Text>
      ) : (
        <Stack gap="xs">
          {availableMetrics.map((row) => (
            <Group key={row.label} justify="space-between">
              <Text size="sm" c="dimmed">
                {row.label}
              </Text>
              {loading ? (
                <Skeleton height={12} width={60} />
              ) : (
                <Text size="sm" fw={600}>
                  {row.format(row.value as number)}
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
  const indicatorDiagnostics = useIndicatorDiagnostics(60000);
  const indicatorIndex = useMemo(() => {
    const map = new Map<string, IndicatorDiagnostic>();
    indicatorDiagnostics.data?.results?.forEach((item) => {
      map.set(item.id, item);
    });
    return map;
  }, [indicatorDiagnostics.data]);
  const indicatorLookup = (id: string) => indicatorIndex.get(id);
  const indicatorOk = (id: string) => {
    const meta = indicatorLookup(id);
    return meta ? meta.status === "ok" : true;
  };
  const [portfolioChange, setPortfolioChange] = useState<number | null>(null);
  const [portfolioLoading, setPortfolioLoading] = useState(true);
  const apiBase = getApiBaseUrl();
  const isOnline = !statusError;
  const statusErrorStatus = (statusError as any)?.status;
  const statusErrorDetail = (statusError as any)?.detail;
  const statusOffline = isNetworkError(statusError) || statusErrorStatus === 0;

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
        // Keep last known portfolio change to avoid flicker
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
        skills: Array.isArray((data as any).skills) ? (data as any).skills : [],
      }))
    : [];

  const pendingTaskCount = loading || tasksError || !indicatorOk("dashboard.tasks.pending_count")
    ? null
    : tasks?.length ?? null;
  const unreadMessageCount = loading || unreadError || !indicatorOk("dashboard.messages.unread_total")
    ? null
    : unreadCount?.total ?? null;
  const upcomingBillsTotal = loading || billsError || !indicatorOk("dashboard.bills.upcoming_total")
    ? null
    : bills?.reduce((sum: number, b: any) => sum + (b.amount || 0), 0) ?? null;

  const onlineAgents = agentList.filter(
    (a) => a.status === "online" || a.status === "running"
  ).length;

  return (
    <Shell>
      <Page title="Dashboard" subtitle="Home operations, organized" fullWidth>
        <Stack gap="lg" pb={100} className="dashboard-stack">
          {error && (
            <Alert icon={<IconAlertCircle size={16} />} title="Connection Error" color="red" radius="md">
              <Group justify="space-between" align="center" wrap="wrap">
                <Text size="sm">
                  {statusOffline
                    ? (statusError as any)?.message || `Unable to reach backend at ${apiBase}. Start the API and try again.`
                    : typeof statusErrorStatus === "number"
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
                <Button
                  size="xs"
                  variant="default"
                  onClick={() => {
                    try {
                      window.localStorage.removeItem("mycasa_api_base_override");
                      window.location.reload();
                    } catch {
                      // ignore
                    }
                  }}
                >
                  Reset API connection
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

          <SimpleGrid cols={{ base: 1, lg: 2 }} spacing="lg" className="dashboard-grid">
            <Stack gap="lg" className="dashboard-left" style={{ height: "100%" }}>
              <StatusHeader
                userName={user?.display_name || user?.username || "there"}
                pendingTasks={pendingTaskCount}
                unreadMessages={unreadMessageCount}
                portfolioChange={indicatorOk("dashboard.portfolio.change_pct") ? portfolioChange : null}
                heartbeat={statusData?.facts?.heartbeat || null}
                identity={statusData?.facts?.identity || null}
                loading={loading || portfolioLoading}
                isOnline={isOnline}
                janitorRun={janitorRun}
                janitorLoading={janitorLoading}
                janitorError={janitorError}
                indicatorLookup={indicatorLookup}
                onAddTask={() => router.push("/maintenance")}
                onInbox={() => router.push("/inbox")}
                onJanitor={() => router.push("/janitor")}
              />
              <Box className="dashboard-chat-slot">
                <GlobalChat mode="embedded" />
              </Box>
            </Stack>

            <Stack gap="lg" className="dashboard-right">
              <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
                <KpiCard
                  title="Open Tasks"
                  value={loading ? "..." : pendingTaskCount === null ? "N/A" : String(pendingTaskCount)}
                  subtitle={
                    tasksError
                      ? "Unavailable"
                      : `${tasks?.filter((t: any) => t.priority === "high")?.length || 0} high priority`
                  }
                  icon={IconChecklist}
                  color="primary"
                  loading={loading}
                  indicatorMeta={indicatorLookup("dashboard.tasks.pending_count")}
                  onClick={() => router.push("/maintenance")}
                />
                <KpiCard
                  title="Upcoming Bills"
                  value={
                    loading
                      ? "..."
                      : upcomingBillsTotal === null
                        ? "N/A"
                        : `$${upcomingBillsTotal.toLocaleString()}`
                  }
                  subtitle={billsError ? "Unavailable" : `${bills?.length || 0} bills due`}
                  icon={IconWallet}
                  color="warning"
                  loading={loading}
                  indicatorMeta={indicatorLookup("dashboard.bills.upcoming_total")}
                  onClick={() => router.push("/finance")}
                />
                <KpiCard
                  title="Unread Messages"
                  value={loading ? "..." : unreadMessageCount === null ? "N/A" : String(unreadMessageCount)}
                  subtitle={
                    unreadError
                      ? "Unavailable"
                      : `${unreadCount?.gmail || 0} Gmail, ${unreadCount?.whatsapp || 0} WhatsApp`
                  }
                  icon={IconInbox}
                  color="info"
                  loading={loading}
                  indicatorMeta={indicatorLookup("dashboard.messages.unread_total")}
                  onClick={() => router.push("/inbox")}
                />
                <KpiCard
                  title="System Health"
                  value={loading ? "..." : statusError ? "N/A" : `${onlineAgents}/${agentList.length}`}
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
                  indicatorMeta={indicatorLookup("dashboard.system.agents_online")}
                  onClick={() => router.push("/system")}
                />
              </SimpleGrid>

              <SimpleGrid cols={{ base: 1, lg: 2 }} spacing="lg" className="dashboard-right-grid">
                <Card radius="md" withBorder padding="md" style={{ minHeight: 360 }}>
                  <Group justify="space-between" mb="md">
                    <Group gap="xs">
                      <ThemeIcon variant="light" color="primary" size="sm" radius="md">
                        <IconRobot size={14} />
                      </ThemeIcon>
                      <Text fw={600} size="sm">
                        Agents
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
                    <ScrollArea style={{ flex: 1, minHeight: 0 }} type="auto">
                      <Stack gap="sm">
                        {agentList.map((agent) => (
                          <AgentCard key={agent.id} agent={agent} onClick={() => router.push("/settings")} />
                        ))}
                      </Stack>
                    </ScrollArea>
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

            {/* removed marketing sections per product UI */}
          </SimpleGrid>
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
  if (typeof value !== "number" || Number.isNaN(value)) return "N/A";
  return `${Math.round(value)}%`;
}

function formatUptime(value?: number | null): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "N/A";
  const hours = Math.floor(value / 3600);
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(hours / 24);
  return `${days}d`;
}
