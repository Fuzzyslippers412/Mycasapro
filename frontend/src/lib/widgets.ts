/**
 * Dashboard Widget Configuration System
 * Stores widget preferences in localStorage and backend
 */

export interface Widget {
  id: string;
  name: string;
  description: string;
  icon: string;
  defaultEnabled: boolean;
  size: "small" | "medium" | "large";
  category: "status" | "finance" | "tasks" | "agents" | "tools";
}

// Available widgets
export const AVAILABLE_WIDGETS: Widget[] = [
  {
    id: "system-status",
    name: "System Status",
    description: "Overall system health and connection status",
    icon: "IconActivity",
    defaultEnabled: true,
    size: "small",
    category: "status",
  },
  {
    id: "agent-count",
    name: "Active Agents",
    description: "Number of running agents",
    icon: "IconCpu",
    defaultEnabled: true,
    size: "small",
    category: "agents",
  },
  {
    id: "pending-tasks",
    name: "Pending Tasks",
    description: "Tasks awaiting action",
    icon: "IconTool",
    defaultEnabled: true,
    size: "small",
    category: "tasks",
  },
  {
    id: "alerts",
    name: "Alerts",
    description: "System alerts and warnings",
    icon: "IconAlertTriangle",
    defaultEnabled: true,
    size: "small",
    category: "status",
  },
  {
    id: "agent-grid",
    name: "Agent Grid",
    description: "Status of all agents",
    icon: "IconCpu",
    defaultEnabled: true,
    size: "large",
    category: "agents",
  },
  {
    id: "portfolio-chart",
    name: "Portfolio Chart",
    description: "Portfolio performance over time",
    icon: "IconChartLine",
    defaultEnabled: true,
    size: "large",
    category: "finance",
  },
  {
    id: "portfolio-summary",
    name: "Portfolio Summary",
    description: "Quick portfolio value and change",
    icon: "IconWallet",
    defaultEnabled: true,
    size: "medium",
    category: "finance",
  },
  {
    id: "recent-activity",
    name: "Recent Activity",
    description: "Timeline of recent events",
    icon: "IconClock",
    defaultEnabled: true,
    size: "medium",
    category: "status",
  },
  {
    id: "quick-actions",
    name: "Quick Actions",
    description: "Common actions and shortcuts",
    icon: "IconBolt",
    defaultEnabled: true,
    size: "medium",
    category: "tools",
  },
  {
    id: "janitor-status",
    name: "Janitor Status",
    description: "Last audit results and cleanup stats",
    icon: "IconTrash",
    defaultEnabled: false,
    size: "medium",
    category: "tools",
  },
  {
    id: "upcoming-bills",
    name: "Upcoming Bills",
    description: "Bills due in the next 30 days",
    icon: "IconReceipt",
    defaultEnabled: false,
    size: "medium",
    category: "finance",
  },
  {
    id: "chat-preview",
    name: "Chat Preview",
    description: "Recent chat messages",
    icon: "IconMessage",
    defaultEnabled: false,
    size: "medium",
    category: "tools",
  },
];

export interface DashboardConfig {
  enabledWidgets: string[];
  widgetOrder: string[];
  layout: "default" | "compact" | "expanded";
}

const STORAGE_KEY = "mycasa_dashboard_config";
const DEFAULT_CONFIG: DashboardConfig = {
  enabledWidgets: AVAILABLE_WIDGETS.filter(w => w.defaultEnabled).map(w => w.id),
  widgetOrder: AVAILABLE_WIDGETS.filter(w => w.defaultEnabled).map(w => w.id),
  layout: "default",
};

export function getDashboardConfig(): DashboardConfig {
  if (typeof window === "undefined") return DEFAULT_CONFIG;
  
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      return { ...DEFAULT_CONFIG, ...JSON.parse(stored) };
    }
  } catch (e) {
    console.error("Failed to load dashboard config:", e);
  }
  return DEFAULT_CONFIG;
}

export function saveDashboardConfig(config: Partial<DashboardConfig>): void {
  if (typeof window === "undefined") return;
  
  try {
    const current = getDashboardConfig();
    const updated = { ...current, ...config };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  } catch (e) {
    console.error("Failed to save dashboard config:", e);
  }
}

export function toggleWidget(widgetId: string): DashboardConfig {
  const config = getDashboardConfig();
  const enabled = config.enabledWidgets.includes(widgetId);
  
  if (enabled) {
    config.enabledWidgets = config.enabledWidgets.filter(id => id !== widgetId);
    config.widgetOrder = config.widgetOrder.filter(id => id !== widgetId);
  } else {
    config.enabledWidgets.push(widgetId);
    config.widgetOrder.push(widgetId);
  }
  
  saveDashboardConfig(config);
  return config;
}

export function resetDashboardConfig(): DashboardConfig {
  saveDashboardConfig(DEFAULT_CONFIG);
  return DEFAULT_CONFIG;
}
