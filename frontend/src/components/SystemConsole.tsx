"use client";

import { useState, useEffect, useRef, useMemo, useCallback } from "react";
import { getApiBaseUrl } from "@/lib/api";
import {
  Box,
  Group,
  Text,
  TextInput,
  ActionIcon,
  Stack,
  Badge,
  Paper,
  Transition,
  ScrollArea,
  Kbd,
  Loader,
  Tooltip,
  Collapse,
  Menu,
  UnstyledButton,
  TypographyStylesProvider,
  Avatar,
} from "@mantine/core";
import {
  IconSend,
  IconChevronUp,
  IconChevronDown,
  IconTerminal,
  IconTrash,
  IconCommand,
  IconSparkles,
  IconSettings,
  IconRocket,
  IconX,
  IconAt,
} from "@tabler/icons-react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import { useWizard } from "./SetupWizard/WizardProvider";
import { useAgentContext, AGENTS } from "@/lib/AgentContext";
import { sendManagerChat, sendAgentChat } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";

// ============ TYPES ============
interface Message {
  id: string;
  role: "user" | "system";
  text: string;
  timestamp: string;
  isCommand?: boolean;
  isLoading?: boolean;
  exitCode?: number;
  isError?: boolean;
  agentName?: string;
  agentEmoji?: string;
  routedTo?: string;
}

interface SystemStats {
  agents_online: number;
  tasks_pending: number;
  cost_total: number | null;
}

interface AgentCommand {
  command: string;
  description: string;
  agent: string;
  emoji: string;
}

// ============ AGENT COMMANDS ============
const AGENT_COMMANDS: AgentCommand[] = [
  // Agent targeting with @
  { command: "@Mamadou", description: "Talk to Finance Manager", agent: "Finance", emoji: "💰" },
  { command: "@Ousmane", description: "Talk to Maintenance Manager", agent: "Maintenance", emoji: "🔧" },
  { command: "@Aïcha", description: "Talk to Security Manager", agent: "Security", emoji: "🛡️" },
  { command: "@Malik", description: "Talk to Contractors Manager", agent: "Contractors", emoji: "👷" },
  { command: "@Zainab", description: "Talk to Projects Manager", agent: "Projects", emoji: "📋" },
  { command: "@Salimata", description: "Talk to Janitor", agent: "Janitor", emoji: "🧹" },
  { command: "@Amina", description: "Talk to Mail Agent", agent: "Mail", emoji: "✉️" },
  { command: "@Backup", description: "Talk to Backup Agent", agent: "Backup", emoji: "🗄️" },
  
  // Finance Agent 💰 - Extensive capabilities
  { command: "/portfolio", description: "View holdings & allocation", agent: "Finance", emoji: "💰" },
  { command: "/analyze", description: "Deep analysis of positions", agent: "Finance", emoji: "💰" },
  { command: "/recommend", description: "Get buy/sell recommendations", agent: "Finance", emoji: "💰" },
  { command: "/project", description: "Portfolio projections & growth", agent: "Finance", emoji: "💰" },
  { command: "/rebalance", description: "Rebalancing suggestions", agent: "Finance", emoji: "💰" },
  { command: "/sectors", description: "Sector analysis & trends", agent: "Finance", emoji: "💰" },
  { command: "/laggards", description: "Underperforming positions", agent: "Finance", emoji: "💰" },
  { command: "/winners", description: "Top performing positions", agent: "Finance", emoji: "💰" },
  { command: "/dividends", description: "Dividend income analysis", agent: "Finance", emoji: "💰" },
  { command: "/bills", description: "View upcoming bills", agent: "Finance", emoji: "💰" },
  { command: "/budget", description: "Budget overview", agent: "Finance", emoji: "💰" },
  { command: "/spending", description: "Monthly spending", agent: "Finance", emoji: "💰" },
  
  // Inbox / Mail 📬
  { command: "/inbox", description: "View inbox messages", agent: "Inbox", emoji: "📬" },
  { command: "/unread", description: "Show only unread", agent: "Inbox", emoji: "📬" },
  { command: "/markread", description: "Mark all as read", agent: "Inbox", emoji: "📬" },
  { command: "/archive", description: "Archive old messages", agent: "Inbox", emoji: "📬" },
  { command: "/search", description: "Search messages", agent: "Inbox", emoji: "📬" },
  { command: "/sync", description: "Sync inbox now", agent: "Inbox", emoji: "📬" },
  
  // Maintenance Agent 🔧
  { command: "/tasks", description: "Maintenance tasks", agent: "Maintenance", emoji: "🔧" },
  { command: "/schedule", description: "Upcoming maintenance", agent: "Maintenance", emoji: "🔧" },
  { command: "/readings", description: "Home readings", agent: "Maintenance", emoji: "🔧" },
  { command: "/overdue", description: "Overdue items", agent: "Maintenance", emoji: "🔧" },
  
  // Contractors Agent 👷
  { command: "/contractors", description: "List contractors", agent: "Contractors", emoji: "👷" },
  { command: "/reviews", description: "Contractor ratings", agent: "Contractors", emoji: "👷" },
  { command: "/hire", description: "Find a contractor", agent: "Contractors", emoji: "👷" },
  
  // Projects Agent 📋
  { command: "/projects", description: "Active projects", agent: "Projects", emoji: "📋" },
  { command: "/milestones", description: "Project milestones", agent: "Projects", emoji: "📋" },
  { command: "/timeline", description: "Project timeline", agent: "Projects", emoji: "📋" },
  
  // Janitor Agent 🧹
  { command: "/health", description: "System health check", agent: "Janitor", emoji: "🧹" },
  { command: "/logs", description: "View system logs", agent: "Janitor", emoji: "🧹" },
  { command: "/cleanup", description: "Run cleanup tasks", agent: "Janitor", emoji: "🧹" },
  { command: "/debug", description: "Debug info", agent: "Janitor", emoji: "🧹" },
  
  // Security Agent 🛡️
  { command: "/security", description: "Security status", agent: "Security", emoji: "🛡️" },
  { command: "/scan", description: "Run security scan", agent: "Security", emoji: "🛡️" },
  { command: "/threats", description: "View threats", agent: "Security", emoji: "🛡️" },
  { command: "/credentials", description: "Credential health", agent: "Security", emoji: "🛡️" },
  
  // System
  { command: "/status", description: "System status", agent: "System", emoji: "⚡" },
  { command: "/agents", description: "Active agents", agent: "System", emoji: "🤖" },
  { command: "/launch", description: "Launch all agents", agent: "System", emoji: "🚀" },
  { command: "/help", description: "All commands", agent: "System", emoji: "❓" },
];

