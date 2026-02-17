"use client";
import React, { useState, useEffect, useCallback, useMemo } from "react";
import GridLayout from "react-grid-layout";
import {
  Card,
  Text,
  Group,
  Badge,
  ActionIcon,
  Menu,
  ThemeIcon,
  Stack,
  Button,
  Modal,
  SimpleGrid,
  Switch,
  Paper,
  Loader,
  ScrollArea,
  Box,
} from "@mantine/core";
import {
  IconGripVertical,
  IconX,
  IconPlus,
  IconSettings,
  IconActivity,
  IconCpu,
  IconTool,
  IconAlertTriangle,
  IconChartLine,
  IconClock,
  IconBolt,
  IconTrash,
  IconReceipt2,
  IconMessageCircle,
} from "@tabler/icons-react";
import "react-grid-layout/css/styles.css";
import { sendAgentChat, getApiBaseUrl } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";

const API_URL = getApiBaseUrl();

// Widget definitions
const WIDGET_TYPES = {
  "system-status": { name: "System Status", icon: IconActivity, color: "blue", w: 2, h: 2, minW: 1, minH: 1 },
  "agent-grid": { name: "Agent Grid", icon: IconCpu, color: "violet", w: 4, h: 3, minW: 2, minH: 2 },
  "tasks": { name: "Tasks", icon: IconTool, color: "orange", w: 2, h: 2, minW: 1, minH: 1 },
  "alerts": { name: "Alerts", icon: IconAlertTriangle, color: "red", w: 2, h: 2, minW: 1, minH: 1 },
  "activity": { name: "Activity", icon: IconClock, color: "cyan", w: 2, h: 2, minW: 1, minH: 1 },
  "quick-actions": { name: "Quick Actions", icon: IconBolt, color: "yellow", w: 2, h: 1, minW: 1, minH: 1 },
  "janitor": { name: "Janitor", icon: IconTrash, color: "gray", w: 2, h: 2, minW: 1, minH: 1 },
  "chat": { name: "Chat", icon: IconMessageCircle, color: "indigo", w: 3, h: 3, minW: 2, minH: 2 },
  "portfolio-summary": { name: "Portfolio Summary", icon: IconChartLine, color: "green", w: 2, h: 2, minW: 1, minH: 1 },
};

const WIDGET_ID_MAP: Record<string, string> = {
  "agent-count": "agent-grid",
  "pending-tasks": "tasks",
  "recent-activity": "activity",
  "janitor-status": "janitor",
  "chat-preview": "chat",
  "portfolio-summary": "portfolio-summary",
  "portfolio-chart": "portfolio-summary",
};

interface LayoutItem {
  i: string;
  x: number;
  y: number;
  w: number;
  h: number;
  minW?: number;
  minH?: number;
}

interface DashboardConfig {
  layout: LayoutItem[];
  widgets: string[];
}

const STORAGE_KEY = "mycasa_dashboard_config";

const DEFAULT_CONFIG: DashboardConfig = {
  layout: [
    { i: "system-status", x: 0, y: 0, w: 2, h: 2 },
    { i: "agent-grid", x: 2, y: 0, w: 4, h: 3 },
    { i: "tasks", x: 6, y: 0, w: 2, h: 2 },
    { i: "alerts", x: 6, y: 2, w: 2, h: 2 },
  ],
  widgets: ["system-status", "agent-grid", "tasks", "alerts"],
};

// Widget content components
function SystemStatusWidget({ data }: { data: any }) {
  return (
    <Stack gap="xs">
      <Group justify="space-between">
        <Text size="sm" c="dimmed">Backend</Text>
        <Badge color={data?.running ? "green" : "red"} size="sm" variant="light">
          {data?.running ? "Online" : "Offline"}
        </Badge>
      </Group>
      <Group justify="space-between">
        <Text size="sm" c="dimmed">Agents</Text>
        <Text size="sm" fw={600}>{data?.resources?.agents_active || 0} / {data?.resources?.agents_total || 0}</Text>
      </Group>
      <Group justify="space-between">
        <Text size="sm" c="dimmed">Database</Text>
        <Text size="sm" fw={500}>{data?.database?.size_formatted || "N/A"}</Text>
      </Group>
      <Group justify="space-between">
        <Text size="sm" c="dimmed">Last activity</Text>
        <Text size="xs" c="dimmed">
          {data?.last_activity ? new Date(data.last_activity).toLocaleTimeString() : "—"}
        </Text>
      </Group>
    </Stack>
  );
}

