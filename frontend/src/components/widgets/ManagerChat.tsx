"use client";

import { useState, useEffect, useRef, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { getApiBaseUrl, isNetworkError, apiFetch } from "@/lib/api";
import {
  Paper,
  Stack,
  Text,
  ScrollArea,
  TextInput,
  ActionIcon,
  Group,
  Box,
  Badge,
  Collapse,
  Loader,
  Tooltip,
  Kbd,
  Menu,
  Divider,
  rem,
  UnstyledButton,
  TypographyStylesProvider,
} from "@mantine/core";
import {
  IconSend,
  IconChevronDown,
  IconChevronUp,
  IconTerminal2,
  IconX,
  IconRobot,
  IconCurrencyDollar,
  IconTool,
  IconUsers,
  IconHelp,
  IconCommand,
  IconBolt,
  IconSparkles,
  IconPaperclip,
  IconFile,
  IconPhoto,
} from "@tabler/icons-react";
import ReactMarkdown from "react-markdown";
import { sendManagerChat, getAgentChatHistory } from "@/lib/api";

// ============ TYPES ============
interface Message {
  id: string;
  role: "manager" | "user" | "system";
  text: string;
  timestamp: string;
  isCommand?: boolean;
  isStreaming?: boolean;
  exitCode?: number;
  agentName?: string;
  agentEmoji?: string;
  routedTo?: string;
  delegationNote?: string;
}

interface AgentCommand {
  command: string;
  description: string;
  agent: string;
  emoji: string;
}

// ============ AGENT COMMANDS ============
const AGENT_COMMANDS: AgentCommand[] = [
  // Finance Agent
  { command: "/bills", description: "View upcoming bills", agent: "Finance", emoji: "💰" },
  { command: "/portfolio", description: "Check investments", agent: "Finance", emoji: "💰" },
  { command: "/budget", description: "Budget overview", agent: "Finance", emoji: "💰" },
  { command: "/spending", description: "Monthly spending", agent: "Finance", emoji: "💰" },
  { command: "/alerts finance", description: "Financial alerts", agent: "Finance", emoji: "💰" },
  
  // Maintenance Agent  
  { command: "/tasks", description: "Maintenance tasks", agent: "Maintenance", emoji: "🔧" },
  { command: "/schedule", description: "Upcoming maintenance", agent: "Maintenance", emoji: "🔧" },
  { command: "/readings", description: "Home readings", agent: "Maintenance", emoji: "🔧" },
  { command: "/overdue", description: "Overdue items", agent: "Maintenance", emoji: "🔧" },
  
  // Contractors Agent
  { command: "/contractors", description: "List contractors", agent: "Contractors", emoji: "👷" },
  { command: "/reviews", description: "Contractor ratings", agent: "Contractors", emoji: "👷" },
  
  // System
  { command: "/status", description: "System status", agent: "System", emoji: "⚡" },
  { command: "/agents", description: "Active agents", agent: "System", emoji: "🤖" },
  { command: "/help", description: "All commands", agent: "System", emoji: "❓" },
];

// ============ CONSTANTS ============
const API_URL = getApiBaseUrl();
const STORAGE_KEY = "mycasa_chat_history_v3";
const CONVERSATION_KEY = "mycasa_manager_conversation_id";

const storageKey = (userId?: number | null) => `${STORAGE_KEY}:${userId ?? "anon"}`;
const conversationKey = (userId?: number | null) => `${CONVERSATION_KEY}:${userId ?? "anon"}`;

// ============ STORAGE HELPERS ============
function saveToStorage(key: string, messages: Message[]): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(key, JSON.stringify(messages.slice(-100)));
  } catch (e) {
    console.error("[Chat] Save failed:", e);
  }
}

function loadFromStorage(key: string): Message[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(key);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) return parsed;
    }
  } catch (e) {
    console.error("[Chat] Load failed:", e);
  }
  return [];
}