// ============ CONSTANTS ============
const API_URL = getApiBaseUrl();
const conversationKey = (agentId: string, userId?: number | null) =>
  `mycasa_console_conversation_${agentId}:${userId ?? "anon"}`;

// Avatar images for agents
const AVATAR_IMAGES: Record<string, string> = {
  manager: "https://images.unsplash.com/photo-1560250097-0b93528c311a?w=200&h=200&fit=crop&crop=face&sat=-100&con=1.1",
  finance: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=200&h=200&fit=crop&crop=face&sat=-100&con=1.1",
  maintenance: "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=200&h=200&fit=crop&crop=face&sat=-100&con=1.1",
  security: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=200&h=200&fit=crop&crop=face&sat=-100&con=1.1",
  contractors: "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=200&h=200&fit=crop&crop=face&sat=-100&con=1.1",
  projects: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200&h=200&fit=crop&crop=face&sat=-100&con=1.1",
  janitor: "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=200&h=200&fit=crop&crop=face&sat=-100&con=1.1",
  "mail-skill": "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=200&h=200&fit=crop&crop=face&sat=-100&con=1.1",
  "backup-recovery": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=200&h=200&fit=crop&crop=face&sat=-100&con=1.1",
};

const AGENT_ALIASES: Record<string, string[]> = {
  manager: ["manager", "galidima", "gm"],
  finance: ["finance", "mamadou"],
  maintenance: ["maintenance", "ousmane", "maint"],
  security: ["security", "security-manager", "aicha"],
  contractors: ["contractors", "malik", "contractor"],
  projects: ["projects", "zainab", "project"],
  janitor: ["janitor", "salimata", "sule"],
  "mail-skill": ["mail", "mail-skill", "amina", "inbox"],
  "backup-recovery": ["backup", "backup-recovery"],
};

const normalizeAgentToken = (value: string) =>
  value
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");

function resolveAgentId(token: string): string | null {
  const normalized = normalizeAgentToken(token);
  for (const [id, aliases] of Object.entries(AGENT_ALIASES)) {
    if (aliases.some((alias) => normalizeAgentToken(alias) === normalized)) return id;
  }
  return null;
}