function AgentGridWidget({ data }: { data: any }) {
  const agents = data?.processes || [];

  const toggleAgent = async (agentId: string, enable: boolean) => {
    try {
      // enable/disable via settings
      await fetch(`${API_URL}/api/settings/agents/enabled`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ [agentId]: enable })
      });
      // trigger system startup to apply
      await fetch(`${API_URL}/api/system/startup`, { method: "POST" });
      window.dispatchEvent(new CustomEvent("mycasa-system-sync"));
    } catch (e) {
      // ignore
    }
  };

  return (
    <SimpleGrid cols={2} spacing="xs">
      {agents.slice(0, 8).map((agent: any) => (
        <Paper key={agent.id} p="xs" withBorder radius="sm" bg="rgba(255,255,255,0.02)">
          <Group gap="xs" justify="space-between">
            <Group gap="xs">
              <Badge 
                size="xs" 
                variant="light"
                color={agent.state === "running" ? "green" : agent.state === "idle" ? "blue" : "gray"}
              >
                {agent.state}
              </Badge>
              <Text size="xs" truncate>{agent.name?.replace(" Agent", "")}</Text>
            </Group>
            <Button size="xs" variant="light" onClick={() => toggleAgent(agent.id, agent.state !== "running")}
              style={{ paddingLeft: 6, paddingRight: 6 }}>
              {agent.state === "running" ? "Stop" : "Start"}
            </Button>
          </Group>
        </Paper>
      ))}
    </SimpleGrid>
  );
}

function TasksWidget({ data }: { data: any }) {
  const tasks = data?.tasks || [];
  return (
    <Stack gap="xs">
      <Text size="sm" fw={500}>{tasks.length} pending</Text>
      {tasks.slice(0, 3).map((t: any, i: number) => (
        <Text key={i} size="xs" truncate c="dimmed">{t.title || t.name}</Text>
      ))}
    </Stack>
  );
}

function AlertsWidget({ data }: { data: any }) {
  const alerts = data?.alerts || [];
  return alerts.length > 0 ? (
    <Stack gap="xs">
      {alerts.slice(0, 3).map((a: any, i: number) => (
        <Badge key={i} color="red" variant="light" size="sm">{a.message || a}</Badge>
      ))}
    </Stack>
  ) : (
    <Text size="sm" c="dimmed">No alerts</Text>
  );
}

function JanitorWidget({ data }: { data: any }) {
  const status = data?.status;
  const health = status?.health || "unknown";
  const metrics = status?.metrics || {};
  const [running, setRunning] = useState(false);
  const [lastAudit, setLastAudit] = useState<string | null>(null);

  const runAudit = async () => {
    setRunning(true);
    try {
      const res = await fetch(`${API_URL}/api/janitor/run-audit`, { method: "POST" });
      if (res.ok) {
        const out = await res.json();
        setLastAudit(out?.timestamp || new Date().toISOString());
      }
    } catch (e) {
      // ignore
    } finally {
      setRunning(false);
    }
  };

  return (
    <Stack gap="xs">
      <Group justify="space-between">
        <Text size="sm" c="dimmed">Health</Text>
        <Badge size="sm" color={health === "healthy" ? "green" : health === "degraded" ? "orange" : "red"}>
          {health}
        </Badge>
      </Group>
      <Group justify="space-between">
        <Text size="sm" c="dimmed">Open incidents</Text>
        <Text size="sm" fw={500}>{metrics.open_incidents || 0}</Text>
      </Group>
      <Group justify="space-between">
        <Text size="sm" c="dimmed">Month cost</Text>
        <Text size="sm" fw={500}>${metrics.month_cost || 0}</Text>
      </Group>
      <Group justify="space-between">
        <Text size="sm" c="dimmed">Audit</Text>
        <Button size="xs" variant="light" onClick={runAudit} disabled={running}>
          {running ? <Loader size="xs" /> : "Run"}
        </Button>
      </Group>
      {(lastAudit || data?.status?.metrics?.last_audit) && (
        <Text size="xs" c="dimmed">
          Last audit: {new Date(lastAudit || data?.status?.metrics?.last_audit).toLocaleString()}
        </Text>
      )}
    </Stack>
  );
}

function PortfolioSummaryWidget({ data }: { data: any }) {
  const total = data?.total_value || 0;
  const cash = data?.cash || 0;
  const holdings = data?.holdings || [];
  return (
    <Stack gap="xs">
      <Group justify="space-between">
        <Text size="sm" c="dimmed">Total</Text>
        <Text size="sm" fw={600}>${total.toLocaleString()}</Text>
      </Group>
      <Group justify="space-between">
        <Text size="sm" c="dimmed">Cash</Text>
        <Text size="sm" fw={500}>${cash.toLocaleString()}</Text>
      </Group>
      <Group justify="space-between">
        <Text size="sm" c="dimmed">Holdings</Text>
        <Text size="sm" fw={500}>{holdings.length}</Text>
      </Group>
    </Stack>
  );
}