// ============ ATTACHMENT TYPE ============
interface PendingAttachment {
  id: string;
  file: File;
  name: string;
  type: string;
  size: number;
  preview?: string;
  uploading: boolean;
  uploaded: boolean;
  error?: string;
}

// ============ COMPONENT ============
export function ManagerChat() {
  const { isAuthenticated, user } = useAuth();
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [expanded, setExpanded] = useState(false);
  const [unread, setUnread] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [routingStatus, setRoutingStatus] = useState<string | null>(null);
  const [showCommands, setShowCommands] = useState(false);
  const [pendingAttachments, setPendingAttachments] = useState<PendingAttachment[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [historyStatus, setHistoryStatus] = useState<"idle" | "loading" | "error">("idle");
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [personalMode, setPersonalMode] = useState(false);
  
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const chatAllowed = isAuthenticated || personalMode;

  useEffect(() => {
    let active = true;
    const checkPersonalMode = async () => {
      try {
        const data = await apiFetch<any>("/api/system/status");
        if (active) setPersonalMode(Boolean(data.personal_mode));
      } catch {
        // ignore
      }
    };
    checkPersonalMode();
    return () => {
      active = false;
    };
  }, []);

  // Filter commands based on input
  const filteredCommands = useMemo(() => {
    if (!input.startsWith("/")) return [];
    const search = input.slice(1).toLowerCase();
    return AGENT_COMMANDS.filter(c => 
      c.command.slice(1).toLowerCase().includes(search) ||
      c.description.toLowerCase().includes(search)
    ).slice(0, 6);
  }, [input]);

  // Load/save persistence
  useEffect(() => {
    const key = storageKey(user?.id ?? null);
    const stored = loadFromStorage(key);
    setMessages(stored);
    setMounted(true);

    const convoKey = conversationKey(user?.id ?? null);
    const storedConversation = typeof window !== "undefined"
      ? window.localStorage.getItem(convoKey)
      : null;
    setConversationId(storedConversation || null);

    if (!chatAllowed) {
      setHistoryStatus("idle");
      setHistoryError(null);
      return;
    }

    setHistoryStatus("loading");
    setHistoryError(null);
    getAgentChatHistory("manager", storedConversation || undefined, 50)
      .then((data) => {
        if (data?.messages?.length) {
          const mapped = data.messages.map((msg: any) => ({
            id: msg.id,
            role: (msg.role === "assistant"
              ? "manager"
              : msg.role === "system"
                ? "system"
                : "user") as Message["role"],
            text: msg.content,
            timestamp: msg.timestamp,
          }));
          setMessages(mapped);
        }
        if (data?.conversation_id) {
          setConversationId(data.conversation_id);
          window.localStorage.setItem(convoKey, data.conversation_id);
        }
        setHistoryStatus("idle");
      })
      .catch((err) => {
        setHistoryStatus("error");
        if (isNetworkError(err)) {
          setHistoryError(`Unable to reach backend at ${API_URL}. Start the server and try again.`);
        } else if (err?.status === 401) {
          setHistoryError(personalMode ? "Session unavailable. Retry shortly." : "Sign in required to load history.");
        } else {
          setHistoryError(err?.detail || "Unable to load history");
        }
      });
  }, [chatAllowed, isAuthenticated, personalMode, user?.id]);

  useEffect(() => {
    if (mounted && messages.length > 0) {
      saveToStorage(storageKey(user?.id ?? null), messages);
    }
  }, [messages, mounted, user?.id]);

  // Auto-scroll
  useEffect(() => {
    if (scrollRef.current && expanded) {
      scrollRef.current.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
    }
  }, [messages, expanded]);

  // Focus on expand
  useEffect(() => {
    if (expanded) {
      setUnread(0);
      inputRef.current?.focus();
    }
  }, [expanded]);

  // Show command suggestions when typing /
  useEffect(() => {
    setShowCommands(input.startsWith("/") && filteredCommands.length > 0);
  }, [input, filteredCommands.length]);

  // Listen for messages from other pages (Finance, System, etc.)
  useEffect(() => {
    const handleExternalMessage = (event: CustomEvent<{ message: string; source: string }>) => {
      const { message } = event.detail;
      if (message && !isLoading) {
        // Expand the chat
        setExpanded(true);
        // Set the input and trigger send after a brief delay
        setInput(message);
        setTimeout(() => {
          // Trigger send programmatically
          const sendEvent = new CustomEvent("galidima-chat-execute");
          window.dispatchEvent(sendEvent);
        }, 100);
      }
    };

    window.addEventListener("galidima-chat-send" as any, handleExternalMessage);
    return () => window.removeEventListener("galidima-chat-send" as any, handleExternalMessage);
  }, [isLoading]);

  // Execute send when triggered externally
  useEffect(() => {
    const handleExecute = () => {
      if (input.trim() && !isLoading) {
        handleSendMessage(input.trim());
      }
    };

    window.addEventListener("galidima-chat-execute", handleExecute);
    return () => window.removeEventListener("galidima-chat-execute", handleExecute);
  }, [input, isLoading]);

  // Core message sending logic (extracted for reuse)
  const handleSendMessage = async (messageText: string) => {
    if (!messageText.trim() || isLoading) return;
    if (!chatAllowed) {
      const systemMsg: Message = {
        id: `sys_${Date.now()}`,
        role: "system",
        text: "Sign in is required on this server. Enable Personal Mode to chat without login.",
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, systemMsg]);
      router.push("/login");
      return;
    }
    const userMessage = messageText.trim();
    const isCommand = userMessage.startsWith("/");

    const userMsg: Message = {
      id: `user_${Date.now()}`,
      role: "user",
      text: userMessage,
      timestamp: new Date().toISOString(),
      isCommand,
    };

    const placeholderMsg: Message = {
      id: `resp_${Date.now()}`,
      role: "manager",
      text: "",
      timestamp: new Date().toISOString(),
      isStreaming: true,
      isCommand,
    };

    setMessages(prev => [...prev, userMsg, placeholderMsg]);
    setInput("");
    setShowCommands(false);
    setIsLoading(true);
    setRoutingStatus("Routing...");

    try {
      const data = await sendManagerChat(userMessage, conversationId || undefined);
      if (data?.conversation_id) {
        setConversationId(data.conversation_id);
        window.localStorage.setItem(conversationKey(user?.id ?? null), data.conversation_id);
      }

      if (data?.error) {
        const message = data.error;
        setMessages(prev => {
          const updated = [...prev];
          const lastIdx = updated.length - 1;
          if (updated[lastIdx]?.isStreaming) {
            updated[lastIdx] = {
              ...updated[lastIdx],
              text: `❌ ${message}`,
              isStreaming: false,
            };
          }
          return updated;
        });
        return;
      }

      if (data.routed_to) {
        const labels: Record<string, string> = {
          finance_agent: "💰 Finance",
          maintenance_agent: "🔧 Maintenance", 
          contractors_agent: "👷 Contractors",
          clawdbot_agent: "🤖 Clawdbot",
          clawdbot_cli: "⚡ CLI",
        };
        setRoutingStatus(labels[data.routed_to] || data.routed_to);
      }

      setMessages(prev => {
        const updated = [...prev];
        const lastIdx = updated.length - 1;
        if (updated[lastIdx]?.isStreaming) {
          updated[lastIdx] = {
            ...updated[lastIdx],
            text: data.response || "(no response)",
            isStreaming: false,
            exitCode: data.exit_code,
            agentName: data.agent_name,
            agentEmoji: data.agent_emoji,
            routedTo: data.routed_to,
            delegationNote: data.delegation_note,
          };
        }
        return updated;
      });
      if (data?.task_created) {
        window.dispatchEvent(new CustomEvent("mycasa-system-sync"));
        if (data?.routed_to === "maintenance") {
          try {
            router.push("/maintenance");
          } catch {
            // ignore navigation errors
          }
        }
      }
    } catch (e: any) {
      let message = e?.detail || e?.message || "Connection error";
      if (e?.status === 401) {
        message = personalMode ? "Session unavailable. Retry shortly." : "Session expired. Please sign in again.";
      } else if (isNetworkError(e)) {
        message = `Unable to reach backend at ${API_URL}. Start the server and try again.`;
      } else if (String(message).toLowerCase().includes("api key")) {
        message = "LLM provider is not configured. Go to Settings → General → LLM Provider and connect Qwen OAuth or add an API key.";
      }
      setMessages(prev => {
        const updated = [...prev];
        const lastIdx = updated.length - 1;
        if (updated[lastIdx]?.isStreaming) {
          updated[lastIdx] = {
            ...updated[lastIdx],
            text: `❌ ${message}`,
            isStreaming: false,
          };
        }
        return updated;
      });
    } finally {
      setIsLoading(false);
      setTimeout(() => setRoutingStatus(null), 1500);
    }
  };

  // ============ FILE ATTACHMENT HANDLERS ============
  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const attachment: PendingAttachment = {
        id: `pending_${Date.now()}_${i}`,
        file,
        name: file.name,
        type: file.type,
        size: file.size,
        uploading: true,
        uploaded: false,
      };

      // Generate preview for images
      if (file.type.startsWith("image/")) {
        const reader = new FileReader();
        reader.onload = (ev) => {
          setPendingAttachments(prev =>
            prev.map(a => a.id === attachment.id
              ? { ...a, preview: ev.target?.result as string }
              : a
            )
          );
        };
        reader.readAsDataURL(file);
      }

      setPendingAttachments(prev => [...prev, attachment]);

      // Upload file
      try {
        const formData = new FormData();
        formData.append("file", file);

        const res = await fetch(`${API_URL}/api/chat/upload`, {
          method: "POST",
          body: formData,
        });

        if (res.ok) {
          const data = await res.json();
          setPendingAttachments(prev =>
            prev.map(a => a.id === attachment.id
              ? { ...a, id: data.file_id, uploading: false, uploaded: true, preview: data.preview || a.preview }
              : a
            )
          );
        } else {
          setPendingAttachments(prev =>
            prev.map(a => a.id === attachment.id
              ? { ...a, uploading: false, error: "Upload failed" }
              : a
            )
          );
        }
      } catch {
        setPendingAttachments(prev =>
          prev.map(a => a.id === attachment.id
            ? { ...a, uploading: false, error: "Upload failed" }
            : a
          )
        );
      }
    }

    // Clear input
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const removeAttachment = (id: string) => {
    setPendingAttachments(prev => prev.filter(a => a.id !== id));
  };

  // Wrapper for direct sends from input
  const handleSend = () => {
    const hasContent = input.trim() || pendingAttachments.some(a => a.uploaded);
    if (hasContent) {
      // Build message with attachment info
      let messageText = input.trim();
      const uploadedAttachments = pendingAttachments.filter(a => a.uploaded && !a.error);
      
      if (uploadedAttachments.length > 0 && !messageText) {
        messageText = `[${uploadedAttachments.length} file(s) attached]`;
      }
      
      // TODO: Include attachment IDs in API call when backend supports it
      handleSendMessage(messageText);
      setPendingAttachments([]);
    }
  };

  const handleCommandSelect = (command: string) => {
    setInput(command + " ");
    setShowCommands(false);
    inputRef.current?.focus();
  };

  const handleClear = () => {
    setMessages([]);
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(storageKey(user?.id ?? null));
      window.localStorage.removeItem(conversationKey(user?.id ?? null));
    }
  };

  const formatTime = (ts: string) => {
    try {
      return new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } catch {
      return "";
    }
  };

  const getAgentColor = (routedTo?: string) => {
    switch (routedTo) {
      case "finance_agent": return "teal";
      case "maintenance_agent": return "orange";
      case "contractors_agent": return "yellow";
      case "clawdbot_cli": return "green";
      default: return "indigo";
    }
  };

  return (
    <Paper
      withBorder
      radius="lg"
      style={{
        position: "fixed",
        bottom: 16,
        left: "50%",
        transform: "translateX(-50%)",
        width: expanded ? "min(560px, 92vw)" : 56,
        zIndex: 1000,
        transition: "all 0.25s cubic-bezier(0.4, 0, 0.2, 1)",
        overflow: "hidden",
        boxShadow: expanded ? "var(--chat-panel-shadow)" : "var(--chat-lip-shadow)",
        background: "var(--chat-lip-bg)",
        border: "1px solid var(--chat-lip-border)",
      }}
    >
      {/* Compact Header (collapsed) */}
      {!expanded && (
        <Box
          p="sm"
          style={{ cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center" }}
          onClick={() => setExpanded(true)}
        >
          <Box style={{ position: "relative" }}>
            <IconSparkles size={24} style={{ color: "var(--mantine-color-indigo-5)" }} />
            {unread > 0 && (
              <Badge 
                size="xs" 
                color="red" 
                variant="filled" 
                style={{ position: "absolute", top: -6, right: -8, minWidth: 16 }}
              >
                {unread}
              </Badge>
            )}
          </Box>
        </Box>
      )}

      {/* Expanded View */}
      <Collapse in={expanded}>
        <Stack gap={0}>
          {/* Header */}
          <Group
            px="md"
            py="sm"
            justify="space-between"
            style={{
              background: "var(--surface-2)",
              borderBottom: "1px solid var(--border-1)",
            }}
          >
            <Group gap="xs">
              <IconSparkles size={18} style={{ color: "var(--color-primary)" }} />
              <Text fw={600} size="sm" style={{ color: "var(--text-primary)" }}>Galidima</Text>
              <Badge size="xs" variant="dot" color="green">Manager</Badge>
            </Group>
            <Group gap={4}>
              {routingStatus && (
                <Badge size="xs" variant="light" color="blue">
                  {routingStatus}
                </Badge>
              )}
              <ActionIcon 
                variant="subtle" 
                color="gray" 
                size="sm"
                onClick={() => setExpanded(false)}
              >
                <IconChevronDown size={16} />
              </ActionIcon>
            </Group>
          </Group>

          {/* Messages */}
          <ScrollArea h={320} px="md" py="sm" viewportRef={scrollRef}>
            <Stack gap="sm">
              {messages.length === 0 ? (
                <Box ta="center" py="xl">
                  {historyStatus === "loading" ? (
                    <Group gap="xs" justify="center">
                      <Loader size={16} color="gray" />
                      <Text c="dimmed" size="sm">Loading history…</Text>
                    </Group>
                  ) : historyStatus === "error" ? (
                    <>
                      <Text c="red" size="sm">Failed to load history</Text>
                      <Text c="dimmed" size="xs" mt={4}>{historyError}</Text>
                    </>
                  ) : (
                    <>
                      <IconRobot size={36} style={{ opacity: 0.2, marginBottom: 8 }} />
                      <Text c="dimmed" size="sm">Your home manager</Text>
                      <Text c="dimmed" size="xs" mt={4}>Type <Kbd size="xs">/</Kbd> for commands</Text>
                    </>
                  )}
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
                      {msg.routedTo && msg.role === "manager" && !msg.isStreaming && (
                        <Group gap={4} mb={4}>
                          <Text size="xs" c="dimmed">{msg.agentEmoji}</Text>
                          <Text size="xs" c="dimmed" fw={500}>{msg.agentName}</Text>
                        </Group>
                      )}
                      <Paper
                        px="sm"
                        py="xs"
                        radius="lg"
                        style={{
                          background: msg.role === "user"
                            ? "linear-gradient(135deg, var(--color-primary-light) 0%, var(--color-primary) 100%)"
                            : "var(--surface-2)",
                          border: msg.role === "user" ? "1px solid transparent" : "1px solid var(--border-1)",
                          borderBottomRightRadius: msg.role === "user" ? 4 : undefined,
                          borderBottomLeftRadius: msg.role === "manager" ? 4 : undefined,
                        }}
                      >
                        {msg.isStreaming ? (
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
                          <TypographyStylesProvider
                            style={{
                              color: "var(--text-primary)",
                              fontSize: "0.875rem",
                              lineHeight: 1.5,
                            }}
                          >
                            <Box
                              style={{
                                fontFamily: msg.isCommand ? "var(--mantine-font-family-monospace)" : undefined,
                                fontSize: msg.isCommand ? "12px" : undefined,
                              }}
                              className="chat-markdown"
                            >
                              <ReactMarkdown
                                components={{
                                  // Style tables for chat
                                  table: ({ children }) => (
                                    <Box style={{ overflowX: "auto", marginTop: 8, marginBottom: 8 }}>
                                      <table style={{ 
                                        borderCollapse: "collapse", 
                                        fontSize: "0.75rem",
                                        width: "100%",
                                      }}>
                                        {children}
                                      </table>
                                    </Box>
                                  ),
                                  th: ({ children }) => (
                                    <th style={{ 
                                      borderBottom: "1px solid var(--border-1)",
                                      padding: "4px 8px",
                                      textAlign: "left",
                                      fontWeight: 600,
                                      color: "var(--text-secondary)",
                                    }}>
                                      {children}
                                    </th>
                                  ),
                                  td: ({ children }) => (
                                    <td style={{ 
                                      borderBottom: "1px solid var(--border-1)",
                                      padding: "4px 8px",
                                    }}>
                                      {children}
                                    </td>
                                  ),
                                  // Style headers
                                  h1: ({ children }) => <Text fw={700} size="md" mb={4}>{children}</Text>,
                                  h2: ({ children }) => <Text fw={600} size="sm" mb={4} mt={8}>{children}</Text>,
                                  h3: ({ children }) => <Text fw={600} size="sm" mb={2} mt={6}>{children}</Text>,
                                  // Style lists
                                  ul: ({ children }) => <Box component="ul" style={{ margin: "4px 0", paddingLeft: 16 }}>{children}</Box>,
                                  ol: ({ children }) => <Box component="ol" style={{ margin: "4px 0", paddingLeft: 16 }}>{children}</Box>,
                                  li: ({ children }) => <li style={{ marginBottom: 2 }}>{children}</li>,
                                  // Style code
                                  code: ({ children, className }) => {
                                    const isBlock = className?.includes("language-");
                                    return isBlock ? (
                                      <Box
                                        component="pre"
                                        style={{
                                          background: "var(--surface-2)",
                                          border: "1px solid var(--border-1)",
                                          padding: 8,
                                          borderRadius: 4,
                                          overflowX: "auto",
                                          fontSize: "0.75rem",
                                          margin: "8px 0",
                                        }}
                                      >
                                        <code>{children}</code>
                                      </Box>
                                    ) : (
                                      <code style={{
                                        background: "var(--surface-2)",
                                        border: "1px solid var(--border-1)",
                                        padding: "1px 4px",
                                        borderRadius: 3,
                                        fontSize: "0.8em",
                                      }}>
                                        {children}
                                      </code>
                                    );
                                  },
                                  // Style strong/bold
                                  strong: ({ children }) => <strong style={{ fontWeight: 600, color: "var(--text-primary)" }}>{children}</strong>,
                                  // Style paragraphs
                                  p: ({ children }) => <Text size="sm" mb={4} style={{ color: "var(--text-primary)" }}>{children}</Text>,
                                  // Style horizontal rules
                                  hr: () => <Box style={{ borderTop: "1px solid var(--border-1)", margin: "8px 0" }} />,
                                }}
                              >
                                {msg.text}
                              </ReactMarkdown>
                            </Box>
                            {msg.delegationNote && (
                              <Text size="xs" c="dimmed" mt={6}>
                                {msg.delegationNote}
                              </Text>
                            )}
                          </TypographyStylesProvider>
                        )}
                      </Paper>
                      <Text 
                        size="xs" 
                        c="dimmed" 
                        ta={msg.role === "user" ? "right" : "left"} 
                        mt={2}
                        px={4}
                      >
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
                background: "var(--surface-2)",
                borderTop: "1px solid var(--border-1)",
                maxHeight: 180,
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
                  onMouseEnter={(e) => e.currentTarget.style.background = "var(--surface-1)"}
                  onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
                >
                  <Text size="sm">{cmd.emoji}</Text>
                  <Text size="sm" c="blue.6" ff="monospace">{cmd.command}</Text>
                  <Text size="xs" c="dimmed" style={{ flex: 1 }}>{cmd.description}</Text>
                  <Badge size="xs" variant="light" color="gray">{cmd.agent}</Badge>
                </UnstyledButton>
              ))}
            </Box>
          </Collapse>

          {/* Attachment Preview */}
          {pendingAttachments.length > 0 && (
            <Box
              p="xs"
              style={{
                borderTop: "1px solid var(--border-1)",
                background: "var(--surface-2)",
              }}
            >
              <Group gap="xs" wrap="wrap">
                {pendingAttachments.map((att) => (
                  <Paper
                    key={att.id}
                    p={6}
                    radius="md"
                    withBorder
                    style={{
                      position: "relative",
                      opacity: att.uploading ? 0.6 : 1,
                      background: "var(--surface-1)",
                      borderColor: att.error ? "var(--color-error)" : "var(--border-1)",
                    }}
                  >
                    <Group gap={6}>
                      {att.preview ? (
                        <img
                          src={att.preview}
                          alt={att.name}
                          style={{
                            width: 28,
                            height: 28,
                            borderRadius: 4,
                            objectFit: "cover",
                          }}
                        />
                      ) : (
                        <IconFile size={20} style={{ opacity: 0.7 }} />
                      )}
                      <Box>
                        <Text size="xs" fw={500} lineClamp={1} maw={80}>
                          {att.name}
                        </Text>
                        <Text size="xs" c="dimmed">
                          {att.uploading ? "..." : att.error || `${(att.size / 1024).toFixed(0)}KB`}
                        </Text>
                      </Box>
                      {!att.uploading && (
                        <ActionIcon
                          size="xs"
                          variant="subtle"
                          color="gray"
                          onClick={() => removeAttachment(att.id)}
                        >
                          <IconX size={12} />
                        </ActionIcon>
                      )}
                      {att.uploading && <Loader size="xs" />}
                    </Group>
                  </Paper>
                ))}
              </Group>
            </Box>
          )}

          {/* Hidden file input */}
          <input
            type="file"
            ref={fileInputRef}
            style={{ display: "none" }}
            multiple
            accept="image/*,.pdf,.doc,.docx,.txt,.md,.json,.csv,.py,.js,.ts,.yaml,.yml"
            onChange={handleFileSelect}
          />

          {/* Input Area */}
          <Box
            p="sm"
            style={{
              borderTop: pendingAttachments.length > 0 ? "none" : "1px solid var(--border-1)",
              background: "var(--surface-2)",
            }}
          >
            <Group gap="xs">
              <Menu shadow="lg" position="top-start" width={280}>
                <Menu.Target>
                  <ActionIcon 
                    variant="subtle" 
                    color="gray" 
                    size="lg"
                  >
                    <IconCommand size={18} />
                  </ActionIcon>
                </Menu.Target>
                <Menu.Dropdown>
                  <Menu.Label>💰 Finance</Menu.Label>
                  <Menu.Item leftSection={<Text size="xs">📊</Text>} onClick={() => handleCommandSelect("/portfolio")}>Portfolio</Menu.Item>
                  <Menu.Item leftSection={<Text size="xs">💳</Text>} onClick={() => handleCommandSelect("/bills")}>Bills</Menu.Item>
                  <Menu.Item leftSection={<Text size="xs">📈</Text>} onClick={() => handleCommandSelect("/budget")}>Budget</Menu.Item>
                  <Menu.Divider />
                  <Menu.Label>🔧 Maintenance</Menu.Label>
                  <Menu.Item leftSection={<Text size="xs">📋</Text>} onClick={() => handleCommandSelect("/tasks")}>Tasks</Menu.Item>
                  <Menu.Item leftSection={<Text size="xs">🗓️</Text>} onClick={() => handleCommandSelect("/schedule")}>Schedule</Menu.Item>
                  <Menu.Item leftSection={<Text size="xs">📉</Text>} onClick={() => handleCommandSelect("/readings")}>Readings</Menu.Item>
                  <Menu.Divider />
                  <Menu.Label>👷 Contractors</Menu.Label>
                  <Menu.Item leftSection={<Text size="xs">📞</Text>} onClick={() => handleCommandSelect("/contractors")}>List All</Menu.Item>
                  <Menu.Divider />
                  <Menu.Label>⚡ System</Menu.Label>
                  <Menu.Item leftSection={<Text size="xs">🔍</Text>} onClick={() => handleCommandSelect("/status")}>Status</Menu.Item>
                  <Menu.Item leftSection={<Text size="xs">🤖</Text>} onClick={() => handleCommandSelect("/agents")}>Agents</Menu.Item>
                </Menu.Dropdown>
              </Menu>

              {/* Attach button */}
              <Tooltip label="Attach file">
                <ActionIcon
                  variant="subtle"
                  color="gray"
                  size="lg"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isLoading || !chatAllowed}
                >
                  <IconPaperclip size={18} />
                </ActionIcon>
              </Tooltip>
              
              <TextInput
                ref={inputRef}
                placeholder={
                  !chatAllowed
                    ? "Sign in to send messages"
                    : isLoading
                      ? "Processing..."
                      : "Ask anything or type /..."
                }
                value={input}
                onChange={(e) => setInput(e.currentTarget.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                  if (e.key === "Escape") {
                    setShowCommands(false);
                  }
                }}
                style={{ flex: 1 }}
                size="sm"
                radius="xl"
                disabled={isLoading || !chatAllowed}
                styles={{
                  input: {
                    background: "var(--surface-1)",
                    border: "1px solid var(--border-1)",
                    color: "var(--text-primary)",
                    "&:focus": {
                      borderColor: "var(--color-primary)",
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
                disabled={(!input.trim() && !pendingAttachments.some(a => a.uploaded)) || isLoading || !chatAllowed}
                loading={isLoading}
              >
                <IconSend size={16} />
              </ActionIcon>
              
              {messages.length > 0 && (
                <Tooltip label="Clear">
                  <ActionIcon variant="subtle" color="gray" size="lg" onClick={handleClear}>
                    <IconX size={16} />
                  </ActionIcon>
                </Tooltip>
              )}
            </Group>
          </Box>

          {/* Quick Actions Footer */}
          <Group 
            px="md" 
            py="xs" 
            gap="xs" 
            justify="center"
            style={{ 
              borderTop: "1px solid var(--border-1)",
              background: "var(--surface-2)",
            }}
          >
            {["portfolio", "tasks", "bills"].map((q) => (
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
            <Text size="xs" c="dimmed">•</Text>
            <Text size="xs" c="dimmed">
              <Kbd size="xs" px={4}>/</Kbd> commands
            </Text>
          </Group>
        </Stack>
      </Collapse>
    </Paper>
  );
}