export function SystemConsole() {
  const { user } = useAuth();
  const [expanded, setExpanded] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [stats, setStats] = useState<SystemStats>({ agents_online: 0, tasks_pending: 0, cost_total: null });
  const [showCommands, setShowCommands] = useState(false);
  const [launching, setLaunching] = useState(false);
  
  // Hide console when wizard is open
  const { showWizard } = useWizard();
  
  // Agent targeting context
  const { targetAgent, clearAgent, selectAgent, shouldFocusConsole, setShouldFocusConsole } = useAgentContext();

  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Filter commands based on input (supports / and @)
  const filteredCommands = useMemo(() => {
    if (!input.startsWith("/") && !input.startsWith("@")) return [];
    const search = input.slice(1).toLowerCase();
    const prefix = input.charAt(0);
    return AGENT_COMMANDS.filter(c => {
      // If user types @, show @ commands
      if (prefix === "@") {
        return c.command.startsWith("@") && (
          c.command.slice(1).toLowerCase().includes(search) ||
          c.description.toLowerCase().includes(search)
        );
      }
      // If user types /, show / commands
      return c.command.startsWith("/") && (
        c.command.slice(1).toLowerCase().includes(search) ||
        c.description.toLowerCase().includes(search)
      );
    }).slice(0, 8);
  }, [input]);

  const fetchStats = useCallback(async () => {
    try {
      const [monitorRes, costRes] = await Promise.all([
        fetch(`${API_URL}/api/system/monitor`),
        fetch(`${API_URL}/api/fleet/costs`),
      ]);

      let tasksPending = 0;
      let agentsOnline = 0;
      if (monitorRes.ok) {
        const data = await monitorRes.json();
        const processes = data.processes || [];
        tasksPending = processes.reduce((sum: number, p: any) =>
          sum + (p.pending_tasks || 0), 0);
        agentsOnline = processes.filter((p: any) =>
          p.state === "running" || p.state === "idle"
        ).length;
      }

      let costTotal: number | null = null;
      if (costRes.ok) {
        const costData = await costRes.json();
        if (typeof costData.total_cost_usd === "number") {
          costTotal = costData.total_cost_usd;
        }
      }

      setStats({
        agents_online: agentsOnline,
        tasks_pending: tasksPending,
        cost_total: costTotal,
      });
    } catch (e) {
      // Silent fail - keep last known stats
    }
  }, []);

  // Fetch stats from system/monitor for consistency
  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 10000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  // Auto-scroll
  useEffect(() => {
    if (scrollRef.current && expanded) {
      scrollRef.current.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
    }
  }, [messages, expanded]);

  // Focus on expand
  useEffect(() => {
    if (expanded) inputRef.current?.focus();
  }, [expanded]);

  // Show command suggestions (/ or @)
  useEffect(() => {
    setShowCommands((input.startsWith("/") || input.startsWith("@")) && filteredCommands.length > 0);
  }, [input, filteredCommands.length]);
  
  // Focus when agent is selected from AgentManager
  useEffect(() => {
    if (shouldFocusConsole) {
      setExpanded(true);
      setTimeout(() => inputRef.current?.focus(), 100);
      setShouldFocusConsole(false);
    }
  }, [shouldFocusConsole, setShouldFocusConsole]);

  const launchSystem = useCallback(async () => {
    if (launching) return false;
    setLaunching(true);
    try {
      const res = await fetch(`${API_URL}/api/system/startup`, { method: "POST" });
      if (!res.ok) {
        return { success: false, started: 0, alreadyRunning: false, online: null, total: null };
      }
      const data = await res.json();
      await fetchStats();
      let online: number | null = null;
      let total: number | null = null;
      try {
        const liveRes = await fetch(`${API_URL}/api/system/live`);
        if (liveRes.ok) {
          const liveData = await liveRes.json();
          const stats = liveData.agents?.stats || {};
          const active = typeof stats.active === "number" ? stats.active : 0;
          const available = typeof stats.available === "number" ? stats.available : 0;
          online = active + available;
          total = typeof stats.total === "number" ? stats.total : 0;
        }
      } catch (e) {
        online = null;
        total = null;
      }
      if (data.success) {
        window.dispatchEvent(new CustomEvent("mycasa-system-sync"));
      }
      return {
        success: !!data.success,
        started: data.agents_started?.length || 0,
        alreadyRunning: !!data.already_running,
        online,
        total,
      };
    } catch {
      return { success: false, started: 0, alreadyRunning: false, online: null, total: null };
    } finally {
      setLaunching(false);
    }
  }, [fetchStats, launching]);

  // Keyboard shortcut
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "`" && !e.ctrlKey && !e.metaKey) {
        const tag = (e.target as HTMLElement).tagName;
        if (tag !== "INPUT" && tag !== "TEXTAREA") {
          e.preventDefault();
          setExpanded(true);
          setTimeout(() => inputRef.current?.focus(), 100);
        }
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  // Listen for messages from other pages (Finance, System, etc.)
  useEffect(() => {
    const handleExternalMessage = (event: CustomEvent<{ message: string; source: string }>) => {
      const { message } = event.detail;
      if (message && !isLoading) {
        // Expand the console and send the message
        setExpanded(true);
        // Send the message directly
        sendExternalMessage(message);
      }
    };

    window.addEventListener("galidima-chat-send" as any, handleExternalMessage);
    return () => window.removeEventListener("galidima-chat-send" as any, handleExternalMessage);
  }, [isLoading]);

  // Function to send messages from external sources
  const sendExternalMessage = useCallback(async (messageText: string) => {
    if (!messageText.trim() || isLoading) return;
    
    const userMessage = messageText.trim();
    const isCommand = userMessage.startsWith("/");

    const userMsg: Message = {
      id: `user_${Date.now()}`,
      role: "user",
      text: userMessage,
      timestamp: new Date().toISOString(),
      isCommand,
    };

    const placeholder: Message = {
      id: `sys_${Date.now()}`,
      role: "system",
      text: "",
      timestamp: new Date().toISOString(),
      isLoading: true,
      isCommand,
    };

    setMessages(prev => [...prev, userMsg, placeholder]);
    setIsLoading(true);

    try {
      const storedConversation = typeof window !== "undefined"
        ? localStorage.getItem(conversationKey("manager", user?.id)) || undefined
        : undefined;
      const data = await sendManagerChat(userMessage, storedConversation);
      if (data?.conversation_id && typeof window !== "undefined") {
        localStorage.setItem(conversationKey("manager", user?.id), data.conversation_id);
      }
        setMessages(prev => {
          const updated = [...prev];
          const lastIdx = updated.length - 1;
          if (updated[lastIdx]?.isLoading) {
            updated[lastIdx] = {
              ...updated[lastIdx],
              text: data.response || "(no response)",
              isLoading: false,
              exitCode: data.exit_code ?? undefined,
              agentName: data.agent_name,
              agentEmoji: data.agent_emoji,
              routedTo: data.routed_to,
            };
          }
          return updated;
        });
    } catch (e: any) {
      const message = e?.detail || e?.message || "Connection error";
      setMessages(prev => {
        const updated = [...prev];
        const lastIdx = updated.length - 1;
        if (updated[lastIdx]?.isLoading) {
          updated[lastIdx] = {
            ...updated[lastIdx],
            text: `❌ ${message}`,
            isLoading: false,
            isError: true,
          };
        }
        return updated;
      });
    } finally {
      setIsLoading(false);
    }
  }, [isLoading]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    let userMessage = input.trim();
    const isCommand = userMessage.startsWith("/");

    if (isCommand && userMessage.toLowerCase().startsWith("/launch")) {
      const userMsg: Message = {
        id: `user_${Date.now()}`,
        role: "user",
        text: userMessage,
        timestamp: new Date().toISOString(),
        isCommand: true,
      };

      const placeholder: Message = {
        id: `sys_${Date.now()}`,
        role: "system",
        text: "Launching agents...",
        timestamp: new Date().toISOString(),
        isLoading: true,
        isCommand: true,
      };

      setMessages(prev => [...prev, userMsg, placeholder]);
      setInput("");
      setShowCommands(false);
      setIsLoading(true);

      const result = await launchSystem();
      setMessages(prev => {
        const updated = [...prev];
        const lastIdx = updated.length - 1;
        if (updated[lastIdx]?.isLoading) {
          let text = "❌ Failed to launch agents.";
          if (result && result.success && result.alreadyRunning) {
            text = "✅ System already running.";
          } else if (result && result.success && result.total !== null) {
            if (result.total === 0) {
              text = "✅ System online (no agents enabled).";
            } else {
              text = `✅ System online (${result.online}/${result.total} agents ready).`;
            }
          } else if (result && result.success && result.started > 0) {
            text = `✅ Agents launched (${result.started}).`;
          } else if (result && result.success && result.started === 0) {
            text = "⚠️ No agents enabled to start.";
          }
          updated[lastIdx] = {
            ...updated[lastIdx],
            text,
            isLoading: false,
            isError: !(result && result.success),
          };
        }
        return updated;
      });
      setIsLoading(false);
      return;
    }
    
    // If there's a targeted agent, prefix the message with @AgentName
    // unless the user already included an @ mention
    let routeToAgent: string | null = null;
    if (targetAgent && !userMessage.startsWith("@")) {
      routeToAgent = targetAgent.id;
    }
    
    // Check if message starts with @AgentName and extract agent
    const atMatch = userMessage.match(/^@([\p{L}\p{N}_-]+)\s*(.*)/u);
    if (atMatch) {
      const resolved = resolveAgentId(atMatch[1]);
      const agent = resolved ? AGENTS.find(a => a.id === resolved) : undefined;
      if (agent) {
        routeToAgent = agent.id;
        userMessage = atMatch[2] || `Talk to ${agent.displayName}`;
      }
    }

    const userMsg: Message = {
      id: `user_${Date.now()}`,
      role: "user",
      text: targetAgent && !input.startsWith("@") ? `@${targetAgent.displayName} ${userMessage}` : userMessage,
      timestamp: new Date().toISOString(),
      isCommand,
    };

    const placeholder: Message = {
      id: `sys_${Date.now()}`,
      role: "system",
      text: "",
      timestamp: new Date().toISOString(),
      isLoading: true,
      isCommand,
    };

    setMessages(prev => [...prev, userMsg, placeholder]);
    setInput("");
    setShowCommands(false);
    setIsLoading(true);

    try {
      const target = routeToAgent || "manager";
      const storedConversation = typeof window !== "undefined"
        ? localStorage.getItem(conversationKey(target, user?.id)) || undefined
        : undefined;

      const data = target === "manager"
        ? await sendManagerChat(userMessage, storedConversation)
        : await sendAgentChat(target, userMessage, storedConversation);

      if (data?.conversation_id && typeof window !== "undefined") {
        localStorage.setItem(conversationKey(target, user?.id), data.conversation_id);
      }
        setMessages(prev => {
          const updated = [...prev];
          const lastIdx = updated.length - 1;
          if (updated[lastIdx]?.isLoading) {
            updated[lastIdx] = {
              ...updated[lastIdx],
              text: data.response || "(no response)",
              isLoading: false,
              exitCode: data.exit_code ?? undefined,
              agentName: data.agent_name,
              agentEmoji: data.agent_emoji,
              routedTo: data.routed_to,
            };
          }
          return updated;
        });
    } catch (e: any) {
      const message = e?.detail || e?.message || "Connection error";
      setMessages(prev => {
        const updated = [...prev];
        const lastIdx = updated.length - 1;
        if (updated[lastIdx]?.isLoading) {
          updated[lastIdx] = {
            ...updated[lastIdx],
            text: message,
            isLoading: false,
            isError: true,
          };
        }
        return updated;
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleCommandSelect = (command: string) => {
    if (command.startsWith("@")) {
      const token = command.slice(1).trim();
      const resolved = resolveAgentId(token);
      if (resolved) {
        const mentionToken =
          resolved === "mail-skill" ? "mail" : resolved === "backup-recovery" ? "backup" : resolved;
        selectAgent(resolved, { greet: false });
        setInput(`@${mentionToken} `);
        setShowCommands(false);
        inputRef.current?.focus();
        return;
      }
    }
    setInput(command + " ");
    setShowCommands(false);
    inputRef.current?.focus();
  };

  const handleClear = () => setMessages([]);

  const formatTime = (ts: string) => {
    try {
      return new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } catch {
      return "";
    }
  };

  // Hide when wizard is open
  if (showWizard) {
    return null;
  }

  return (
    <Box
      style={{
        position: "fixed",
        bottom: 0,
        left: 0,
        right: 0,
        zIndex: 1000,
        background: "linear-gradient(to top, var(--mantine-color-dark-8) 0%, var(--mantine-color-dark-8) 90%, transparent 100%)",
        paddingTop: 8,
      }}
    >
      <Paper
        mx="auto"
        radius="lg"
        style={{
          maxWidth: 700,
          margin: "0 auto 12px auto",
          overflow: "hidden",
          boxShadow: "0 -4px 24px rgba(0,0,0,0.3), 0 0 0 1px rgba(99,102,241,0.15)",
          background: "var(--mantine-color-dark-7)",
          border: "1px solid var(--mantine-color-dark-5)",
        }}
      >
        {/* Collapsed Header */}
        <Group
          px="md"
          py="xs"
          justify="space-between"
          style={{
            cursor: "pointer",
            background: expanded 
              ? targetAgent 
                ? `linear-gradient(90deg, rgba(${targetAgent.color === "teal" ? "20,184,166" : targetAgent.color === "blue" ? "59,130,246" : targetAgent.color === "red" ? "239,68,68" : targetAgent.color === "orange" ? "249,115,22" : targetAgent.color === "grape" ? "168,85,247" : targetAgent.color === "cyan" ? "34,211,238" : "99,102,241"},0.15) 0%, transparent 100%)`
                : "linear-gradient(90deg, rgba(99,102,241,0.12) 0%, rgba(79,70,229,0.08) 100%)"
              : "transparent",
            borderBottom: expanded ? "1px solid var(--mantine-color-dark-5)" : undefined,
          }}
          onClick={() => setExpanded(!expanded)}
        >
          <Group gap="sm">
            {targetAgent ? (
              <>
                <Avatar
                  src={AVATAR_IMAGES[targetAgent.id]}
                  size={24}
                  radius="xl"
                  style={{ border: "2px solid var(--mantine-color-green-6)" }}
                />
                <Text size="sm" fw={600} c="gray.3">{targetAgent.displayName}</Text>
                <Badge size="xs" variant="light" color={targetAgent.color}>{targetAgent.name}</Badge>
                <Tooltip label="Clear target, talk to Galidima">
                  <ActionIcon 
                    size="xs" 
                    variant="subtle" 
                    color="gray" 
                    onClick={(e) => { e.stopPropagation(); clearAgent(); }}
                  >
                    <IconX size={12} />
                  </ActionIcon>
                </Tooltip>
              </>
            ) : (
              <>
                <IconSparkles size={18} style={{ color: "var(--mantine-color-indigo-4)" }} />
                <Text size="sm" fw={600} c="gray.3">Galidima</Text>
                <Badge size="xs" variant="dot" color="green">Manager</Badge>
              </>
            )}
          </Group>
          
          <Group gap="sm">
            <Badge size="xs" variant="light" color="indigo">{stats.agents_online} agents online</Badge>
            <Badge size="xs" variant="light" color={stats.tasks_pending > 0 ? "orange" : "gray"}>
              {stats.tasks_pending} tasks
            </Badge>
            <Badge size="xs" variant="light" color={stats.cost_total === null ? "gray" : "teal"}>
              {stats.cost_total === null ? "Cost unavailable" : `$${stats.cost_total.toFixed(2)} total`}
            </Badge>
            
            <Text size="xs" c="dimmed" ml="xs">
              Press <Kbd size="xs">`</Kbd> to focus
            </Text>
            
            <Tooltip label="Turn On System">
              <ActionIcon 
                variant="subtle" 
                color="green" 
                size="sm"
                loading={launching}
                onClick={async (e) => { 
                  e.stopPropagation();
                  const result = await launchSystem();
                  let text = "❌ Failed to launch agents.";
                  if (result && result.success && result.alreadyRunning) {
                    text = "✅ System already running.";
                  } else if (result && result.success && result.total !== null) {
                    if (result.total === 0) {
                      text = "✅ System online (no agents enabled).";
                    } else {
                      text = `✅ System online (${result.online}/${result.total} agents ready).`;
                    }
                  } else if (result && result.success && result.started > 0) {
                    text = `✅ Agents launched (${result.started}).`;
                  } else if (result && result.success && result.started === 0) {
                    text = "⚠️ No agents enabled to start.";
                  }
                  setMessages(prev => ([
                    ...prev,
                    {
                      id: `sys_${Date.now()}`,
                      role: "system",
                      text,
                      timestamp: new Date().toISOString(),
                      isError: !(result && result.success),
                    }
                  ]));
                }}
              >
                <IconRocket size={14} />
              </ActionIcon>
            </Tooltip>
            
            <Tooltip label="Settings">
              <ActionIcon 
                variant="subtle" 
                color="gray" 
                size="sm"
                component={Link}
                href="/settings"
                onClick={(e) => e.stopPropagation()}
              >
                <IconSettings size={14} />
              </ActionIcon>
            </Tooltip>
            
            <Tooltip label="Clear history">
              <ActionIcon 
                variant="subtle" 
                color="gray" 
                size="sm"
                onClick={(e) => { e.stopPropagation(); handleClear(); }}
              >
                <IconTrash size={14} />
              </ActionIcon>
            </Tooltip>
            
            <ActionIcon variant="subtle" color="gray" size="sm">
              {expanded ? <IconChevronDown size={16} /> : <IconChevronUp size={16} />}
            </ActionIcon>
          </Group>
        </Group>

        {/* Expanded Content */}
        <Collapse in={expanded}>
          {/* Messages */}
          <ScrollArea h={280} px="md" py="sm" viewportRef={scrollRef}>
            <Stack gap="sm">
              {messages.length === 0 ? (
                <Box ta="center" py="xl">
                  <IconTerminal size={32} style={{ opacity: 0.15, marginBottom: 8 }} />
                  <Text c="dimmed" size="sm">Your AI home manager</Text>
                  <Text c="dimmed" size="xs" mt={4}>Type <Kbd size="xs">/</Kbd> for commands or ask naturally</Text>
                </Box>
              ) : (
                messages.map((msg) => (
                  <Box
                    key={msg.id}
                    style={{
                      display: "flex",
                      justifyContent: msg.role === "user" ? "flex-end" : "flex-start",
                    }}
                  >
                    <Box style={{ maxWidth: "85%" }}>
                      {msg.routedTo && msg.role === "system" && !msg.isLoading && (
                        <Group gap={4} mb={4}>
                          <Text size="xs">{msg.agentEmoji}</Text>
                          <Text size="xs" c="dimmed" fw={500}>{msg.agentName}</Text>
                        </Group>
                      )}
                      <Paper
                        px="sm"
                        py="xs"
                        radius="lg"
                        style={{
                          background: msg.role === "user"
                            ? "linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)"
                            : msg.isError
                            ? "var(--mantine-color-red-9)"
                            : "var(--mantine-color-dark-6)",
                          borderBottomRightRadius: msg.role === "user" ? 4 : undefined,
                          borderBottomLeftRadius: msg.role === "system" ? 4 : undefined,
                        }}
                      >
                        {msg.isLoading ? (
                          <Group gap="xs">
                            <Loader size={12} color="gray" />
                            <Text size="sm" c="dimmed">Thinking...</Text>
                          </Group>
                        ) : msg.role === "user" ? (
                          <Text
                            size="sm"
                            style={{
                              color: "white",
                              whiteSpace: "pre-wrap",
                            }}
                          >
                            {msg.text}
                          </Text>
                        ) : (
                          <Box
                            className="chat-markdown"
                            style={{
                              fontFamily: msg.isCommand ? "var(--mantine-font-family-monospace)" : undefined,
                              fontSize: msg.isCommand ? "12px" : "0.875rem",
                              color: "var(--mantine-color-gray-2)",
                              lineHeight: 1.5,
                            }}
                          >
                            <ReactMarkdown
                              components={{
                                table: ({ children }) => (
                                  <Box style={{ overflowX: "auto", marginTop: 8, marginBottom: 8 }}>
                                    <table style={{ borderCollapse: "collapse", fontSize: "0.75rem", width: "100%" }}>
                                      {children}
                                    </table>
                                  </Box>
                                ),
                                th: ({ children }) => (
                                  <th style={{ borderBottom: "1px solid var(--mantine-color-dark-4)", padding: "4px 8px", textAlign: "left", fontWeight: 600, color: "var(--mantine-color-gray-4)" }}>
                                    {children}
                                  </th>
                                ),
                                td: ({ children }) => (
                                  <td style={{ borderBottom: "1px solid var(--mantine-color-dark-5)", padding: "4px 8px" }}>
                                    {children}
                                  </td>
                                ),
                                h1: ({ children }) => <Text fw={700} size="md" mb={4}>{children}</Text>,
                                h2: ({ children }) => <Text fw={600} size="sm" mb={4} mt={8}>{children}</Text>,
                                h3: ({ children }) => <Text fw={600} size="sm" mb={2} mt={6}>{children}</Text>,
                                ul: ({ children }) => <Box component="ul" style={{ margin: "4px 0", paddingLeft: 16 }}>{children}</Box>,
                                ol: ({ children }) => <Box component="ol" style={{ margin: "4px 0", paddingLeft: 16 }}>{children}</Box>,
                                li: ({ children }) => <li style={{ marginBottom: 2 }}>{children}</li>,
                                code: ({ children, className }) => {
                                  const isBlock = className?.includes("language-");
                                  return isBlock ? (
                                    <Box component="pre" style={{ background: "var(--mantine-color-dark-8)", padding: 8, borderRadius: 4, overflowX: "auto", fontSize: "0.75rem", margin: "8px 0" }}>
                                      <code>{children}</code>
                                    </Box>
                                  ) : (
                                    <code style={{ background: "var(--mantine-color-dark-5)", padding: "1px 4px", borderRadius: 3, fontSize: "0.8em" }}>
                                      {children}
                                    </code>
                                  );
                                },
                                strong: ({ children }) => <strong style={{ fontWeight: 600, color: "var(--mantine-color-gray-1)" }}>{children}</strong>,
                                p: ({ children }) => <Text size="sm" mb={4} style={{ color: "var(--mantine-color-gray-2)" }}>{children}</Text>,
                                hr: () => <Box style={{ borderTop: "1px solid var(--mantine-color-dark-4)", margin: "8px 0" }} />,
                              }}
                            >
                              {msg.text}
                            </ReactMarkdown>
                          </Box>
                        )}
                        {msg.exitCode !== undefined && (
                          <Badge size="xs" color={msg.exitCode === 0 ? "green" : "red"} mt={4}>
                            exit {msg.exitCode}
                          </Badge>
                        )}
                      </Paper>
                      <Text size="xs" c="dimmed" ta={msg.role === "user" ? "right" : "left"} mt={2} px={4}>
                        {formatTime(msg.timestamp)}
                      </Text>
                    </Box>
                  </Box>
                ))
              )}
            </Stack>
          </ScrollArea>

          {/* Command Suggestions */}
          <Collapse in={showCommands}>
            <Box
              px="md"
              py="xs"
              style={{
                background: "var(--mantine-color-dark-8)",
                borderTop: "1px solid var(--mantine-color-dark-5)",
                maxHeight: 150,
                overflowY: "auto",
              }}
            >
              {filteredCommands.map((cmd) => (
                <UnstyledButton
                  key={cmd.command}
                  onClick={() => handleCommandSelect(cmd.command)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    width: "100%",
                    padding: "6px 8px",
                    borderRadius: 6,
                    transition: "background 0.1s",
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = "var(--mantine-color-dark-6)"}
                  onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
                >
                  <Text size="sm">{cmd.emoji}</Text>
                  <Text size="sm" c="indigo.4" ff="monospace">{cmd.command}</Text>
                  <Text size="xs" c="dimmed" style={{ flex: 1 }}>{cmd.description}</Text>
                  <Badge size="xs" variant="light" color="gray">{cmd.agent}</Badge>
                </UnstyledButton>
              ))}
            </Box>
          </Collapse>
        </Collapse>

        {/* Input Area - Always Visible */}
        <Box
          px="md"
          py="sm"
          style={{
            borderTop: expanded ? "1px solid var(--mantine-color-dark-5)" : undefined,
            background: "var(--mantine-color-dark-8)",
          }}
        >
          <Group gap="xs">
            <Menu shadow="lg" position="top-start" width={260}>
              <Menu.Target>
                <ActionIcon variant="subtle" color="gray" size="lg" radius="xl">
                  <IconCommand size={18} />
                </ActionIcon>
              </Menu.Target>
              <Menu.Dropdown style={{ maxHeight: 400, overflowY: "auto" }}>
                <Menu.Label>💰 Finance</Menu.Label>
                <Menu.Item onClick={() => handleCommandSelect("/portfolio")}>📊 Portfolio</Menu.Item>
                <Menu.Item onClick={() => handleCommandSelect("/analyze")}>🔍 Analyze Positions</Menu.Item>
                <Menu.Item onClick={() => handleCommandSelect("/recommend")}>💡 Recommendations</Menu.Item>
                <Menu.Item onClick={() => handleCommandSelect("/project")}>📈 Projections</Menu.Item>
                <Menu.Item onClick={() => handleCommandSelect("/rebalance")}>⚖️ Rebalance</Menu.Item>
                <Menu.Item onClick={() => handleCommandSelect("/sectors")}>🏭 Sector Analysis</Menu.Item>
                <Menu.Item onClick={() => handleCommandSelect("/bills")}>💳 Bills</Menu.Item>
                <Menu.Divider />
                <Menu.Label>📬 Inbox</Menu.Label>
                <Menu.Item onClick={() => handleCommandSelect("/inbox")}>📥 All Messages</Menu.Item>
                <Menu.Item onClick={() => handleCommandSelect("/unread")}>🔵 Unread Only</Menu.Item>
                <Menu.Item onClick={() => handleCommandSelect("/markread")}>✅ Mark All Read</Menu.Item>
                <Menu.Item onClick={() => handleCommandSelect("/sync")}>🔄 Sync Now</Menu.Item>
                <Menu.Divider />
                <Menu.Label>🔧 Maintenance</Menu.Label>
                <Menu.Item onClick={() => handleCommandSelect("/tasks")}>📋 Tasks</Menu.Item>
                <Menu.Item onClick={() => handleCommandSelect("/schedule")}>🗓️ Schedule</Menu.Item>
                <Menu.Item onClick={() => handleCommandSelect("/readings")}>📉 Readings</Menu.Item>
                <Menu.Item onClick={() => handleCommandSelect("/overdue")}>⚠️ Overdue</Menu.Item>
                <Menu.Divider />
                <Menu.Label>👷 Contractors</Menu.Label>
                <Menu.Item onClick={() => handleCommandSelect("/contractors")}>📞 List All</Menu.Item>
                <Menu.Item onClick={() => handleCommandSelect("/hire")}>🔍 Find/Hire</Menu.Item>
                <Menu.Divider />
                <Menu.Label>📋 Projects</Menu.Label>
                <Menu.Item onClick={() => handleCommandSelect("/projects")}>🏗️ Active</Menu.Item>
                <Menu.Item onClick={() => handleCommandSelect("/milestones")}>🎯 Milestones</Menu.Item>
                <Menu.Item onClick={() => handleCommandSelect("/timeline")}>📅 Timeline</Menu.Item>
                <Menu.Divider />
                <Menu.Label>🧹 Janitor</Menu.Label>
                <Menu.Item onClick={() => handleCommandSelect("/health")}>💚 Health Check</Menu.Item>
                <Menu.Item onClick={() => handleCommandSelect("/logs")}>📜 Logs</Menu.Item>
                <Menu.Item onClick={() => handleCommandSelect("/cleanup")}>🗑️ Cleanup</Menu.Item>
                <Menu.Divider />
                <Menu.Label>🛡️ Security</Menu.Label>
                <Menu.Item onClick={() => handleCommandSelect("/security")}>🔒 Status</Menu.Item>
                <Menu.Item onClick={() => handleCommandSelect("/scan")}>🔎 Scan</Menu.Item>
                <Menu.Item onClick={() => handleCommandSelect("/threats")}>⚠️ Threats</Menu.Item>
                <Menu.Divider />
                <Menu.Label>⚡ System</Menu.Label>
                <Menu.Item onClick={() => handleCommandSelect("/status")}>🔍 Status</Menu.Item>
                <Menu.Item onClick={() => handleCommandSelect("/agents")}>🤖 Agents</Menu.Item>
                <Menu.Item onClick={() => handleCommandSelect("/launch")}>🚀 Launch All</Menu.Item>
              </Menu.Dropdown>
            </Menu>
            
            {/* @ Agent selector */}
            <Menu shadow="lg" position="top-start" width={200}>
              <Menu.Target>
                <Tooltip label="Talk to specific agent">
                  <ActionIcon variant="subtle" color={targetAgent ? targetAgent.color : "gray"} size="lg" radius="xl">
                    <IconAt size={18} />
                  </ActionIcon>
                </Tooltip>
              </Menu.Target>
              <Menu.Dropdown>
                <Menu.Label>Select Agent</Menu.Label>
                {AGENTS.map((agent) => (
                  <Menu.Item
                    key={agent.id}
                    leftSection={<Text size="sm">{agent.emoji}</Text>}
                    onClick={() => {
                      if (agent.id === "manager") {
                        clearAgent();
                        setInput("");
                      } else {
                        const mentionToken =
                          agent.id === "mail-skill" ? "mail" : agent.id === "backup-recovery" ? "backup" : agent.id;
                        selectAgent(agent.id, { greet: false });
                        setInput(`@${mentionToken} `);
                      }
                      inputRef.current?.focus();
                    }}
                    style={{
                      background: targetAgent?.id === agent.id ? "var(--mantine-color-dark-5)" : undefined,
                    }}
                  >
                    <Text size="sm">{agent.displayName}</Text>
                    <Text size="xs" c="dimmed">{agent.name}</Text>
                  </Menu.Item>
                ))}
              </Menu.Dropdown>
            </Menu>
            
            <TextInput
              ref={inputRef}
              placeholder={isLoading ? "Processing..." : targetAgent ? `Ask ${targetAgent.displayName}...` : "Ask anything or type / or @..."}
              value={input}
              onChange={(e) => setInput(e.currentTarget.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
                if (e.key === "Escape") {
                  setShowCommands(false);
                  setExpanded(false);
                }
              }}
              onFocus={() => setExpanded(true)}
              style={{ flex: 1 }}
              size="sm"
              radius="xl"
              disabled={isLoading}
              styles={{
                input: {
                  background: "var(--mantine-color-dark-6)",
                  border: targetAgent 
                    ? `1px solid var(--mantine-color-${targetAgent.color}-6)`
                    : "1px solid var(--mantine-color-dark-4)",
                  "&:focus": {
                    borderColor: targetAgent 
                      ? `var(--mantine-color-${targetAgent.color}-5)`
                      : "var(--mantine-color-indigo-6)",
                  },
                },
              }}
            />
            
            <ActionIcon 
              variant="gradient"
              gradient={{ from: "indigo", to: "violet", deg: 135 }}
              size="lg"
              radius="xl"
              onClick={handleSend} 
              disabled={!input.trim() || isLoading}
              loading={isLoading}
            >
              <IconSend size={16} />
            </ActionIcon>
          </Group>
        </Box>

        {/* Quick Actions Footer */}
        <Collapse in={expanded}>
          <Group 
            px="md" 
            py="xs" 
            gap="xs" 
            justify="center"
            style={{ 
              borderTop: "1px solid var(--mantine-color-dark-6)",
              background: "var(--mantine-color-dark-8)",
            }}
          >
            {["portfolio", "tasks", "bills", "contractors"].map((q) => (
              <Badge
                key={q}
                size="sm"
                variant="light"
                color="gray"
                style={{ cursor: "pointer" }}
                onClick={() => {
                  setInput(q);
                  inputRef.current?.focus();
                }}
              >
                {q}
              </Badge>
            ))}
          </Group>
        </Collapse>
      </Paper>
    </Box>
  );
}