function ChatWidget() {
  const { user } = useAuth();
  const [agentId, setAgentId] = useState<string>("finance");
  const [input, setInput] = useState<string>("");
  const [messages, setMessages] = useState<Array<{role: string; content: string}>>([]);

  const send = async () => {
    if (!input.trim()) return;
    const userMsg = { role: "user", content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    try {
      const key = `mycasa_dashboard_conversation_${agentId}:${user?.id ?? "anon"}`;
      const storedConversation = typeof window !== "undefined" ? localStorage.getItem(key) || undefined : undefined;
      const data = await sendAgentChat(agentId, userMsg.content, storedConversation);
      if (data?.conversation_id && typeof window !== "undefined") {
        localStorage.setItem(key, data.conversation_id);
      }
      setMessages(prev => [...prev, { role: "agent", content: data.response || "" }]);
    } catch (e) {
      // ignore
    }
  };

  return (
    <Stack gap="xs">
      <Group gap="xs">
        <Badge variant="light">agent</Badge>
        <Text size="xs" c="dimmed">{agentId}</Text>
      </Group>
      <ScrollArea h={120} offsetScrollbars>
        <Stack gap={6}>
          {messages.length === 0 && (
            <Text size="xs" c="dimmed">Ask an agent…</Text>
          )}
          {messages.map((m, i) => (
            <Box key={i} p={6} style={{ background: m.role === "user" ? "rgba(255,255,255,0.04)" : "rgba(99,102,241,0.08)", borderRadius: 8 }}>
              <Text size="xs" c={m.role === "user" ? "dimmed" : "white"}>{m.content}</Text>
            </Box>
          ))}
        </Stack>
      </ScrollArea>
      <Group gap="xs">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Message…"
          style={{ flex: 1, background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)", color: "white", padding: "6px 8px", borderRadius: 6 }}
        />
        <Button size="xs" variant="light" onClick={send}>Send</Button>
      </Group>
    </Stack>
  );
}

function GenericWidget({ type }: { type: string }) {
  const config = WIDGET_TYPES[type as keyof typeof WIDGET_TYPES];
  return (
    <Text size="sm" c="dimmed">{config?.name || type}</Text>
  );
}

interface DraggableDashboardProps {
  systemData?: any;
  tasksData?: any;
  alertsData?: any;
  janitorData?: any;
  portfolioData?: any;
}

export function DraggableDashboard({ systemData, tasksData, alertsData, janitorData, portfolioData }: DraggableDashboardProps) {
  const [config, setConfig] = useState<DashboardConfig>(DEFAULT_CONFIG);
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [mounted, setMounted] = useState(false);

  // Load from localStorage on mount
  useEffect(() => {
    setMounted(true);
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        const enabledWidgets: string[] = parsed.enabledWidgets || parsed.widgets || DEFAULT_CONFIG.widgets;
        const mappedWidgets = enabledWidgets.map((w: string) => WIDGET_ID_MAP[w] || w);
        const layout = parsed.layout || DEFAULT_CONFIG.layout;
        setConfig({
          layout,
          widgets: mappedWidgets,
        });
      }
    } catch (e) {
      console.error("Failed to load dashboard config:", e);
    }
  }, []);

  // Save to localStorage
  const saveConfig = useCallback((newConfig: DashboardConfig) => {
    setConfig(newConfig);
    try {
      // Keep compatible shape with WidgetManager config
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          enabledWidgets: newConfig.widgets,
          widgetOrder: newConfig.widgets,
          layout: newConfig.layout,
          layoutStyle: "default",
        })
      );
    } catch (e) {
      console.error("Failed to save dashboard config:", e);
    }
  }, []);

  const handleLayoutChange = useCallback((newLayout: readonly LayoutItem[]) => {
    saveConfig({ ...config, layout: [...newLayout] });
  }, [config, saveConfig]);

  const removeWidget = useCallback((widgetId: string) => {
    const newWidgets = config.widgets.filter(w => w !== widgetId);
    const newLayout = config.layout.filter(l => l.i !== widgetId);
    saveConfig({ layout: newLayout, widgets: newWidgets });
  }, [config, saveConfig]);

  const addWidget = useCallback((widgetType: string) => {
    if (config.widgets.includes(widgetType)) return;
    
    const widgetConfig = WIDGET_TYPES[widgetType as keyof typeof WIDGET_TYPES];
    const newLayout: LayoutItem = {
      i: widgetType,
      x: 0,
      y: Infinity, // Put at bottom
      w: widgetConfig?.w || 2,
      h: widgetConfig?.h || 2,
      minW: widgetConfig?.minW,
      minH: widgetConfig?.minH,
    };
    
    saveConfig({
      layout: [...config.layout, newLayout],
      widgets: [...config.widgets, widgetType],
    });
    setAddModalOpen(false);
  }, [config, saveConfig]);

  const renderWidgetContent = useCallback((widgetId: string) => {
    switch (widgetId) {
      case "system-status":
        return <SystemStatusWidget data={systemData} />;
      case "agent-grid":
        return <AgentGridWidget data={systemData} />;
      case "tasks":
        return <TasksWidget data={tasksData} />;
      case "alerts":
        return <AlertsWidget data={alertsData} />;
      case "janitor":
        return <JanitorWidget data={janitorData} />;
      case "portfolio-summary":
        return <PortfolioSummaryWidget data={portfolioData} />;
      case "chat":
        return <ChatWidget />;
      default:
        return <GenericWidget type={widgetId} />;
    }
  }, [systemData, tasksData, alertsData, janitorData, portfolioData]);

  const availableWidgets = useMemo(() =>
    Object.keys(WIDGET_TYPES).filter(w => !config.widgets.includes(w)),
    [config.widgets]
  );

  const gridChildren = useMemo(() =>
    config.widgets.map((widgetId) => {
      const widgetConfig = WIDGET_TYPES[widgetId as keyof typeof WIDGET_TYPES];
      const Icon = widgetConfig?.icon || IconActivity;

      return (
        <div key={widgetId}>
          <Card
            withBorder
            h="100%"
            style={{
              overflow: "hidden",
              background: "rgba(18,22,28,0.75)",
              borderColor: "rgba(255,255,255,0.08)",
              borderRadius: 16,
              boxShadow: "0 8px 30px rgba(0,0,0,0.25)",
            }}
          >
            <Card.Section
              withBorder
              inheritPadding
              py="xs"
              style={{
                background: "linear-gradient(90deg, rgba(255,214,153,0.08), rgba(143,188,255,0.06))",
                borderColor: "rgba(255,255,255,0.06)",
              }}
            >
              <Group justify="space-between">
                <Group gap="xs">
                  <ActionIcon
                    className="drag-handle"
                    variant="subtle"
                    size="sm"
                    style={{ cursor: "grab" }}
                  >
                    <IconGripVertical size={14} />
                  </ActionIcon>
                  <ThemeIcon size="sm" variant="light" color={widgetConfig?.color}>
                    <Icon size={12} />
                  </ThemeIcon>
                  <Text size="xs" fw={600}>{widgetConfig?.name}</Text>
                </Group>
                <ActionIcon
                  variant="subtle"
                  size="sm"
                  onClick={() => removeWidget(widgetId)}
                >
                  <IconX size={12} />
                </ActionIcon>
              </Group>
            </Card.Section>
            <Card.Section p="sm" style={{ flex: 1, overflow: "auto" }}>
              {renderWidgetContent(widgetId)}
            </Card.Section>
          </Card>
        </div>
      );
    }),
    [config.widgets, removeWidget, renderWidgetContent]
  );

  const modalWidgetList = useMemo(() =>
    availableWidgets.map((widgetType) => {
      const widgetConfig = WIDGET_TYPES[widgetType as keyof typeof WIDGET_TYPES];
      const Icon = widgetConfig?.icon || IconActivity;
      return (
        <Paper
          key={widgetType}
          p="md"
          withBorder
          style={{ cursor: "pointer" }}
          onClick={() => addWidget(widgetType)}
        >
          <Group>
            <ThemeIcon color={widgetConfig?.color} variant="light">
              <Icon size={16} />
            </ThemeIcon>
            <Text size="sm">{widgetConfig?.name}</Text>
          </Group>
        </Paper>
      );
    }),
    [availableWidgets, addWidget]
  );

  if (!mounted) return null;

  return (
    <>
      <Group justify="space-between" mb="md">
        <Text size="lg" fw={700} c="white">Dashboard</Text>
        <Button
          leftSection={<IconPlus size={16} />}
          variant="light"
          size="xs"
          onClick={() => setAddModalOpen(true)}
          style={{ background: "rgba(255,255,255,0.06)" }}
        >
          Add Widget
        </Button>
      </Group>

      {React.createElement(GridLayout as any, {
        className: "layout",
        layout: config.layout,
        rowHeight: 80,
        width: 1200,
        onLayoutChange: handleLayoutChange,
        draggableHandle: ".drag-handle",
        isResizable: true,
        isDraggable: true,
        compactType: "vertical"
      }, gridChildren)}

      <Modal opened={addModalOpen} onClose={() => setAddModalOpen(false)} title="Add Widget">
        <SimpleGrid cols={2}>
          {modalWidgetList}
        </SimpleGrid>
        {availableWidgets.length === 0 && (
          <Text c="dimmed" ta="center">All widgets added</Text>
        )}
      </Modal>
    </>
  );
}
