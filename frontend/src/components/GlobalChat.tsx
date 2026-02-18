"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import {
  Paper,
  Group,
  Stack,
  Text,
  TextInput,
  Button,
  ActionIcon,
  Avatar,
  ScrollArea,
  Box,
  ThemeIcon,
  Tooltip,
  Badge,
  Collapse,
  Skeleton,
  Switch,
  Divider,
  Menu,
  Loader,
  Select,
  Alert,
  SimpleGrid,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import {
  IconSend,
  IconRobot,
  IconUser,
  IconMessage,
  IconChevronUp,
  IconChevronDown,
  IconX,
  IconSettings,
  IconPower,
  IconRefresh,
  IconRocket,
  IconTrash,
  IconArrowRight,
  IconHistory,
  IconPlus,
  IconArchive,
  IconEdit,
} from "@tabler/icons-react";
import { tokens } from "@/theme/tokens";
import { sendAgentChat, sendManagerChat, getAgentChatHistory, getAgentConversations, createAgentConversation, renameAgentConversation, archiveAgentConversation, restoreAgentConversation, getApiBaseUrl, isNetworkError, apiFetch } from "@/lib/api";

interface Message {
  id: number;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  agent?: string;
  routedTo?: string;
  delegationNote?: string;
  inputTokens?: number;
  outputTokens?: number;
  latencyMs?: number;
  taskCreated?: {
    task_id?: number | string;
    title?: string;
    due_date?: string | null;
    scheduled_date?: string | null;
    assigned_to?: string | null;
  };
  janitorReport?: {
    okCount: number;
    failCount: number;
    failures: Array<{ name: string; detail: string }>;
    options: {
      allowDestructive: boolean;
      useLive: boolean;
      includeOauth: boolean;
    };
  };
}

interface ConversationSummary {
  id: string;
  title?: string | null;
  updated_at?: string | null;
  created_at?: string | null;
  archived_at?: string | null;
  message_count?: number;
  last_message?: string | null;
}

interface AgentStatus {
  id: string;
  name: string;
  state: string;
  enabled: boolean;
  skills?: string[];
  currentRequests?: number;
  defaultModel?: string;
}

interface LlmStatus {
  loading: boolean;
  provider: string;
  authType: string;
  model: string;
  apiKeySet: boolean;
  oauthConnected: boolean;
  error: string | null;
}

const API_URL = getApiBaseUrl();
const CONVERSATION_KEY_PREFIX = "mycasa_conversation";
const CLEAR_KEY_PREFIX = "mycasa_chat_cleared_v1";

const AGENT_NAMES: Record<string, string> = {
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

const AGENT_ALIASES: Record<string, string[]> = {
  manager: ["manager", "galidima", "gm"],
  finance: ["finance", "mamadou"],
  maintenance: ["maintenance", "ousmane", "maint"],
  contractors: ["contractors", "malik", "contractor"],
  projects: ["projects", "zainab", "project"],
  security: ["security", "aicha"],
  "security-manager": ["security-manager"],
  janitor: ["janitor", "sule", "salimata"],
  "mail-skill": ["mail", "mail-skill", "amina", "inbox"],
  "backup-recovery": ["backup", "backup-recovery"],
};

const normalizeAgentToken = (value: string) =>
  value
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");

const isTaskIntent = (text: string) => {
  const msg = text.toLowerCase();
  const intentKeywords = [
    "remind",
    "reminder",
    "add a task",
    "add task",
    "schedule",
    "task",
    "need to",
    "have to",
    "clean",
    "fix",
    "repair",
    "replace",
    "inspect",
  ];
  const dateHints = [
    "today",
    "tomorrow",
    "this ",
    "next ",
    "by ",
    "on ",
    "friday",
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "saturday",
    "sunday",
  ];
  const hasIntent = intentKeywords.some((k) => msg.includes(k));
  const hasDate = dateHints.some((k) => msg.includes(k));
  return hasIntent && (msg.includes("task") || msg.includes("remind") || hasDate);
};

const routeHintForMessage = (message: string, agentId: string) => {
  if (agentId === "manager" && isTaskIntent(message)) return "maintenance";
  return null;
};

const handoffRouteFor = (agentId?: string | null) => {
  switch (agentId) {
    case "maintenance":
    case "maintenance_agent":
      return "/maintenance";
    case "finance":
    case "finance_agent":
      return "/finance";
    case "contractors":
    case "contractors_agent":
      return "/contractors";
    case "projects":
      return "/projects";
    case "mail":
    case "mail-skill":
      return "/inbox";
    case "backup":
    case "backup-recovery":
      return "/system";
    default:
      return null;
  }
};

function resolveAgentId(token: string): string | null {
  const normalized = normalizeAgentToken(token);
  for (const [id, aliases] of Object.entries(AGENT_ALIASES)) {
    if (aliases.some((alias) => normalizeAgentToken(alias) === normalized)) return id;
  }
  return null;
}

function conversationKey(agentId: string, userId?: number | null): string {
  const userScope = userId ? `user_${userId}` : "anon";
  return `${CONVERSATION_KEY_PREFIX}_${userScope}_${agentId}`;
}

function clearedKey(agentId: string, userId?: number | null): string {
  const userScope = userId ? `user_${userId}` : "anon";
  return `${CLEAR_KEY_PREFIX}_${userScope}_${agentId}`;
}

function isHistoryCleared(agentId: string, userId?: number | null): boolean {
  if (typeof window === "undefined") return false;
  return Boolean(window.localStorage.getItem(clearedKey(agentId, userId)));
}

function extractMentionedAgents(text: string): { agents: string[]; cleaned: string } {
  const agents = new Set<string>();
  const mentionRegex = /@([\p{L}\p{N}_-]+)/gu;
  let match: RegExpExecArray | null;

  while ((match = mentionRegex.exec(text)) !== null) {
    const id = resolveAgentId(match[1]);
    if (id) agents.add(id);
  }

  const cleaned = text
    .replace(mentionRegex, (full, token) => (resolveAgentId(token) ? "" : full))
    .replace(/\s{2,}/g, " ")
    .trim();

  return { agents: Array.from(agents), cleaned };
}

function toSettingsAgentId(agentId: string): string {
  if (agentId === "security-manager") return "security";
  if (agentId === "mail-skill") return "mail";
  if (agentId === "backup-recovery") return "backup";
  return agentId;
}

function toFleetAgentId(agentId: string): string {
  if (agentId === "security") return "security-manager";
  if (agentId === "mail") return "mail-skill";
  if (agentId === "backup") return "backup-recovery";
  return agentId;
}

function getStatusColor(state: string, enabled: boolean): string {
  if (!enabled) return tokens.colors.neutral[400];
  switch (state) {
    case "online":
    case "running":
    case "active":
      return tokens.colors.success[500];
    case "available":
      return tokens.colors.primary[400];
    case "busy":
      return tokens.colors.warn[500];
    case "error":
      return tokens.colors.error[500];
    default:
      return tokens.colors.primary[400];
  }
}

function getStatusLabel(state: string, enabled: boolean): string {
  if (!enabled) return "disabled";
  switch (state) {
    case "online":
    case "running":
    case "active":
      return "online";
    case "available":
      return "available";
    case "not_loaded":
    case "idle":
      return "idle";
    case "busy":
      return "busy";
    case "error":
      return "error";
    default:
      return state;
  }
}

export function GlobalChat({ mode = "floating" }: { mode?: "floating" | "embedded" }) {
  const { isAuthenticated, user } = useAuth();
  const router = useRouter();
  const isEmbedded = mode === "embedded";
  const [expanded, { toggle }] = useDisclosure(isEmbedded);
  const [showAgentSettings, setShowAgentSettings] = useState(false);
  const [agents, setAgents] = useState<AgentStatus[]>([]);
  const [loadingAgents, setLoadingAgents] = useState(true);
  const [togglingAgent, setTogglingAgent] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [llmStatus, setLlmStatus] = useState<LlmStatus>({
    loading: true,
    provider: "",
    authType: "",
    model: "",
    apiKeySet: false,
    oauthConnected: false,
    error: null,
  });
  const [selectedAgent, setSelectedAgent] = useState("manager");
  const [pendingRoute, setPendingRoute] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const [mounted, setMounted] = useState(false);
  const messageIdRef = useRef(1);
  const [historyStatus, setHistoryStatus] = useState<"idle" | "loading" | "error">("idle");
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [sessions, setSessions] = useState<ConversationSummary[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [sessionsError, setSessionsError] = useState<string | null>(null);
  const [showArchivedSessions, setShowArchivedSessions] = useState(false);
  const [showSessionsPanel, setShowSessionsPanel] = useState(true);
  const [launching, setLaunching] = useState(false);
  const [personalMode, setPersonalMode] = useState(false);
  const [personalModeChecked, setPersonalModeChecked] = useState(false);
  const [personalModeError, setPersonalModeError] = useState<string | null>(null);
  const [taskActionState, setTaskActionState] = useState<Record<string, string>>({});
  const agentTheme = (() => {
    const key = selectedAgent || "manager";
    switch (key) {
      case "finance":
        return { label: "Finance", accent: tokens.colors.success[500], color: "green" as const };
      case "maintenance":
        return { label: "Maintenance", accent: tokens.colors.warn[500], color: "yellow" as const };
      case "contractors":
        return { label: "Contractors", accent: tokens.colors.primary[500], color: "blue" as const };
      case "projects":
        return { label: "Projects", accent: tokens.colors.primary[600], color: "indigo" as const };
      case "security":
      case "security-manager":
        return { label: "Security", accent: tokens.colors.error[500], color: "red" as const };
      case "janitor":
        return { label: "Janitor", accent: tokens.colors.neutral[700], color: "dark" as const };
      case "mail":
      case "mail-skill":
        return { label: "Mail", accent: tokens.colors.primary[400], color: "blue" as const };
      case "backup":
      case "backup-recovery":
        return { label: "Backup", accent: tokens.colors.neutral[500], color: "gray" as const };
      default:
        return { label: "Command", accent: tokens.colors.primary[500], color: "blue" as const };
    }
  })();
  const selectedAgentMeta = agents.find((a) => a.id === selectedAgent);
  const selectedSkills = selectedAgentMeta?.skills || [];
  const activeAgents = agents
    .filter((agent) => (agent.currentRequests || 0) > 0)
    .map((agent) => ({
      id: agent.id,
      name: agent.name,
      count: agent.currentRequests || 0,
    }));
  const assignableAgents = agents.filter((agent) => agent.enabled && agent.id !== "manager");
  const chatAllowed = !personalModeError;
  const lipTitle = !chatAllowed
    ? personalModeError || "Backend unavailable"
    : expanded
      ? "Close chat"
      : `Ask ${agentTheme.label}`;
  const agentOptions = agents
    .filter((agent) => agent.enabled)
    .map((agent) => ({
      value: agent.id,
      label: agent.name,
    }));

  const nextMessageId = useCallback(() => {
    const id = messageIdRef.current;
    messageIdRef.current += 1;
    return id;
  }, []);

  const pushAssistantMessage = useCallback(
    (content: string, agentName = "System") => {
      const message: Message = {
        id: nextMessageId(),
        role: "assistant",
        content,
        timestamp: new Date().toISOString(),
        agent: agentName,
      };
      setMessages((prev) => [...prev, message]);
    },
    [nextMessageId]
  );

  const pushJanitorReport = useCallback(
    (report: Message["janitorReport"]) => {
      if (!report) return;
      const message: Message = {
        id: nextMessageId(),
        role: "assistant",
        content: "Janitor preflight report",
        timestamp: new Date().toISOString(),
        agent: "Janitor",
        janitorReport: report,
      };
      setMessages((prev) => [...prev, message]);
    },
    [nextMessageId]
  );

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    let active = true;
    const checkPersonalMode = async () => {
      try {
        const data = await apiFetch<any>("/api/system/status");
        if (active) {
          setPersonalMode(Boolean(data.personal_mode));
          setPersonalModeError(null);
        }
      } catch {
        if (active) {
          setPersonalMode(false);
          setPersonalModeError("Backend unavailable. Start the API to chat.");
        }
      } finally {
        if (active) setPersonalModeChecked(true);
      }
    };
    checkPersonalMode();
    return () => {
      active = false;
    };
  }, []);

  const refreshSessions = async (agentId: string) => {
    if (!chatAllowed) return;
    setSessionsLoading(true);
    setSessionsError(null);
    try {
      const data = await getAgentConversations(agentId, 12, showArchivedSessions);
      setSessions(data?.conversations || []);
    } catch (err: any) {
      if (isNetworkError(err)) {
        setSessionsError(`Unable to reach backend at ${API_URL}.`);
      } else {
        setSessionsError(err?.detail || "Unable to load sessions");
      }
    } finally {
      setSessionsLoading(false);
    }
  };

  const loadConversation = async (agentId: string, targetId?: string) => {
    if (!chatAllowed) return;
    setHistoryStatus("loading");
    setHistoryError(null);
    setMessages([]);
    messageIdRef.current = 1;
    try {
      let conversationId = targetId;
      if (!conversationId) {
        try {
          const latest = await getAgentConversations(agentId, 1, false);
          const recent = latest?.conversations?.[0]?.id;
          if (recent) {
            conversationId = recent;
          }
        } catch {
          // ignore and fall through
        }
      }
      if (!conversationId) {
        try {
          const created = await createAgentConversation(agentId);
          conversationId = created?.conversation_id;
        } catch {
          conversationId = undefined;
        }
      }
      const data = await getAgentChatHistory(agentId, conversationId, 50);
      if (data?.messages?.length) {
        const mapped: Message[] = data.messages.map((msg: any, idx: number) => ({
          id: idx + 1,
          role: msg.role === "assistant" ? "assistant" : "user",
          content: msg.content,
          timestamp: msg.timestamp || new Date().toISOString(),
          agent: msg.role === "assistant" ? (AGENT_NAMES[agentId] || agentId) : undefined,
        }));
        setMessages(mapped);
        messageIdRef.current = mapped.length + 1;
      }
      if (data?.conversation_id && typeof window !== "undefined") {
        window.localStorage.setItem(conversationKey(agentId, user?.id), data.conversation_id);
      }
      setHistoryStatus("idle");
    } catch (err: any) {
      setHistoryStatus("error");
      if (isNetworkError(err)) {
        setHistoryError(`Unable to reach backend at ${API_URL}.`);
      } else if (err?.status === 401) {
        setHistoryError("History unavailable on this server. Enable Personal Mode or sign in.");
      } else {
        setHistoryError(err?.detail || "Unable to load history.");
      }
    }
  };

  useEffect(() => {
    const handler = (event: Event) => {
      const detail = (event as CustomEvent)?.detail as { conversationId?: string | null } | undefined;
      if (!detail || typeof window === "undefined") return;
      const current = window.localStorage.getItem(conversationKey(selectedAgent, user?.id)) || undefined;
      if (!detail.conversationId || detail.conversationId === current) {
        loadConversation(selectedAgent, current);
      }
    };
    window.addEventListener("mycasa-chat-sync", handler as EventListener);
    return () => window.removeEventListener("mycasa-chat-sync", handler as EventListener);
  }, [selectedAgent, user?.id, chatAllowed]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    setMessages([]);
    messageIdRef.current = 1;

    if (isHistoryCleared(selectedAgent, user?.id)) {
      setHistoryStatus("idle");
      setHistoryError(null);
      return;
    }

    if (!chatAllowed) {
        setHistoryStatus("idle");
        setHistoryError("Backend unavailable. Start the API to load history.");
        return;
      }

    const storedConversation = window.localStorage.getItem(conversationKey(selectedAgent, user?.id)) || undefined;
    refreshSessions(selectedAgent);
    loadConversation(selectedAgent, storedConversation);
  }, [selectedAgent, chatAllowed, personalMode, isAuthenticated, user?.id, showArchivedSessions]);

  useEffect(() => {
    if (sessionsLoading) return;
    if (showArchivedSessions) return;
    if (typeof window === "undefined") return;
    const currentId = localStorage.getItem(conversationKey(selectedAgent, user?.id));
    if (!currentId) return;
    if (!sessions.find((session) => session.id === currentId)) {
      handleNewSession();
    }
  }, [sessions, sessionsLoading, showArchivedSessions, selectedAgent, user?.id]);

  // Fetch real agent status from system live endpoint (single source of truth)
  const fetchAgents = useCallback(async () => {
    try {
      const [liveRes, enabledRes, fleetRes] = await Promise.all([
        fetch(`${API_URL}/api/system/live`),
        fetch(`${API_URL}/api/settings/agents/enabled`),
        fetch(`${API_URL}/api/fleet/agents`),
      ]);

      let liveAgents: Record<string, any> = {};
      let enabledMap: Record<string, boolean> = {};
      let fleetAgents: Record<string, any> = {};

      if (liveRes.ok) {
        const liveData = await liveRes.json();
        liveAgents = liveData.agents?.agents || {};
      }

      if (enabledRes.ok) {
        enabledMap = await enabledRes.json();
      }
      if (fleetRes.ok) {
        const fleetData = await fleetRes.json();
        const items = Array.isArray(fleetData?.agents) ? fleetData.agents : [];
        fleetAgents = items.reduce((acc: Record<string, any>, agent: any) => {
          if (agent?.id) acc[agent.id] = agent;
          return acc;
        }, {});
      }

      const allAgentIds = new Set([
        ...Object.keys(liveAgents),
        ...Object.keys(enabledMap),
      ]);

      const agentList = Array.from(allAgentIds).map((id) => {
        const live = liveAgents[id] || {};
        const settingsId = toSettingsAgentId(id);
        const enabled =
          typeof enabledMap[settingsId] === "boolean"
            ? enabledMap[settingsId]
            : live.status && live.status !== "offline";
        const status = live.status || (enabled ? "available" : "offline");
        const fleetId = toFleetAgentId(id);
        const fleet = fleetAgents[fleetId] || {};
        return {
          id,
          name: AGENT_NAMES[id] || id,
          state: status,
          enabled,
          skills: Array.isArray(fleet.skills) ? fleet.skills : [],
          currentRequests: typeof fleet.current_requests === "number" ? fleet.current_requests : 0,
          defaultModel: fleet.default_model,
        };
      });

      // Add manager if not in list (it's always available)
      if (!agentList.find((a) => a.id === "manager")) {
        agentList.unshift({ id: "manager", name: "Galidima", state: "online", enabled: true });
      }

      // Sort: enabled first, then by name
      agentList.sort((a, b) => {
        if (a.enabled !== b.enabled) return a.enabled ? -1 : 1;
        return a.name.localeCompare(b.name);
      });

      setAgents(agentList);
    } catch (e) {
      // Fallback to basic manager
      setAgents([{ id: "manager", name: "Galidima", state: "online", enabled: true }]);
    } finally {
      setLoadingAgents(false);
    }
  }, []);

  useEffect(() => {
    setMounted(true);
    fetchAgents();
    // Refresh agent status every 30 seconds
    const interval = setInterval(fetchAgents, 30000);
    return () => clearInterval(interval);
  }, [fetchAgents]);

  useEffect(() => {
    const handler = () => fetchAgents();
    window.addEventListener("mycasa-system-sync", handler as EventListener);
    return () => window.removeEventListener("mycasa-system-sync", handler as EventListener);
  }, [fetchAgents]);

  useEffect(() => {
    let active = true;
    const fetchLlmStatus = async () => {
      try {
        const data = await apiFetch<any>("/api/settings/system");
        if (!active) return;
        setLlmStatus({
          loading: false,
          provider: data.llm_provider || "",
          authType: data.llm_auth_type || "",
          model: data.llm_model || "",
          apiKeySet: Boolean(data.llm_api_key_set),
          oauthConnected: Boolean(data.llm_oauth_connected),
          error: null,
        });
      } catch (e: any) {
        if (!active) return;
        setLlmStatus({
          loading: false,
          provider: "",
          authType: "",
          model: "",
          apiKeySet: false,
          oauthConnected: false,
          error: e?.detail || e?.message || "Unknown error",
        });
      }
    };
    fetchLlmStatus();
    const handler = () => fetchLlmStatus();
    window.addEventListener("mycasa-llm-status", handler as EventListener);
    return () => {
      active = false;
      window.removeEventListener("mycasa-llm-status", handler as EventListener);
    };
  }, [chatAllowed, personalMode, isAuthenticated]);

  const prevMessageCount = useRef(0);
  useEffect(() => {
    if (!expanded && !isEmbedded) return;
    const currentCount = messages.length;
    if (currentCount <= prevMessageCount.current) {
      prevMessageCount.current = currentCount;
      return;
    }
    prevMessageCount.current = currentCount;
    messagesEndRef.current?.scrollIntoView({ behavior: isEmbedded ? "auto" : "smooth" });
  }, [messages.length, expanded, isEmbedded]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (isEmbedded) return;
    const root = rootRef.current;
    if (!root) return;

    const updateOffset = () => {
      const height = root.getBoundingClientRect().height;
      const next = Math.max(72, Math.ceil(height) + 12);
      document.documentElement.style.setProperty("--global-chat-offset", `${next}px`);
    };

    updateOffset();

    let observer: ResizeObserver | null = null;
    if (typeof ResizeObserver !== "undefined") {
      observer = new ResizeObserver(updateOffset);
      observer.observe(root);
    }
    window.addEventListener("resize", updateOffset);

    return () => {
      if (observer) observer.disconnect();
      window.removeEventListener("resize", updateOffset);
    };
  }, [expanded, showAgentSettings, messages.length, isLoading, agents.length]);

  const toggleAgentEnabled = async (agentId: string, currentEnabled: boolean) => {
    setTogglingAgent(agentId);
    try {
      const settingsId = toSettingsAgentId(agentId);
      const res = await fetch(`${API_URL}/api/settings/agent/${settingsId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: !currentEnabled }),
      });
      if (res.ok) {
        // Update local state immediately
        setAgents((prev) =>
          prev.map((a) => (a.id === agentId ? { ...a, enabled: !currentEnabled } : a))
        );
        // Refresh to get actual state
        setTimeout(fetchAgents, 500);
        window.dispatchEvent(new CustomEvent("mycasa-system-sync"));
      }
    } catch (e) {
      console.error("Failed to toggle agent:", e);
    } finally {
      setTogglingAgent(null);
    }
  };

  const launchAgents = useCallback(async () => {
    if (launching) return;
    setLaunching(true);
    try {
      const res = await fetch(`${API_URL}/api/system/startup`, { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        const alreadyRunning = data.already_running;
        const success = data.success;
        let content = "Failed to launch agents.";

        if (success) {
          let liveStats: { online: number; total: number } | null = null;
          try {
            const liveRes = await fetch(`${API_URL}/api/system/live`);
            if (liveRes.ok) {
              const liveData = await liveRes.json();
              const stats = liveData.agents?.stats || {};
              const active = typeof stats.active === "number" ? stats.active : 0;
              const available = typeof stats.available === "number" ? stats.available : 0;
              const total = typeof stats.total === "number" ? stats.total : 0;
              liveStats = { online: active + available, total };
            }
          } catch (e) {
            liveStats = null;
          }

          if (alreadyRunning) {
            content = "System already running.";
          } else if (liveStats) {
            if (liveStats.total === 0) {
              content = "System online (no agents enabled).";
            } else {
              content = `System online (${liveStats.online}/${liveStats.total} agents ready).`;
            }
          } else {
            const started = data.agents_started?.length || 0;
            if (started > 0) {
              content = `Agents launched (${started}).`;
            } else {
              content = "Warning: No agents enabled to start.";
            }
          }

          window.dispatchEvent(new CustomEvent("mycasa-system-sync"));
        }

        setMessages((prev) => [
          ...prev,
          {
            id: nextMessageId(),
            role: "assistant",
            content,
            timestamp: new Date().toISOString(),
            agent: "System",
          },
        ]);
      } else {
        setMessages((prev) => [
          ...prev,
          {
            id: nextMessageId(),
            role: "assistant",
            content: "Failed to launch agents.",
            timestamp: new Date().toISOString(),
            agent: "System",
          },
        ]);
      }
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        {
          id: nextMessageId(),
          role: "assistant",
          content: "Failed to launch agents.",
          timestamp: new Date().toISOString(),
          agent: "System",
        },
      ]);
    } finally {
      setLaunching(false);
      fetchAgents();
    }
  }, [fetchAgents, launching, nextMessageId]);

  const setTaskAction = (taskId: string, action: string) => {
    setTaskActionState((prev) => ({ ...prev, [taskId]: action }));
  };

  const clearTaskAction = (taskId: string) => {
    setTaskActionState((prev) => {
      const next = { ...prev };
      delete next[taskId];
      return next;
    });
  };

  const handleTaskComplete = async (taskId: string, title?: string) => {
    if (!taskId) return;
    setTaskAction(taskId, "complete");
    try {
      await apiFetch(`/api/tasks/${taskId}/complete`, { method: "PATCH", body: JSON.stringify({}) });
      pushAssistantMessage(`Task "${title || taskId}" marked complete.`, AGENT_NAMES[selectedAgent] || selectedAgent);
      window.dispatchEvent(new CustomEvent("mycasa-chat-sync"));
      window.dispatchEvent(new CustomEvent("mycasa-system-sync"));
    } catch (err: any) {
      pushAssistantMessage(
        `Warning: Unable to complete task "${title || taskId}". ${err?.detail || err?.message || ""}`.trim(),
        "System"
      );
    } finally {
      clearTaskAction(taskId);
    }
  };

  const handleTaskDelete = async (taskId: string, title?: string) => {
    if (!taskId) return;
    setTaskAction(taskId, "delete");
    try {
      await apiFetch(`/api/tasks/${taskId}`, { method: "DELETE" });
      pushAssistantMessage(`Task "${title || taskId}" deleted.`, AGENT_NAMES[selectedAgent] || selectedAgent);
      window.dispatchEvent(new CustomEvent("mycasa-chat-sync"));
      window.dispatchEvent(new CustomEvent("mycasa-system-sync"));
    } catch (err: any) {
      pushAssistantMessage(
        `Warning: Unable to delete task "${title || taskId}". ${err?.detail || err?.message || ""}`.trim(),
        "System"
      );
    } finally {
      clearTaskAction(taskId);
    }
  };

  const handleTaskReassign = async (taskId: string, title: string | undefined, assigneeId: string) => {
    if (!taskId || !assigneeId) return;
    setTaskAction(taskId, `assign:${assigneeId}`);
    const assigneeLabel = AGENT_NAMES[assigneeId] || assigneeId;
    try {
      await apiFetch(`/api/tasks/${taskId}`, {
        method: "PATCH",
        body: JSON.stringify({ assigned_to: assigneeId }),
      });
      pushAssistantMessage(
        `Task "${title || taskId}" reassigned to ${assigneeLabel}.`,
        "Galidima"
      );
      window.dispatchEvent(new CustomEvent("mycasa-chat-sync"));
      window.dispatchEvent(new CustomEvent("mycasa-system-sync"));
    } catch (err: any) {
      pushAssistantMessage(
        `Warning: Unable to reassign task "${title || taskId}". ${err?.detail || err?.message || ""}`.trim(),
        "System"
      );
    } finally {
      clearTaskAction(taskId);
    }
  };

  const runJanitorPreflight = useCallback(
    async (optionsText: string) => {
      const allowDestructive = /--destructive|destructive|allow-destructive/i.test(optionsText);
      const useLive = /--live|live|use-live/i.test(optionsText);
      const includeOauth = /--oauth|oauth/i.test(optionsText);
      pushAssistantMessage(
        `Running Janitor preflight (${useLive ? "live backend" : "isolated"})${allowDestructive ? " with destructive checks" : ""}...`,
        "Janitor"
      );
      try {
        const payload: any = {
          isolated: !useLive,
          allow_destructive: allowDestructive,
          skip_oauth: !includeOauth,
          open_browser: includeOauth,
        };
        if (useLive) {
          payload.api_base = API_URL;
        }
        const result = await apiFetch<any>(
          "/api/janitor/run-preflight",
          { method: "POST", body: JSON.stringify(payload) },
          120000
        );
        const report = result?.report;
        const summaryItems = Array.isArray(report?.results) ? report.results : [];
        const failures = summaryItems.filter((r: any) => !r.ok);
        const okCount = summaryItems.length - failures.length;
        pushJanitorReport({
          okCount,
          failCount: failures.length,
          failures: failures.slice(0, 5).map((f: any) => ({
            name: f.name || "Check",
            detail: f.detail || "Check failed",
          })),
          options: {
            allowDestructive,
            useLive,
            includeOauth,
          },
        });
        if (failures.length === 0) {
          pushAssistantMessage("Preflight passed. No failures detected.", "Janitor");
        }
      } catch (err: any) {
        const detail = err?.detail || err?.message || "Preflight failed.";
        pushAssistantMessage(`Warning: Janitor preflight failed: ${detail}`, "Janitor");
      }
    },
    [pushAssistantMessage, pushJanitorReport]
  );

  const sendToAgents = async (
    agentIds: string[],
    message: string,
    addLocalResponse: (content: string, agent?: string) => void
  ) => {
    for (const agentId of agentIds) {
      const convKey = conversationKey(agentId, user?.id);
      const conversationId = typeof window !== "undefined" ? localStorage.getItem(convKey) || undefined : undefined;
      let data: any;
      try {
        data = agentId === "manager"
          ? await sendManagerChat(message, conversationId)
          : await sendAgentChat(agentId, message, conversationId);
      } catch (err: any) {
        const status = err?.status;
        const detail = err?.detail || err?.message;
        if (isNetworkError(err)) {
          addLocalResponse(
            `Unable to reach the backend at ${API_URL}. Start the server and try again.`,
            "System"
          );
          continue;
        }
        if (status === 401) {
          addLocalResponse(
            "This server requires sign-in. Enable Personal Mode in .env or sign in from the login page.",
            "System"
          );
        } else if (detail) {
          if (String(detail).toLowerCase().includes("api key")) {
            addLocalResponse(
              "LLM provider is not configured. Go to Settings → General → LLM Provider and connect Qwen OAuth or add an API key.",
              "System"
            );
            continue;
          }
          addLocalResponse(`Warning: ${detail}`, "System");
        } else {
          addLocalResponse(`Failed to reach ${AGENT_NAMES[agentId] || agentId}.`, "System");
        }
        continue;
      }

      if (data?.conversation_id && typeof window !== "undefined") {
        localStorage.setItem(convKey, data.conversation_id);
      }
      const agent = agents.find((a) => a.id === agentId);

      if (data?.error) {
        addLocalResponse(`Warning: ${data.error}`, "System");
        continue;
      }

      const assistantMessage: Message = {
        id: nextMessageId(),
        role: "assistant",
        content: data.response || "I received your message.",
        timestamp: new Date().toISOString(),
        agent: data.agent_name || agent?.name || AGENT_NAMES[agentId] || agentId,
        routedTo: data.routed_to || undefined,
        delegationNote: data.delegation_note || undefined,
        inputTokens: data.input_tokens_est,
        outputTokens: data.output_tokens_est,
        latencyMs: data.latency_ms,
        taskCreated: data.task_created,
      };

      setMessages((prev) => [...prev, assistantMessage]);
      setPendingRoute(null);
      refreshSessions(agentId);
      if (data?.task_created && typeof window !== "undefined") {
        const routed = data?.routed_to || "maintenance";
        setSelectedAgent(routed);
        window.dispatchEvent(new CustomEvent("mycasa-system-sync"));
        try {
          if (routed === "maintenance") {
            router.push("/maintenance");
          }
        } catch {
          // ignore navigation errors
        }
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isLoading) return;
    if (!chatAllowed) {
      const localMessage: Message = {
        id: nextMessageId(),
        role: "assistant",
        content: "Backend unavailable. Start the API and try again.",
        timestamp: new Date().toISOString(),
        agent: "System",
      };
      setMessages((prev) => [...prev, localMessage]);
      setPendingRoute(null);
      return;
    }

    const userMessage: Message = {
      id: nextMessageId(),
      role: "user",
      content: inputValue,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    setIsLoading(true);
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(clearedKey(selectedAgent, user?.id ?? null));
    }
    setPendingRoute(routeHintForMessage(userMessage.content, selectedAgent));

    const addLocalResponse = (content: string, agent?: string) => {
      const localMessage: Message = {
        id: nextMessageId(),
        role: "assistant",
        content,
        timestamp: new Date().toISOString(),
        agent: agent || "System",
      };
      setMessages((prev) => [...prev, localMessage]);
      setPendingRoute(null);
    };

    try {
      const trimmed = userMessage.content.trim();
      const commandMatch = trimmed.match(/^\/([a-zA-Z0-9_-]+)\b(.*)?$/);

      if (commandMatch) {
        const command = commandMatch[1].toLowerCase();
        const rest = (commandMatch[2] || "").trim();

        if (command === "help") {
          addLocalResponse(
            "Commands: /agents (list), /model <name> (set model for selected agent), /preflight [destructive] [live] (run Janitor checks), /janitor preflight [destructive] [live], /<agent> <message> or @agent. Example: /finance show my budget or @maintenance schedule AC check."
          );
          setIsLoading(false);
          return;
        }

        if (command === "preflight" || (command === "janitor" && rest.startsWith("preflight"))) {
          const optionsText = command === "janitor" ? rest.replace(/^preflight\s*/i, "") : rest;
          await runJanitorPreflight(optionsText);
          setIsLoading(false);
          return;
        }

        if (command === "agents") {
          const list = agents.map((a) => `${a.name} (@${a.id})`).join(", ");
          addLocalResponse(`Available agents: ${list}`);
          setIsLoading(false);
          return;
        }

        if (command === "model") {
          if (!rest) {
            addLocalResponse("Usage: /model <model-name> (applies to selected agent).");
            setIsLoading(false);
            return;
          }
          const fleetId = toFleetAgentId(selectedAgent);
          const modelRes = await fetch(`${API_URL}/api/fleet/agents/${fleetId}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ default_model: rest }),
          });
          if (modelRes.ok) {
            addLocalResponse(`Model set for ${AGENT_NAMES[selectedAgent] || selectedAgent}: ${rest}`);
          } else {
            addLocalResponse("Failed to update model. Check backend logs and model name.");
          }
          setIsLoading(false);
          return;
        }

        const agentFromCommand = resolveAgentId(command);
        if (agentFromCommand) {
          if (!rest) {
            addLocalResponse(`Tell me what to ask ${AGENT_NAMES[agentFromCommand] || agentFromCommand}.`);
            setIsLoading(false);
            return;
          }
          await sendToAgents([agentFromCommand], rest, addLocalResponse);
          setIsLoading(false);
          return;
        }
      }

      const mentionResult = extractMentionedAgents(trimmed);
      const targetAgents = mentionResult.agents.length > 0 ? mentionResult.agents : [selectedAgent];
      const messageContent = mentionResult.cleaned || trimmed;

      if (!messageContent) {
        addLocalResponse("Tell me what you want me to ask.");
        setIsLoading(false);
        return;
      }

      if (
        mentionResult.agents.includes("janitor") &&
        /^preflight(\b|:)/i.test(messageContent)
      ) {
        const optionsText = messageContent.replace(/^preflight\s*/i, "");
        await runJanitorPreflight(optionsText);
        setIsLoading(false);
        return;
      }

      await sendToAgents(targetAgents, messageContent, addLocalResponse);
    } catch (error) {
      let errorContent = "We can’t reach the backend. Start the server and try again.";
      if (error instanceof Error && error.name === "AbortError") {
        errorContent = "The request timed out. The response is taking longer than expected. Please try again.";
      }
      const errorMessage: Message = {
        id: nextMessageId(),
        role: "assistant",
        content: errorContent,
        timestamp: new Date().toISOString(),
        agent: "System",
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  // Count online/enabled agents
  const enabledAgents = agents.filter((a) => a.enabled);
  const onlineCount = agents.filter(
    (a) =>
      a.enabled &&
      (a.state === "active" ||
        a.state === "running" ||
        a.state === "online" ||
        a.state === "available" ||
        a.state === "idle" ||
        a.state === "busy")
  ).length;
  const llmConnected =
    llmStatus.authType === "qwen-oauth" ? llmStatus.oauthConnected : llmStatus.apiKeySet;
  const llmBadgeColor = llmStatus.loading
    ? "gray"
    : llmStatus.error
      ? "red"
      : llmConnected
        ? "green"
        : "yellow";
  const llmBadgeLabel = llmStatus.loading
    ? "LLM: checking"
    : llmStatus.error
      ? "LLM: unavailable"
      : llmConnected
        ? `LLM: ${llmStatus.authType === "qwen-oauth" ? "Qwen OAuth" : "API key"}`
        : "LLM: not connected";
  const llmTooltip = llmStatus.loading
    ? "Checking LLM connection status"
    : llmStatus.error
      ? `Status unavailable: ${llmStatus.error}`
      : `Provider: ${llmStatus.provider || "unknown"} • Model: ${llmStatus.model || "default"} • Auth: ${
          llmStatus.authType || "unknown"
        } • ${llmConnected ? "Connected" : "Not connected"}`;

  const showPanel = isEmbedded || expanded;

  const handleClearChat = async () => {
    const confirmClear = confirm("Clear chat history for this agent? This won't erase long-term memory.");
    if (!confirmClear) return;
    const convKey = conversationKey(selectedAgent, user?.id);
    const conversationId = typeof window !== "undefined" ? localStorage.getItem(convKey) || undefined : undefined;
    if (typeof window !== "undefined") {
      window.localStorage.setItem(clearedKey(selectedAgent, user?.id ?? null), String(Date.now()));
    }
    try {
      await apiFetch(`/api/agents/${selectedAgent}/history${conversationId ? `?conversation_id=${conversationId}` : ""}`, {
        method: "DELETE",
      });
      if (typeof window !== "undefined") {
        localStorage.removeItem(convKey);
      }
      setMessages([]);
      setHistoryStatus("idle");
      setHistoryError(null);
      try {
        const created = await createAgentConversation(selectedAgent);
        if (created?.conversation_id && typeof window !== "undefined") {
          localStorage.setItem(convKey, created.conversation_id);
        }
        await refreshSessions(selectedAgent);
      } catch {
        // ignore
      }
    } catch (e) {
      setHistoryStatus("error");
      setHistoryError(
        isNetworkError(e)
          ? `Unable to reach backend at ${API_URL}.`
          : (e as any)?.detail || (e as Error)?.message || "Failed to clear chat history."
      );
    }
  };

  const handleNewSession = async () => {
    if (!chatAllowed) return;
    try {
      const created = await createAgentConversation(selectedAgent);
      if (created?.conversation_id && typeof window !== "undefined") {
        localStorage.setItem(conversationKey(selectedAgent, user?.id), created.conversation_id);
      }
      setMessages([]);
      setHistoryStatus("idle");
      await refreshSessions(selectedAgent);
    } catch {
      // ignore
    }
  };

  const handleSelectSession = async (sessionId: string) => {
    if (!sessionId) return;
    if (typeof window !== "undefined") {
      localStorage.setItem(conversationKey(selectedAgent, user?.id), sessionId);
    }
    await loadConversation(selectedAgent, sessionId);
  };

  const handleDeleteSession = async (sessionId: string) => {
    if (!sessionId) return;
    try {
      await apiFetch(`/api/agents/${selectedAgent}/history?conversation_id=${sessionId}`, { method: "DELETE" });
      await refreshSessions(selectedAgent);
      const currentId = typeof window !== "undefined" ? localStorage.getItem(conversationKey(selectedAgent, user?.id)) : null;
      if (currentId === sessionId) {
        if (typeof window !== "undefined") {
          localStorage.removeItem(conversationKey(selectedAgent, user?.id));
        }
        setMessages([]);
        setHistoryStatus("idle");
        await handleNewSession();
      }
    } catch {
      // ignore
    }
  };

  const handleArchiveSession = async (sessionId: string) => {
    if (!sessionId) return;
    try {
      await archiveAgentConversation(selectedAgent, sessionId);
      await refreshSessions(selectedAgent);
      const currentId = typeof window !== "undefined" ? localStorage.getItem(conversationKey(selectedAgent, user?.id)) : null;
      if (currentId === sessionId) {
        await handleNewSession();
      }
    } catch {
      // ignore
    }
  };

  const handleRestoreSession = async (sessionId: string) => {
    if (!sessionId) return;
    try {
      await restoreAgentConversation(selectedAgent, sessionId);
      await refreshSessions(selectedAgent);
    } catch {
      // ignore
    }
  };

  const handleRenameSession = async (sessionId: string, currentTitle?: string | null) => {
    const nextTitle = prompt("Rename session", currentTitle || "");
    if (nextTitle === null) return;
    try {
      await renameAgentConversation(selectedAgent, sessionId, nextTitle.trim() || null);
      await refreshSessions(selectedAgent);
    } catch {
      // ignore
    }
  };

  const panelStyle = isEmbedded
    ? {
        marginBottom: -1,
        display: "flex",
        flexDirection: "column",
        height: "100%",
        minHeight: 640,
      }
    : {
        marginBottom: -1,
        display: "flex",
        flexDirection: "column",
        height: "min(680px, calc(100vh - 140px))",
      };

  const panel = (
    <Box
      className="global-chat-panel"
      style={panelStyle}
    >
          {/* Header with Agent Controls Toggle */}
          <Group
            justify="space-between"
            px="md"
            py="sm"
            className="global-chat-header"
          >
            <Group gap="sm">
              <ThemeIcon
                variant="light"
                color={agentTheme.color}
                size="sm"
                radius="sm"
                style={{ backgroundColor: `${agentTheme.accent}22` }}
              >
                <IconMessage size={14} />
              </ThemeIcon>
              <Stack gap={0}>
                <Text fw={600} size="sm">
                  Home Command • {agentTheme.label}
                </Text>
                <Text size="xs" c="dimmed">
                  {selectedAgent === "manager"
                    ? "Galidima routes requests and logs outcomes for your home"
                    : `Focused on ${agentTheme.label.toLowerCase()} workflows`}
                </Text>
                <Group gap={6} mt={4} wrap="wrap">
                  {(selectedSkills.length > 0 ? selectedSkills.slice(0, 4) : ["Skills unavailable"]).map(
                    (skill) => (
                      <Badge key={skill} size="xs" variant="light" color={agentTheme.color}>
                        {skill}
                      </Badge>
                    )
                  )}
                </Group>
                {activeAgents.length > 0 && (
                  <Group gap={6} mt={4} wrap="wrap">
                    <Text size="xs" c="dimmed">
                      Active now:
                    </Text>
                    {activeAgents.slice(0, 3).map((agent) => (
                      <Badge key={agent.id} size="xs" variant="light">
                        {agent.name} {agent.count}
                      </Badge>
                    ))}
                    {activeAgents.length > 3 && (
                      <Text size="xs" c="dimmed">
                        +{activeAgents.length - 3} more
                      </Text>
                    )}
                  </Group>
                )}
              </Stack>
            </Group>
            <Group gap="xs">
              <Badge size="sm" variant="light" color="green">
                {onlineCount}/{enabledAgents.length} online
              </Badge>
              <Tooltip label={llmTooltip}>
                <Badge size="sm" variant="light" color={llmBadgeColor}>
                  {llmBadgeLabel}
                </Badge>
              </Tooltip>
              <Tooltip label={showSessionsPanel ? "Hide sessions" : "Show sessions"}>
                <ActionIcon
                  variant={showSessionsPanel ? "light" : "subtle"}
                  color="gray"
                  size="sm"
                  onClick={() => setShowSessionsPanel((current) => !current)}
                >
                  <IconHistory size={14} />
                </ActionIcon>
              </Tooltip>
              <Tooltip label="Clear chat history">
                <ActionIcon
                  variant="subtle"
                  color="gray"
                  onClick={handleClearChat}
                  size="sm"
                >
                  <IconTrash size={14} />
                </ActionIcon>
              </Tooltip>
              <Tooltip label="Launch agents">
                <ActionIcon
                  variant="subtle"
                  color="green"
                  onClick={launchAgents}
                  size="sm"
                  loading={launching}
                >
                  <IconRocket size={14} />
                </ActionIcon>
              </Tooltip>
              <Tooltip label="Refresh">
                <ActionIcon
                  variant="subtle"
                  color="gray"
                  onClick={fetchAgents}
                  size="sm"
                  loading={loadingAgents}
                >
                  <IconRefresh size={14} />
                </ActionIcon>
              </Tooltip>
              <ActionIcon variant="subtle" color="gray" onClick={toggle} size="sm">
                <IconX size={14} />
              </ActionIcon>
            </Group>
          </Group>

          <Box className="global-chat-body">
            {showSessionsPanel && (
              <Box className="global-chat-sessions">
                <Box px="md" pb="sm" className="global-chat-sessions-inner">
                  <Group justify="space-between" align="center" mb="xs">
                    <Text size="xs" fw={600} c="dimmed">
                      Sessions
                    </Text>
                    <Group gap="xs">
                      <Button
                        size="xs"
                        variant="light"
                        leftSection={<IconPlus size={12} />}
                        onClick={handleNewSession}
                      >
                        New
                      </Button>
                      <Group gap={6}>
                        <Text size="xs" c="dimmed">Archived</Text>
                        <Switch
                          size="sm"
                          checked={showArchivedSessions}
                          onChange={(e) => setShowArchivedSessions(e.currentTarget.checked)}
                        />
                      </Group>
                    </Group>
                  </Group>
                  <ScrollArea style={{ flex: 1 }}>
                    <Stack gap="xs">
                      {sessionsLoading && (
                        <Text size="xs" c="dimmed">Loading sessions…</Text>
                      )}
                      {!sessionsLoading && sessions.length === 0 && (
                        <Text size="xs" c="dimmed">No sessions yet</Text>
                      )}
                      {sessions.map((session) => {
                        const label = session.title
                          || session.last_message?.slice(0, 48)
                          || (session.updated_at ? `Session ${new Date(session.updated_at).toLocaleDateString()}` : "Session");
                        const isActive = session.id === (typeof window !== "undefined" ? localStorage.getItem(conversationKey(selectedAgent, user?.id)) : null);
                        const isArchived = Boolean(session.archived_at);
                        return (
                          <Paper
                            key={session.id}
                            withBorder
                            p="xs"
                            radius="md"
                            onClick={() => handleSelectSession(session.id)}
                            style={{
                              cursor: "pointer",
                              borderColor: isActive ? "var(--mantine-color-blue-3)" : "var(--mantine-color-default-border)",
                              background: isActive ? "var(--mantine-color-blue-light)" : undefined,
                            }}
                          >
                            <Group justify="space-between" align="center" wrap="nowrap">
                              <Stack gap={2} style={{ minWidth: 0 }}>
                                <Text size="xs" fw={600} lineClamp={1}>
                                  {label}
                                </Text>
                                <Text size="xs" c="dimmed">
                                  {session.updated_at ? new Date(session.updated_at).toLocaleString() : "No activity yet"}
                                </Text>
                              </Stack>
                              <Group gap="xs">
                                {isActive && <Badge size="xs">Active</Badge>}
                                {isArchived && <Badge size="xs" color="gray">Archived</Badge>}
                                <ActionIcon
                                  size="xs"
                                  variant="subtle"
                                  color="blue"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleRenameSession(session.id, session.title);
                                  }}
                                >
                                  <IconEdit size={12} />
                                </ActionIcon>
                                {isArchived ? (
                                  <ActionIcon
                                    size="xs"
                                    variant="subtle"
                                    color="green"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleRestoreSession(session.id);
                                    }}
                                  >
                                    <IconRefresh size={12} />
                                  </ActionIcon>
                                ) : (
                                  <ActionIcon
                                    size="xs"
                                    variant="subtle"
                                    color="yellow"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleArchiveSession(session.id);
                                    }}
                                  >
                                    <IconArchive size={12} />
                                  </ActionIcon>
                                )}
                                <ActionIcon
                                  size="xs"
                                  variant="subtle"
                                  color="red"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleDeleteSession(session.id);
                                  }}
                                >
                                  <IconTrash size={12} />
                                </ActionIcon>
                              </Group>
                            </Group>
                          </Paper>
                        );
                      })}
                    </Stack>
                  </ScrollArea>
                  {sessionsError && (
                    <Text size="xs" c="red" mt="xs">
                      {sessionsError}
                    </Text>
                  )}
                </Box>
              </Box>
            )}

            <Box className="global-chat-main">
              <Box px="md" pb="sm">
                <Group gap="sm" align="center" wrap="wrap">
                  <Select
                    data={agentOptions.length ? agentOptions : [{ value: "manager", label: "Galidima" }]}
                    value={selectedAgent}
                    onChange={(value) => value && setSelectedAgent(value)}
                    placeholder="Select agent"
                    size="sm"
                    w={220}
                  />
                  <Group gap={6} wrap="nowrap">
                    {agents
                      .filter((a) => a.enabled)
                      .slice(0, 4)
                      .map((agent) => (
                        <Tooltip
                          key={agent.id}
                          label={`${agent.name} • ${getStatusLabel(agent.state, agent.enabled)}`}
                        >
                          <Paper
                            withBorder
                            py={4}
                            px={8}
                            radius="xl"
                            className="chat-agent-chip"
                            style={{
                              cursor: "pointer",
                              borderColor:
                                selectedAgent === agent.id
                                  ? tokens.colors.primary[500]
                                  : undefined,
                              backgroundColor:
                                selectedAgent === agent.id
                                  ? "var(--agent-chip-selected-bg)"
                                  : undefined,
                              flexShrink: 0,
                            }}
                            onClick={() => setSelectedAgent(agent.id)}
                          >
                            <Group gap={4}>
                              <Box
                                style={{
                                  width: 6,
                                  height: 6,
                                  borderRadius: "50%",
                                  backgroundColor: getStatusColor(agent.state, agent.enabled),
                                }}
                              />
                              <Text size="xs" fw={selectedAgent === agent.id ? 600 : 400}>
                                {agent.name.split(" ")[0]}
                              </Text>
                            </Group>
                          </Paper>
                        </Tooltip>
                      ))}
                  </Group>
                  <ActionIcon
                    variant={showAgentSettings ? "filled" : "subtle"}
                    color="gray"
                    size="sm"
                    onClick={() => setShowAgentSettings(!showAgentSettings)}
                  >
                    <IconSettings size={14} />
                  </ActionIcon>
                </Group>
              </Box>

          {/* Agent Controls Panel - More Prominent */}
          <Collapse in={showAgentSettings}>
            <Box
              px="sm"
              py="sm"
              className="global-chat-agent-panel"
              style={{
                borderBottom: "1px solid var(--mantine-color-default-border)",
                maxHeight: 220,
                overflowY: "auto",
              }}
            >
              <Group justify="space-between" mb="sm">
                <Group gap="xs">
                  <IconPower size={14} style={{ color: "var(--mantine-color-green-6)" }} />
                  <Text size="xs" fw={600}>
                    Agent controls
                  </Text>
                  <Badge size="xs" variant="light" color="green">
                    {enabledAgents.length} enabled
                  </Badge>
                </Group>
                <Text size="xs" c="dimmed">
                  Toggle availability
                </Text>
              </Group>
              <Stack gap={6}>
                {agents.map((agent) => (
                  <Paper
                    key={agent.id}
                    withBorder
                    p="xs"
                    radius="md"
                    className="global-chat-agent-row"
                    style={{
                      opacity: agent.enabled ? 1 : 0.6,
                      borderColor: agent.enabled
                        ? "var(--mantine-color-green-3)"
                        : "var(--mantine-color-gray-3)",
                      backgroundColor: agent.enabled
                        ? "var(--mantine-color-body)"
                        : "var(--mantine-color-gray-0)",
                    }}
                  >
                    <Group justify="space-between">
                      <Group gap="xs">
                        <Box
                          style={{
                            width: 10,
                            height: 10,
                            borderRadius: "50%",
                            backgroundColor: getStatusColor(agent.state, agent.enabled),
                            boxShadow: agent.enabled ? "0 0 6px " + getStatusColor(agent.state, agent.enabled) : "none",
                          }}
                        />
                        <div>
                          <Text size="xs" fw={600}>
                            {agent.name}
                          </Text>
                          <Text size="10px" c="dimmed">
                            {getStatusLabel(agent.state, agent.enabled)}
                          </Text>
                          {agent.skills && agent.skills.length > 0 && (
                            <Text size="10px" c="dimmed">
                              {agent.skills.slice(0, 2).join(" • ")}
                            </Text>
                          )}
                        </div>
                      </Group>
                      {agent.id !== "manager" ? (
                        <Switch
                          size="sm"
                          checked={agent.enabled}
                          onChange={() => toggleAgentEnabled(agent.id, agent.enabled)}
                          disabled={togglingAgent === agent.id}
                          color="green"
                          label={agent.enabled ? "ON" : "OFF"}
                          labelPosition="left"
                          styles={{
                            label: { fontSize: 10, fontWeight: 600, color: agent.enabled ? "var(--mantine-color-green-6)" : "var(--mantine-color-gray-5)" },
                          }}
                        />
                      ) : (
                        <Badge size="xs" variant="filled" color="blue">
                          Always On
                        </Badge>
                      )}
                    </Group>
                  </Paper>
                ))}
              </Stack>
            </Box>
          </Collapse>

          {/* Messages */}
          <ScrollArea style={{ flex: 1, minHeight: 0 }} p="sm" type="auto" className="global-chat-messages">
            <Stack gap="sm">
              {!chatAllowed && personalModeChecked && personalModeError && (
                <Alert color="red" title="Backend unavailable">
                  {personalModeError}
                </Alert>
              )}
              {chatAllowed && historyStatus === "error" && historyError && (
                <Alert color="red" title="History unavailable">
                  {historyError}
                </Alert>
              )}
              {!isLoading && messages.length === 0 && (
                <Box py="xl" style={{ textAlign: "center" }}>
                  <Text c="dimmed" size="sm">
                    Try one of these prompts:
                  </Text>
                  <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="xs" mt="sm">
                    {[
                      "Review today’s tasks",
                      "Summarize recent activity",
                      "Run a system health check",
                    ].map((prompt) => (
                      <Button
                        key={prompt}
                        size="xs"
                        variant="light"
                        onClick={() => setInputValue(prompt)}
                      >
                        {prompt}
                      </Button>
                    ))}
                  </SimpleGrid>
                </Box>
              )}
              {messages.map((message) => (
                <Group
                  key={message.id}
                  justify={message.role === "user" ? "flex-end" : "flex-start"}
                  align="flex-end"
                >
                  {message.role === "assistant" && (
                    <Avatar size="sm" color="primary" radius="xl">
                      <IconRobot size={14} />
                    </Avatar>
                  )}
                  <Paper
                    px="sm"
                    py="xs"
                    radius="lg"
                    className={message.role === "user" ? "chat-bubble chat-bubble-user" : "chat-bubble"}
                    style={{
                      maxWidth: "78%",
                      background: message.role === "user" ? undefined : "var(--chat-message-bg)",
                      color: message.role === "user" ? "white" : undefined,
                    }}
                  >
                    {message.agent && message.role === "assistant" && (
                      <Text size="xs" fw={600} c="dimmed" mb={2}>
                        {message.agent}
                      </Text>
                    )}
                    <Text size="sm">{message.content}</Text>
                    {message.role === "assistant" && (message.routedTo || message.taskCreated) && (
                      <Box mt={8}>
                        {(() => {
                          const target = message.routedTo || "maintenance";
                          const route = handoffRouteFor(target);
                          const label = AGENT_NAMES[target] || target;
                          const title = message.taskCreated?.title || "Task queued";
                          const due = message.taskCreated?.due_date || message.taskCreated?.scheduled_date;
                          const taskId = message.taskCreated?.task_id;
                          const assignedTo = message.taskCreated?.assigned_to;
                          const assignedLabel = assignedTo ? (AGENT_NAMES[assignedTo] || assignedTo) : null;
                          const actionState = taskId ? taskActionState[String(taskId)] : undefined;
                          const routedMeta = agents.find((agent) => agent.id === target);
                          return (
                            <Stack gap={6}>
                              <Paper
                                withBorder
                                radius="md"
                                p="xs"
                                style={{
                                  background: "var(--surface-2)",
                                  borderColor: "var(--border-1)",
                                }}
                              >
                                <Group justify="space-between" align="center" wrap="wrap">
                                  <Box>
                                    <Group gap={6} wrap="wrap">
                                      <Badge
                                        size="xs"
                                        variant="light"
                                        color="blue"
                                        leftSection={<IconArrowRight size={12} />}
                                      >
                                        Routed
                                      </Badge>
                                      <Text size="xs" fw={600}>
                                        {label}
                                      </Text>
                                      <Text size="xs" c="dimmed">
                                        queued
                                      </Text>
                                    </Group>
                                    <Text size="xs" c="dimmed" mt={4}>
                                      Manager assigned this to {label}.
                                    </Text>
                                  </Box>
                                  <Group gap="xs" wrap="wrap">
                                    {route && (
                                      <Button size="xs" variant="light" onClick={() => router.push(route)}>
                                        View
                                      </Button>
                                    )}
                                    {routedMeta && routedMeta.id !== "manager" && (
                                      <Button
                                        size="xs"
                                        variant="light"
                                        color={routedMeta.enabled ? "yellow" : "green"}
                                        onClick={() => toggleAgentEnabled(routedMeta.id, routedMeta.enabled)}
                                      >
                                        {routedMeta.enabled ? "Pause agent" : "Resume agent"}
                                      </Button>
                                    )}
                                  </Group>
                                </Group>
                              </Paper>
                              {message.taskCreated && (
                                <Paper
                                  withBorder
                                  radius="md"
                                  p="xs"
                                  style={{
                                    background: "var(--surface-2)",
                                    borderColor: "var(--border-1)",
                                  }}
                                >
                                  <Group justify="space-between" align="center" wrap="wrap">
                                    <Box>
                                      <Group gap={6} wrap="wrap">
                                        <Badge size="xs" variant="light" color="green">
                                          Created
                                        </Badge>
                                        <Text size="xs" fw={600} lineClamp={1}>
                                          {title}
                                        </Text>
                                      </Group>
                                      <Text size="xs" c="dimmed" mt={4}>
                                        {due ? `Due ${due}` : "No due date set"}
                                      </Text>
                                      {assignedLabel && (
                                        <Text size="xs" c="dimmed">
                                          Assigned to {assignedLabel}
                                        </Text>
                                      )}
                                    </Box>
                                    <Group gap="xs" wrap="wrap">
                                      {route && (
                                        <Button size="xs" variant="light" onClick={() => router.push(route)}>
                                          Open list
                                        </Button>
                                      )}
                                      {taskId && (
                                        <>
                                          <Menu withinPortal position="bottom-end">
                                            <Menu.Target>
                                              <Button
                                                size="xs"
                                                variant="light"
                                                loading={actionState?.startsWith("assign")}
                                              >
                                                Reassign
                                              </Button>
                                            </Menu.Target>
                                            <Menu.Dropdown>
                                              {assignableAgents.length === 0 && (
                                                <Menu.Item disabled>No agents available</Menu.Item>
                                              )}
                                              {assignableAgents.map((agent) => (
                                                <Menu.Item
                                                  key={agent.id}
                                                  onClick={() => handleTaskReassign(String(taskId), title, agent.id)}
                                                >
                                                  {agent.name}
                                                </Menu.Item>
                                              ))}
                                            </Menu.Dropdown>
                                          </Menu>
                                          <Button
                                            size="xs"
                                            variant="light"
                                            color="green"
                                            loading={actionState === "complete"}
                                            onClick={() => handleTaskComplete(String(taskId), title)}
                                          >
                                            Complete
                                          </Button>
                                          <Button
                                            size="xs"
                                            variant="light"
                                            color="red"
                                            loading={actionState === "delete"}
                                            onClick={() => handleTaskDelete(String(taskId), title)}
                                          >
                                            Delete
                                          </Button>
                                        </>
                                      )}
                                    </Group>
                                  </Group>
                                </Paper>
                              )}
                            </Stack>
                          );
                        })()}
                      </Box>
                    )}
                    {message.role === "assistant" && message.delegationNote && (
                      <Text size="xs" c="dimmed" mt={4}>
                        {message.delegationNote}
                      </Text>
                    )}
                    {message.role === "assistant" && message.janitorReport && (
                      <Box mt={8}>
                        <Paper
                          withBorder
                          radius="md"
                          p="sm"
                          style={{
                            background: "var(--surface-2)",
                            borderColor: "var(--border-1)",
                          }}
                        >
                          <Group justify="space-between" align="center" mb={6} wrap="wrap">
                            <Group gap="xs">
                              <Badge size="xs" variant="light" color={message.janitorReport.failCount > 0 ? "red" : "green"}>
                                {message.janitorReport.failCount > 0 ? "Issues" : "All clear"}
                              </Badge>
                              <Text size="xs" fw={600}>Janitor preflight</Text>
                            </Group>
                            <Group gap="xs">
                              <Button size="xs" variant="light" onClick={() => router.push("/janitor")}>
                                Open Janitor
                              </Button>
                              <Button
                                size="xs"
                                variant="light"
                                onClick={() => {
                                  const opts = message.janitorReport?.options;
                                  if (!opts) return;
                                  const parts = [];
                                  if (opts.allowDestructive) parts.push("destructive");
                                  if (opts.useLive) parts.push("live");
                                  if (opts.includeOauth) parts.push("oauth");
                                  runJanitorPreflight(parts.join(" "));
                                }}
                              >
                                Rerun
                              </Button>
                            </Group>
                          </Group>
                          <Group gap="xs" wrap="wrap">
                            <Badge size="xs" variant="light">Passed {message.janitorReport.okCount}</Badge>
                            <Badge size="xs" variant="light" color={message.janitorReport.failCount > 0 ? "red" : "green"}>
                              Failed {message.janitorReport.failCount}
                            </Badge>
                            <Badge size="xs" variant="light">
                              {message.janitorReport.options.useLive ? "Live" : "Isolated"}
                            </Badge>
                          </Group>
                          {message.janitorReport.failures.length > 0 ? (
                            <Stack gap={4} mt="sm">
                              {message.janitorReport.failures.map((fail, index) => (
                                <Group key={`${fail.name}-${index}`} gap="xs" wrap="nowrap">
                                  <Box
                                    style={{
                                      width: 6,
                                      height: 6,
                                      borderRadius: 999,
                                      background: "var(--mantine-color-red-5)",
                                      marginTop: 4,
                                    }}
                                  />
                                  <Box>
                                    <Text size="xs" fw={600}>
                                      {fail.name}
                                    </Text>
                                    <Text size="xs" c="dimmed">
                                      {fail.detail}
                                    </Text>
                                  </Box>
                                </Group>
                              ))}
                            </Stack>
                          ) : (
                            <Text size="xs" c="dimmed" mt="sm">
                              No issues detected. System checks passed.
                            </Text>
                          )}
                        </Paper>
                      </Box>
                    )}
                    {message.role === "assistant" && (message.latencyMs || message.inputTokens || message.outputTokens) && (
                      <Group gap={6} mt={6}>
                        {typeof message.latencyMs === "number" && (
                          <Badge size="xs" variant="light">Latency {message.latencyMs}ms</Badge>
                        )}
                        {typeof message.inputTokens === "number" && (
                          <Badge size="xs" variant="light">Input {message.inputTokens} tok</Badge>
                        )}
                        {typeof message.outputTokens === "number" && (
                          <Badge size="xs" variant="light">Output {message.outputTokens} tok</Badge>
                        )}
                      </Group>
                    )}
                    {mounted && message.timestamp && (
                      <Text
                        size="xs"
                        c={message.role === "user" ? "rgba(255,255,255,0.7)" : "dimmed"}
                        mt={4}
                      >
                        {new Date(message.timestamp).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </Text>
                    )}
                  </Paper>
                  {message.role === "user" && (
                    <Avatar size="sm" color="gray" radius="xl">
                      <IconUser size={14} />
                    </Avatar>
                  )}
                </Group>
              ))}
              {isLoading && (
                pendingRoute ? (
                  <Group justify="flex-start" align="flex-end">
                    <Avatar size="sm" color="primary" radius="xl">
                      <IconRobot size={14} />
                    </Avatar>
                    <Paper
                      px="sm"
                      py="xs"
                      radius="lg"
                      style={{ backgroundColor: "var(--chat-message-bg)" }}
                    >
                      <Stack gap={6}>
                        <Group gap="xs">
                          <Badge size="xs" variant="light" color="blue">
                            Coordinating
                          </Badge>
                          <Text size="sm" fw={600}>
                            {AGENT_NAMES[pendingRoute] || pendingRoute}
                          </Text>
                        </Group>
                        <Stack gap={4}>
                          <Group gap={6}>
                            <Box
                              style={{
                                width: 8,
                                height: 8,
                                borderRadius: 999,
                                background: "var(--mantine-color-blue-5)",
                              }}
                            />
                            <Text size="xs">Routing request</Text>
                          </Group>
                          <Group gap={6}>
                            <Box
                              style={{
                                width: 8,
                                height: 8,
                                borderRadius: 999,
                                background: "var(--mantine-color-gray-4)",
                              }}
                            />
                            <Text size="xs">Creating task</Text>
                          </Group>
                          <Group gap={6}>
                            <Loader size="xs" />
                            <Text size="xs">Syncing list</Text>
                          </Group>
                        </Stack>
                      </Stack>
                    </Paper>
                  </Group>
                ) : (
                  <Group justify="flex-start" align="flex-end">
                    <Avatar size="sm" color="primary" radius="xl">
                      <IconRobot size={14} />
                    </Avatar>
                    <Paper
                      px="sm"
                      py="xs"
                      radius="lg"
                      style={{ backgroundColor: "var(--chat-message-bg)" }}
                    >
                      <Group gap="xs">
                        <Loader size="xs" />
                        <Text size="sm" c="dimmed">Working on it…</Text>
                      </Group>
                    </Paper>
                  </Group>
                )
              )}
              <div ref={messagesEndRef} />
            </Stack>
          </ScrollArea>

          {/* Input */}
          <Box
            px="sm"
            py="xs"
            className="global-chat-input"
            style={{
              borderTop: "1px solid var(--mantine-color-default-border)",
            }}
          >
            <form onSubmit={handleSubmit}>
              <Group gap="sm">
                <TextInput
                  placeholder={
                    chatAllowed
                      ? `Message ${agentTheme.label}... (@agent or /help)`
                      : "Start the backend to send messages"
                  }
                  value={inputValue}
                  onChange={(e) => setInputValue(e.currentTarget.value)}
                  flex={1}
                  size="sm"
                  radius="md"
                  styles={{
                    input: {
                      border: "1px solid var(--border-1)",
                      backgroundColor: "var(--surface-2)",
                      boxShadow: "none",
                    },
                  }}
                />
                <ActionIcon
                  type="submit"
                  size="lg"
                  radius="md"
                  variant="filled"
                  color={agentTheme.color}
                  disabled={!inputValue.trim() || isLoading || !chatAllowed}
                >
                  <IconSend size={16} />
                </ActionIcon>
              </Group>
            </form>
          </Box>
            </Box>
          </Box>
    </Box>
  );

  return (
    <Box
      className={`global-chat${isEmbedded ? " global-chat--embedded" : ""}`}
      ref={rootRef}
      style={{
        position: isEmbedded ? "sticky" : "fixed",
        top: isEmbedded ? 88 : undefined,
        bottom: isEmbedded ? "auto" : 16,
        left: isEmbedded ? "auto" : "50%",
        right: "auto",
        transform: isEmbedded ? "none" : "translateX(-50%)",
        zIndex: 200,
        width: isEmbedded ? "100%" : "min(560px, calc(100vw - 32px))",
        minWidth: isEmbedded ? "100%" : undefined,
        maxWidth: isEmbedded ? "100%" : undefined,
        height: isEmbedded ? "100%" : undefined,
        alignSelf: isEmbedded ? "stretch" : undefined,
      }}
    >
      {/* Chat panel */}
      {isEmbedded ? panel : <Collapse in={showPanel}>{panel}</Collapse>}

      {!isEmbedded && (
        <Box onClick={toggle} className="global-chat-lip" data-expanded={expanded}>
          <Box className="global-chat-lip-inner">
            <Box className="global-chat-lip-notch" aria-hidden="true" />
            <Group
              justify="center"
              gap="xs"
              py={expanded ? 6 : 8}
              px="lg"
            >
              <ThemeIcon
                variant={expanded ? "light" : "filled"}
                color={agentTheme.color}
                size="sm"
                radius="md"
                style={{ transition: "opacity 200ms ease" }}
              >
                <IconMessage size={14} />
              </ThemeIcon>
              <Text fw={expanded ? 500 : 600} size="xs" c={expanded ? "dimmed" : "gray.7"}>
                {lipTitle}
              </Text>
              {!expanded && (
                <Badge
                  size="xs"
                  variant="light"
                  color={onlineCount > 0 ? "green" : "gray"}
                >
                  {onlineCount}
                </Badge>
              )}
              {expanded ? (
                <IconChevronDown size={14} style={{ color: "var(--mantine-color-dimmed)" }} />
              ) : (
                <IconChevronUp size={14} style={{ color: "var(--mantine-color-gray-6)" }} />
              )}
            </Group>
          </Box>
        </Box>
      )}
    </Box>
  );
}
