"use client";

import { useState, useEffect, useCallback } from "react";
import { Shell } from "@/components/layout/Shell";
import {
  getApiBaseUrl,
  sendAgentChat,
  getAgentChatHistory,
  getAgentConversations,
  createAgentConversation,
  renameAgentConversation,
  archiveAgentConversation,
  restoreAgentConversation,
  deleteAgentConversation,
  apiFetch,
  isNetworkError,
} from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { Page } from "@/components/layout/Page";
import {
  Container,
  Title,
  Text,
  Tabs,
  Card,
  Stack,
  Group,
  Button,
  Badge,
  Alert,
  SimpleGrid,
  ThemeIcon,
  Box,
  Loader,
  ScrollArea,
  Tooltip,
  Paper,
  Divider,
  Progress,
  Table,
  ActionIcon,
  Modal,
  Textarea,
  TextInput,
  Code,
  Timeline,
  RingProgress,
  Center,
  Switch,
} from "@mantine/core";
import {
  IconSparkles,
  IconRefresh,
  IconAlertTriangle,
  IconCheck,
  IconX,
  IconTrash,
  IconPlus,
  IconArchive,
  IconEdit,
  IconShieldCheck,
  IconFileCode,
  IconHistory,
  IconServer,
  IconHeart,
  IconActivity,
  IconCloudDownload,
  IconMessageCircle,
  IconSend,
  IconWand,
  IconBulb,
  IconRocket,
} from "@tabler/icons-react";
import { notifications } from "@mantine/notifications";

const API_URL = getApiBaseUrl();

const cleanError = (message?: string | null) => {
  if (!message) return "";
  return message.replace(/^LLM_ERROR:\s*/i, "").trim();
};

interface AuditResult {
  timestamp: string;
  status: string;
  health_score: number;
  checks_passed: number;
  checks_total: number;
  findings: Array<{
    severity: string;
    domain: string;
    finding: string;
  }>;
}

interface JanitorStatus {
  agent: {
    id: string;
    name: string;
    emoji: string;
    status: string;
    description: string;
  };
  metrics: {
    last_audit: string;
    last_preflight?: string;
    last_preflight_status?: string;
    findings_count: number;
    recent_edits: number;
    system_health: string;
  };
  uptime_seconds: number;
}

interface EditHistoryItem {
  timestamp: string;
  file: string;
  agent: string;
  success: boolean;
  reason?: string;
}

interface BackupFile {
  filename: string;
  size_bytes: number;
  modified: string;
  path: string;
}

interface LogEntry {
  timestamp: string;
  action: string;
  details: string;
  status: string;
  agent_id: string;
}

interface ReviewConcern {
  severity: string;
  issue: string;
}

interface ConversationSummary {
  id: string;
  title?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  archived_at?: string | null;
  message_count?: number;
  last_message?: string | null;
}

interface ReviewResult {
  approved: boolean;
  concerns: ReviewConcern[];
  blocker_count: number;
  warning_count: number;
  reviewed_at: string;
  reviewed_by: string;
}

interface WizardSection {
  id: string;
  title: string;
  status: "ok" | "warning" | "error";
  summary: string;
  findings?: Array<{
    severity: string;
    domain: string;
    finding: string;
  }>;
  details?: Record<string, any>;
}

interface WizardRecommendation {
  id: string;
  severity: string;
  title: string;
  description: string;
  action: string;
  params?: Record<string, any>;
  can_auto_fix: boolean;
}

interface WizardResult {
  timestamp: string;
  summary: {
    health_score: number;
    status: string;
    checks_passed: number;
    checks_total: number;
    findings_count: number;
  };
  sections: WizardSection[];
  recommendations: WizardRecommendation[];
}

interface WizardHistoryItem {
  id: number;
  timestamp: string;
  health_score: number;
  status: string;
  findings_count: number;
  checks_passed: number;
  checks_total: number;
}

interface PreflightInfo {
  script_path: string;
  command: string;
  command_destructive?: string;
  command_use_existing?: string;
  notes?: string;
}

export default function JanitorPage() {
  // State
  const { user } = useAuth();
  const [status, setStatus] = useState<JanitorStatus | null>(null);
  const [audit, setAudit] = useState<AuditResult | null>(null);
  const [editHistory, setEditHistory] = useState<EditHistoryItem[]>([]);
  const [backups, setBackups] = useState<BackupFile[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [auditRunning, setAuditRunning] = useState(false);
  const [cleanupRunning, setCleanupRunning] = useState(false);
  const [wizardResult, setWizardResult] = useState<WizardResult | null>(null);
  const [wizardLoading, setWizardLoading] = useState(false);
  const [wizardError, setWizardError] = useState<string | null>(null);
  const [wizardFixing, setWizardFixing] = useState<string | null>(null);
  const [wizardHistory, setWizardHistory] = useState<WizardHistoryItem[]>([]);
  const [wizardHistoryLoading, setWizardHistoryLoading] = useState(false);
  const [preflightInfo, setPreflightInfo] = useState<PreflightInfo | null>(null);
  const [preflightRunning, setPreflightRunning] = useState(false);
  const [preflightResult, setPreflightResult] = useState<any>(null);
  const [preflightIsolated, setPreflightIsolated] = useState(true);
  const [preflightIncludeOauth, setPreflightIncludeOauth] = useState(false);
  const [preflightAllowDestructive, setPreflightAllowDestructive] = useState(false);

  // Chat state
  const [chatMessage, setChatMessage] = useState("");
  const [chatHistory, setChatHistory] = useState<Array<{ role: string; content: string; timestamp?: string }>>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatSessions, setChatSessions] = useState<ConversationSummary[]>([]);
  const [chatSessionsLoading, setChatSessionsLoading] = useState(false);
  const [chatSessionsError, setChatSessionsError] = useState<string | null>(null);
  const [chatShowArchived, setChatShowArchived] = useState(false);
  const [chatConversationId, setChatConversationId] = useState<string | null>(null);
  const [chatHistoryStatus, setChatHistoryStatus] = useState<"idle" | "loading" | "error">("idle");
  const [chatHistoryError, setChatHistoryError] = useState<string | null>(null);

  // Code review modal
  const [reviewModalOpen, setReviewModalOpen] = useState(false);
  const [reviewFilePath, setReviewFilePath] = useState("");
  const [reviewContent, setReviewContent] = useState("");
  const [reviewResult, setReviewResult] = useState<ReviewResult | null>(null);
  const [reviewLoading, setReviewLoading] = useState(false);

  // Fetch functions
  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/janitor/status`);
      if (res.ok) {
        const data = await res.json();
        setStatus(data);
      }
    } catch (e) {
      console.error("Failed to fetch janitor status:", e);
    }
  }, []);

  const fetchEditHistory = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/janitor/history?limit=20`);
      if (res.ok) {
        const data = await res.json();
        setEditHistory(data.edits || []);
      }
    } catch (e) {
      console.error("Failed to fetch edit history:", e);
    }
  }, []);

  const fetchBackups = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/janitor/backups?limit=30`);
      if (res.ok) {
        const data = await res.json();
        setBackups(data.backups || []);
      }
    } catch (e) {
      console.error("Failed to fetch backups:", e);
    }
  }, []);

  const chatStorageKey = useCallback((userId?: number | null) => {
    return `mycasa_janitor_conversation:${userId ?? "guest"}`;
  }, []);

  const refreshChatSessions = useCallback(async (includeArchived = chatShowArchived) => {
    setChatSessionsLoading(true);
    setChatSessionsError(null);
    try {
      const data = await getAgentConversations("janitor", 12, includeArchived);
      setChatSessions(data?.conversations || []);
    } catch (err: any) {
      setChatSessionsError(err?.detail || "Unable to load sessions");
    } finally {
      setChatSessionsLoading(false);
    }
  }, [chatShowArchived]);

  const loadChatHistory = useCallback(async (conversationId?: string | null) => {
    if (!conversationId) {
      setChatHistory([]);
      setChatHistoryStatus("idle");
      return;
    }
    setChatHistoryStatus("loading");
    setChatHistoryError(null);
    try {
      const data = await getAgentChatHistory("janitor", conversationId, 50);
      const mapped = (data?.messages || []).map((msg: any) => ({
        role: msg.role === "assistant" ? "assistant" : "user",
        content: msg.content,
        timestamp: msg.timestamp,
      }));
      setChatHistory(mapped);
      setChatHistoryStatus("idle");
      if (data?.conversation_id) {
        setChatConversationId(data.conversation_id);
        if (typeof window !== "undefined") {
          localStorage.setItem(chatStorageKey(user?.id ?? null), data.conversation_id);
        }
      }
    } catch (err: any) {
      if (err?.status === 404) {
        setChatHistory([]);
        setChatHistoryStatus("idle");
        setChatHistoryError(null);
        if (typeof window !== "undefined") {
          localStorage.removeItem(chatStorageKey(user?.id ?? null));
        }
        return;
      }
      setChatHistoryStatus("error");
      setChatHistoryError(err?.detail || "Unable to load history");
    }
  }, [chatStorageKey, user?.id]);

  const fetchLogs = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/janitor/logs?limit=30`);
      if (res.ok) {
        const data = await res.json();
        setLogs(data.logs || []);
      }
    } catch (e) {
      console.error("Failed to fetch logs:", e);
    }
  }, []);

  const fetchWizardHistory = useCallback(async () => {
    setWizardHistoryLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/janitor/wizard/history?limit=10`);
      if (res.ok) {
        const data = await res.json();
        setWizardHistory(data.runs || []);
      }
    } catch (e) {
      console.error("Failed to fetch wizard history:", e);
    } finally {
      setWizardHistoryLoading(false);
    }
  }, []);

  const fetchPreflightInfo = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/janitor/preflight-info`);
      if (res.ok) {
        const data = await res.json();
        setPreflightInfo(data);
      }
    } catch (e) {
      console.error("Failed to fetch preflight info:", e);
    }
  }, []);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    await Promise.all([
      fetchStatus(),
      fetchEditHistory(),
      fetchBackups(),
      fetchLogs(),
      fetchWizardHistory(),
      fetchPreflightInfo(),
    ]);
    setLoading(false);
  }, [fetchStatus, fetchEditHistory, fetchBackups, fetchLogs, fetchWizardHistory, fetchPreflightInfo]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  useEffect(() => {
    let active = true;
    const initChat = async () => {
      await refreshChatSessions(chatShowArchived);
      if (!active) return;
      let storedId: string | null = null;
      if (typeof window !== "undefined") {
        storedId = localStorage.getItem(chatStorageKey(user?.id ?? null));
      }
      if (!storedId) {
        try {
          const created = await createAgentConversation("janitor");
          storedId = created?.conversation_id || null;
          if (storedId && typeof window !== "undefined") {
            localStorage.setItem(chatStorageKey(user?.id ?? null), storedId);
          }
        } catch {
          storedId = null;
        }
      }
      if (!active) return;
      setChatConversationId(storedId);
      await loadChatHistory(storedId);
    };
    initChat();
    return () => {
      active = false;
    };
  }, [chatShowArchived, chatStorageKey, loadChatHistory, refreshChatSessions, user?.id]);

  useEffect(() => {
    if (chatSessionsLoading) return;
    if (chatShowArchived) return;
    if (!chatConversationId) return;
    if (!chatSessions.find((session) => session.id === chatConversationId)) {
      handleNewChatSession();
    }
  }, [chatSessions, chatSessionsLoading, chatShowArchived, chatConversationId]);

  // Actions
  const runAudit = async () => {
    setAuditRunning(true);
    try {
      const res = await fetch(`${API_URL}/api/janitor/audit`);
      if (res.ok) {
        const data = await res.json();
        setAudit(data);
        notifications.show({
          title: "Audit Complete",
          message: `Health Score: ${data.health_score}% - ${data.findings.length} findings`,
          color: data.health_score >= 80 ? "green" : data.health_score >= 50 ? "yellow" : "red",
          icon: <IconShieldCheck size={16} />,
        });
        fetchStatus();
      } else {
        throw new Error("Audit failed");
      }
    } catch (e: unknown) {
      notifications.show({
        title: "Audit Failed",
        message: e instanceof Error ? e.message : "Could not run audit",
        color: "red",
      });
    } finally {
      setAuditRunning(false);
    }
  };

  const runCleanup = async (days: number = 7) => {
    setCleanupRunning(true);
    try {
      const res = await fetch(`${API_URL}/api/janitor/cleanup?days_to_keep=${days}`, {
        method: "POST",
      });
      if (res.ok) {
        const data = await res.json();
        notifications.show({
          title: "Cleanup Complete",
          message: `Deleted ${data.deleted} old backups, kept ${data.kept}`,
          color: "green",
          icon: <IconTrash size={16} />,
        });
        fetchBackups();
      } else {
        throw new Error("Cleanup failed");
      }
    } catch (e: unknown) {
      notifications.show({
        title: "Cleanup Failed",
        message: e instanceof Error ? e.message : "Could not run cleanup",
        color: "red",
      });
    } finally {
      setCleanupRunning(false);
    }
  };

  const runWizard = async () => {
    setWizardLoading(true);
    setWizardError(null);
    try {
      const res = await fetch(`${API_URL}/api/janitor/wizard`, { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        setWizardResult(data);
        fetchWizardHistory();
        notifications.show({
          title: "Audit Wizard Complete",
          message: `${data.summary.health_score}% health • ${data.recommendations.length} recommendations`,
          color: data.summary.health_score >= 80 ? "green" : data.summary.health_score >= 50 ? "yellow" : "red",
          icon: <IconWand size={16} />,
        });
      } else {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.detail || "Wizard failed");
      }
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Could not run audit wizard";
      setWizardError(message);
      notifications.show({
        title: "Wizard Failed",
        message,
        color: "red",
      });
    } finally {
      setWizardLoading(false);
    }
  };

  const applyWizardFix = async (fixId: string, action: string, params: Record<string, any> = {}) => {
    setWizardFixing(fixId);
    try {
      const res = await fetch(`${API_URL}/api/janitor/wizard/fix`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, params }),
      });
      if (res.ok) {
        const data = await res.json();
        notifications.show({
          title: "Fix applied",
          message: `Action: ${data.action}`,
          color: "green",
        });
      } else {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.detail || "Fix failed");
      }
      await runWizard();
    } catch (e: unknown) {
      notifications.show({
        title: "Fix failed",
        message: e instanceof Error ? e.message : "Could not apply fix",
        color: "red",
      });
    } finally {
      setWizardFixing(null);
    }
  };

  const runPreflight = async () => {
    setPreflightRunning(true);
    try {
      const payload = {
        api_base: preflightIsolated ? undefined : API_URL,
        skip_oauth: !preflightIncludeOauth,
        open_browser: preflightIncludeOauth,
        allow_destructive: preflightAllowDestructive,
        isolated: preflightIsolated,
      };
      const res = await fetch(`${API_URL}/api/janitor/run-preflight`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        const data = await res.json();
        setPreflightResult(data);
        notifications.show({
          title: "Preflight Complete",
          message: data?.result?.status === "pass" ? "All checks passed." : "Preflight reported issues.",
          color: data?.result?.status === "pass" ? "green" : "yellow",
          icon: <IconRocket size={16} />,
        });
        fetchStatus();
        fetchWizardHistory();
      } else {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.detail || "Preflight failed");
      }
    } catch (e: unknown) {
      notifications.show({
        title: "Preflight Failed",
        message: e instanceof Error ? e.message : "Could not run preflight",
        color: "red",
      });
    } finally {
      setPreflightRunning(false);
    }
  };

  const deleteBackup = async (filename: string) => {
    try {
      const res = await fetch(`${API_URL}/api/janitor/backups/${filename}`, {
        method: "DELETE",
      });
      if (res.ok) {
        notifications.show({
          title: "Backup Deleted",
          message: filename,
          color: "green",
        });
        fetchBackups();
      } else {
        throw new Error("Delete failed");
      }
    } catch (e: unknown) {
      notifications.show({
        title: "Delete Failed",
        message: e instanceof Error ? e.message : "Unknown error",
        color: "red",
      });
    }
  };

  const runCodeReview = async () => {
    if (!reviewFilePath.trim() || !reviewContent.trim()) {
      notifications.show({
        title: "Missing Input",
        message: "Please provide both file path and content",
        color: "orange",
      });
      return;
    }

    setReviewLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/janitor/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          file_path: reviewFilePath,
          new_content: reviewContent,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setReviewResult(data);
      } else {
        const err = await res.json();
        throw new Error(err.detail || "Review failed");
      }
    } catch (e: unknown) {
      notifications.show({
        title: "Review Failed",
        message: e instanceof Error ? e.message : "Unknown error",
        color: "red",
      });
    } finally {
      setReviewLoading(false);
    }
  };

  const sendChatMessage = async () => {
    if (!chatMessage.trim()) return;

    const userMsg = chatMessage;
    setChatHistory((prev) => [...prev, { role: "user", content: userMsg }]);
    setChatMessage("");
    setChatLoading(true);

    try {
      let activeId = chatConversationId;
      if (!activeId) {
        const created = await createAgentConversation("janitor");
        activeId = created?.conversation_id || null;
        if (activeId) {
          setChatConversationId(activeId);
          if (typeof window !== "undefined") {
            localStorage.setItem(chatStorageKey(user?.id ?? null), activeId);
          }
          await refreshChatSessions(chatShowArchived);
        }
      }
      const data = await sendAgentChat("janitor", userMsg, activeId || undefined);
      if (data?.conversation_id && data.conversation_id !== activeId) {
        setChatConversationId(data.conversation_id);
        if (typeof window !== "undefined") {
          localStorage.setItem(chatStorageKey(user?.id ?? null), data.conversation_id);
        }
        await refreshChatSessions(chatShowArchived);
      }
      if (data?.error) {
        setChatHistory((prev) => [
          ...prev,
          { role: "error", content: cleanError(data.error) || data.error },
        ]);
        return;
      }
      const responseText = data?.response?.trim();
      if (responseText) {
        setChatHistory((prev) => [
          ...prev,
          { role: "assistant", content: responseText, timestamp: data?.timestamp },
        ]);
      } else {
        setChatHistory((prev) => [
          ...prev,
          { role: "error", content: "No response received from Janitor." },
        ]);
      }
    } catch (err: any) {
      const detail = err?.detail || err?.message;
      setChatHistory((prev) => [
        ...prev,
        {
          role: "error",
          content: isNetworkError(err)
            ? `Backend unavailable at ${API_URL}. Start the API and retry.`
            : detail || "Failed to reach Janitor.",
        },
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  const handleNewChatSession = async () => {
    try {
      const created = await createAgentConversation("janitor");
      const id = created?.conversation_id || null;
      if (id && typeof window !== "undefined") {
        localStorage.setItem(chatStorageKey(user?.id ?? null), id);
      }
      setChatConversationId(id);
      setChatHistory([]);
      await refreshChatSessions(chatShowArchived);
      if (id) {
        await loadChatHistory(id);
      }
    } catch {
      // ignore
    }
  };

  const handleSelectChatSession = async (sessionId: string) => {
    if (!sessionId) return;
    setChatConversationId(sessionId);
    if (typeof window !== "undefined") {
      localStorage.setItem(chatStorageKey(user?.id ?? null), sessionId);
    }
    await loadChatHistory(sessionId);
  };

  const handleDeleteChatSession = async (sessionId: string) => {
    if (!sessionId) return;
    try {
      await deleteAgentConversation("janitor", sessionId);
      await refreshChatSessions(chatShowArchived);
      if (chatConversationId === sessionId) {
        setChatConversationId(null);
        if (typeof window !== "undefined") {
          localStorage.removeItem(chatStorageKey(user?.id ?? null));
        }
        setChatHistory([]);
      }
    } catch {
      // ignore
    }
  };

  const handleArchiveChatSession = async (sessionId: string) => {
    if (!sessionId) return;
    try {
      await archiveAgentConversation("janitor", sessionId);
      await refreshChatSessions(chatShowArchived);
      if (chatConversationId === sessionId) {
        await handleNewChatSession();
      }
    } catch {
      // ignore
    }
  };

  const handleRestoreChatSession = async (sessionId: string) => {
    if (!sessionId) return;
    try {
      await restoreAgentConversation("janitor", sessionId);
      await refreshChatSessions(chatShowArchived);
    } catch {
      // ignore
    }
  };

  const handleRenameChatSession = async (sessionId: string, currentTitle?: string | null) => {
    const nextTitle = prompt("Rename session", currentTitle || "");
    if (nextTitle === null) return;
    try {
      await renameAgentConversation("janitor", sessionId, nextTitle.trim() || null);
      await refreshChatSessions(chatShowArchived);
    } catch {
      // ignore
    }
  };

  // Helpers
  const formatBytes = (bytes: number) => {
    if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${bytes} B`;
  };

  const getHealthColor = (score: number) => {
    if (score >= 80) return "green";
    if (score >= 50) return "yellow";
    return "red";
  };

  const getSeverityColor = (severity: string) => {
    if (severity === "P1" || severity === "blocker") return "red";
    if (severity === "P2" || severity === "warning") return "yellow";
    return "green";
  };

  const getStatusColor = (status: string) => {
    if (status === "success") return "green";
    if (status === "warning") return "yellow";
    return "red";
  };

  const getWizardStatusColor = (status: string) => {
    if (status === "ok") return "green";
    if (status === "warning") return "yellow";
    return "red";
  };

  return (
    <Shell>
      <Page title="Janitor" subtitle="System cleanup & audits">
      {/* Code Review Modal */}
      <Modal
        opened={reviewModalOpen}
        onClose={() => {
          setReviewModalOpen(false);
          setReviewResult(null);
        }}
        title={
          <Group gap="xs">
            <ThemeIcon size="sm" variant="light" color="violet">
              <IconFileCode size={14} />
            </ThemeIcon>
            <Text fw={600}>Code Review</Text>
          </Group>
        }
        size="xl"
      >
        <Stack gap="md">
          <TextInput
            label="File Path"
            placeholder="/path/to/file.py"
            value={reviewFilePath}
            onChange={(e) => setReviewFilePath(e.target.value)}
          />
          <Textarea
            label="New Content"
            placeholder="Paste the proposed file content here..."
            minRows={10}
            maxRows={20}
            value={reviewContent}
            onChange={(e) => setReviewContent(e.target.value)}
            styles={{ input: { fontFamily: "monospace", fontSize: "12px" } }}
          />

          {reviewResult && (
            <Alert
              color={reviewResult.approved ? "green" : "red"}
              icon={reviewResult.approved ? <IconCheck size={16} /> : <IconX size={16} />}
              title={reviewResult.approved ? "Approved" : "Blocked"}
            >
              <Stack gap="xs">
                <Text size="sm">
                  {reviewResult.blocker_count} blockers, {reviewResult.warning_count} warnings
                </Text>
                {reviewResult.concerns?.length > 0 && (
                  <Stack gap="xs" mt="sm">
                    {reviewResult.concerns.map((c: ReviewConcern, i: number) => (
                      <Group key={i} gap="xs">
                        <Badge color={getSeverityColor(c.severity)} size="xs">
                          {c.severity}
                        </Badge>
                        <Text size="xs">{c.issue}</Text>
                      </Group>
                    ))}
                  </Stack>
                )}
              </Stack>
            </Alert>
          )}

          <Group justify="flex-end">
            <Button variant="default" onClick={() => setReviewModalOpen(false)}>
              Close
            </Button>
            <Button
              onClick={runCodeReview}
              loading={reviewLoading}
              leftSection={<IconShieldCheck size={16} />}
            >
              Review Code
            </Button>
          </Group>
        </Stack>
      </Modal>

      <Container size="xl" py="md" className="janitor-page">
        <Group justify="space-between" mb="xs">
          <Group gap="sm">
            <ThemeIcon size="lg" variant="light" color="violet">
              <IconSparkles size={20} />
            </ThemeIcon>
            <div>
              <Text fw={600}>Janitor</Text>
              <Text c="dimmed" size="sm">
                Janitor — system health, audits, and safe edits
              </Text>
            </div>
          </Group>
          <Group gap="xs">
            <Tooltip label="Refresh all">
              <ActionIcon variant="light" onClick={fetchAll} loading={loading}>
                <IconRefresh size={18} />
              </ActionIcon>
            </Tooltip>
          </Group>
        </Group>

        <Tabs defaultValue="overview" className="janitor-tabs">
          <Tabs.List mb="md" className="janitor-tabs-list">
            <Tabs.Tab value="overview" leftSection={<IconHeart size={16} />}>
              Overview
            </Tabs.Tab>
            <Tabs.Tab value="wizard" leftSection={<IconWand size={16} />}>
              Wizard
            </Tabs.Tab>
            <Tabs.Tab value="audit" leftSection={<IconShieldCheck size={16} />}>
              Audit
            </Tabs.Tab>
            <Tabs.Tab value="history" leftSection={<IconHistory size={16} />}>
              Edit History
            </Tabs.Tab>
            <Tabs.Tab value="backups" leftSection={<IconCloudDownload size={16} />}>
              Backups
            </Tabs.Tab>
            <Tabs.Tab value="logs" leftSection={<IconActivity size={16} />}>
              Activity Logs
            </Tabs.Tab>
            <Tabs.Tab value="chat" leftSection={<IconMessageCircle size={16} />}>
              Chat
            </Tabs.Tab>
          </Tabs.List>

          {/* Overview Tab */}
          <Tabs.Panel value="overview">
            <Stack gap="md">
              {/* Status Cards */}
              <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} className="janitor-stats">
                <Card withBorder p="lg" radius="md">
                  <Group justify="space-between">
                    <div>
                      <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
                        Agent Status
                      </Text>
                      <Text size="xl" fw={700} c={status?.agent.status === "running" ? "green" : "gray"}>
                        {loading ? <Loader size="sm" /> : status?.agent.status || "Unknown"}
                      </Text>
                    </div>
                    <ThemeIcon size="xl" variant="light" color="violet">
                      <IconServer size={24} />
                    </ThemeIcon>
                  </Group>
                </Card>

                <Card withBorder p="lg" radius="md">
                  <Group justify="space-between">
                    <div>
                      <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
                        System Health
                      </Text>
                      <Text
                        size="xl"
                        fw={700}
                        c={
                          status?.metrics.system_health === "healthy"
                            ? "green"
                            : status?.metrics.system_health === "needs_attention"
                            ? "yellow"
                            : "gray"
                        }
                      >
                        {loading ? <Loader size="sm" /> : status?.metrics.system_health || "Unknown"}
                      </Text>
                    </div>
                    <ThemeIcon size="xl" variant="light" color="green">
                      <IconHeart size={24} />
                    </ThemeIcon>
                  </Group>
                </Card>

                <Card withBorder p="lg" radius="md">
                  <Group justify="space-between">
                    <div>
                      <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
                        Findings
                      </Text>
                      <Text
                        size="xl"
                        fw={700}
                        c={
                          status?.metrics.findings_count === 0
                            ? "green"
                            : (status?.metrics.findings_count ?? 0) > 3
                            ? "red"
                            : "yellow"
                        }
                      >
                        {loading ? <Loader size="sm" /> : status?.metrics.findings_count ?? 0}
                      </Text>
                    </div>
                    <ThemeIcon size="xl" variant="light" color="orange">
                      <IconAlertTriangle size={24} />
                    </ThemeIcon>
                  </Group>
                </Card>

                <Card withBorder p="lg" radius="md">
                  <Group justify="space-between">
                    <div>
                      <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
                        Recent Edits
                      </Text>
                      <Text size="xl" fw={700}>
                        {loading ? <Loader size="sm" /> : status?.metrics.recent_edits ?? 0}
                      </Text>
                    </div>
                    <ThemeIcon size="xl" variant="light" color="blue">
                      <IconFileCode size={24} />
                    </ThemeIcon>
                  </Group>
                </Card>
              </SimpleGrid>

              {/* Quick Actions */}
              <Card withBorder p="md" radius="md">
                <Text fw={600} mb="md">
                  Quick Actions
                </Text>
                <Group gap="sm">
                  <Button
                    leftSection={<IconRocket size={16} />}
                    variant="light"
                    color="blue"
                    onClick={runPreflight}
                    loading={preflightRunning}
                  >
                    Run Test Flight
                  </Button>
                  <Button
                    leftSection={<IconWand size={16} />}
                    variant="light"
                    color="violet"
                    onClick={runWizard}
                    loading={wizardLoading}
                  >
                    Run Audit Wizard
                  </Button>
                  <Button
                    leftSection={<IconShieldCheck size={16} />}
                    onClick={runAudit}
                    loading={auditRunning}
                  >
                    Run System Audit
                  </Button>
                  <Button
                    variant="light"
                    color="orange"
                    leftSection={<IconTrash size={16} />}
                    onClick={() => runCleanup(7)}
                    loading={cleanupRunning}
                  >
                    Cleanup Old Backups
                  </Button>
                  <Button
                    variant="light"
                    color="violet"
                    leftSection={<IconFileCode size={16} />}
                    onClick={() => setReviewModalOpen(true)}
                  >
                    Code Review
                  </Button>
                </Group>
              </Card>

              {/* Last Audit Summary */}
              {audit && (
                <Card withBorder p="md" radius="md">
                  <Group justify="space-between" mb="md">
                    <Text fw={600}>Last Audit Results</Text>
                    <Badge color={getHealthColor(audit.health_score)}>
                      {audit.health_score}% Health
                    </Badge>
                  </Group>

                  <Group gap="xl">
                    <RingProgress
                      size={100}
                      thickness={10}
                      roundCaps
                      sections={[
                        {
                          value: audit.health_score,
                          color: getHealthColor(audit.health_score),
                        },
                      ]}
                      label={
                        <Center>
                          <Text size="lg" fw={700}>
                            {audit.health_score}%
                          </Text>
                        </Center>
                      }
                    />
                    <Stack gap="xs">
                      <Text size="sm">
                        <strong>Status:</strong> {audit.status}
                      </Text>
                      <Text size="sm">
                        <strong>Checks:</strong> {audit.checks_passed}/{audit.checks_total} passed
                      </Text>
                      <Text size="sm">
                        <strong>Findings:</strong> {audit.findings.length}
                      </Text>
                      <Text size="xs" c="dimmed">
                        {new Date(audit.timestamp).toLocaleString()}
                      </Text>
                    </Stack>
                  </Group>

                  {audit.findings.length > 0 && (
                    <>
                      <Divider my="md" />
                      <Text fw={500} mb="sm">
                        Findings
                      </Text>
                      <Stack gap="xs">
                        {audit.findings.map((f, i) => (
                          <Paper key={i} withBorder p="sm" radius="sm">
                            <Group gap="sm">
                              <Badge color={getSeverityColor(f.severity)} size="sm">
                                {f.severity}
                              </Badge>
                              <Badge variant="light" color="gray" size="sm">
                                {f.domain}
                              </Badge>
                              <Text size="sm">{f.finding}</Text>
                            </Group>
                          </Paper>
                        ))}
                      </Stack>
                    </>
                  )}
                </Card>
              )}
            </Stack>
          </Tabs.Panel>

          {/* Wizard Tab */}
          <Tabs.Panel value="wizard">
            <Stack gap="md">
              <Card withBorder p="md" radius="md">
                <Group justify="space-between" align="center" wrap="wrap">
                  <div>
                    <Text fw={600}>Audit Wizard</Text>
                    <Text size="sm" c="dimmed">
                      Full system check with actionable recommendations.
                    </Text>
                  </div>
                  <Button
                    leftSection={<IconWand size={16} />}
                    onClick={runWizard}
                    loading={wizardLoading}
                  >
                    Run Audit Wizard
                  </Button>
                </Group>
                {wizardResult && (
                  <Text size="xs" c="dimmed" mt="sm">
                    Last run: {new Date(wizardResult.timestamp).toLocaleString()}
                  </Text>
                )}
              </Card>

              <Card withBorder p="md" radius="md">
                <Group justify="space-between" align="center" wrap="wrap">
                  <div>
                    <Text fw={600}>Test Flight</Text>
                    <Text size="sm" c="dimmed">
                      End-to-end preflight checks for auth, tasks, and agent health.
                    </Text>
                  </div>
                  <Button
                    leftSection={<IconRocket size={16} />}
                    onClick={runPreflight}
                    loading={preflightRunning}
                    variant="light"
                    color="blue"
                  >
                    Run Test Flight
                  </Button>
                </Group>

                <SimpleGrid cols={{ base: 1, sm: 3 }} mt="md">
                  <Paper withBorder p="sm" radius="md">
                    <Text size="xs" c="dimmed" mb={6}>
                      Execution mode
                    </Text>
                    <Switch
                      label={preflightIsolated ? "Isolated (recommended)" : "Use live backend"}
                      checked={preflightIsolated}
                      onChange={(e) => setPreflightIsolated(e.currentTarget.checked)}
                    />
                  </Paper>
                  <Paper withBorder p="sm" radius="md">
                    <Text size="xs" c="dimmed" mb={6}>
                      OAuth coverage
                    </Text>
                    <Switch
                      label={preflightIncludeOauth ? "Include Qwen OAuth (opens browser)" : "Skip OAuth"}
                      checked={preflightIncludeOauth}
                      onChange={(e) => setPreflightIncludeOauth(e.currentTarget.checked)}
                    />
                  </Paper>
                  <Paper withBorder p="sm" radius="md">
                    <Text size="xs" c="dimmed" mb={6}>
                      Destructive checks
                    </Text>
                    <Switch
                      label={preflightAllowDestructive ? "Allow destructive test actions" : "Read-only tests"}
                      checked={preflightAllowDestructive}
                      onChange={(e) => setPreflightAllowDestructive(e.currentTarget.checked)}
                    />
                  </Paper>
                </SimpleGrid>

                <SimpleGrid cols={{ base: 1, sm: 2 }} mt="md">
                  <Paper withBorder p="sm" radius="md">
                    <Text size="xs" c="dimmed">
                      Last test flight
                    </Text>
                    <Text fw={600}>
                      {preflightResult?.result?.status
                        ? preflightResult.result.status.toUpperCase()
                        : status?.metrics.last_preflight_status
                        ? status.metrics.last_preflight_status.toUpperCase()
                        : "Not run"}
                    </Text>
                    <Text size="xs" c="dimmed">
                      {preflightResult?.result?.timestamp ||
                        status?.metrics.last_preflight ||
                        "No timestamp available"}
                    </Text>
                    {preflightResult?.result?.failures !== undefined && (
                      <Text size="xs" mt="xs">
                        Failures: {preflightResult.result.failures}
                      </Text>
                    )}
                  </Paper>
                  <Paper withBorder p="sm" radius="md">
                    <Text size="xs" c="dimmed">
                      Command (CLI)
                    </Text>
                    <Code block>{preflightInfo?.command || "Unavailable"}</Code>
                    {preflightInfo?.notes && (
                      <Text size="xs" c="dimmed" mt="xs">
                        {preflightInfo.notes}
                      </Text>
                    )}
                  </Paper>
                </SimpleGrid>
              </Card>

              {wizardError && (
                <Alert color="red" icon={<IconAlertTriangle size={16} />} title="Wizard Error">
                  {wizardError}
                </Alert>
              )}

              {wizardLoading && (
                <Card withBorder p="md" radius="md">
                  <Group gap="sm">
                    <Loader size="sm" />
                    <Text size="sm" c="dimmed">
                      Running the full audit wizard. This can take a moment.
                    </Text>
                  </Group>
                </Card>
              )}

              {!wizardLoading && !wizardResult && !wizardError && (
                <Card withBorder p="md" radius="md">
                  <Box ta="center" py="lg">
                    <ThemeIcon size={56} variant="light" color="violet" mx="auto">
                      <IconWand size={28} />
                    </ThemeIcon>
                    <Text fw={600} mt="md">
                      Run the audit wizard
                    </Text>
                    <Text size="sm" c="dimmed" mt="xs">
                      Janitor will verify every subsystem and list fixes in priority order.
                    </Text>
                  </Box>
                </Card>
              )}

              {wizardResult && (
                <>
                  <Card withBorder p="md" radius="md">
                    <Group justify="space-between" mb="md" wrap="wrap">
                      <div>
                        <Text fw={600}>Wizard Summary</Text>
                        <Text size="sm" c="dimmed">
                          {wizardResult.summary.findings_count} findings across{" "}
                          {wizardResult.summary.checks_total} checks
                        </Text>
                      </div>
                      <RingProgress
                        size={90}
                        thickness={10}
                        roundCaps
                        sections={[
                          {
                            value: wizardResult.summary.health_score,
                            color: getHealthColor(wizardResult.summary.health_score),
                          },
                        ]}
                        label={
                          <Center>
                            <Text size="lg" fw={700}>
                              {wizardResult.summary.health_score}%
                            </Text>
                          </Center>
                        }
                      />
                    </Group>
                    <SimpleGrid cols={{ base: 1, sm: 3 }}>
                      <Paper withBorder p="sm" radius="md" ta="center">
                        <Text size="xs" c="dimmed">
                          Status
                        </Text>
                        <Text fw={700}>{wizardResult.summary.status}</Text>
                      </Paper>
                      <Paper withBorder p="sm" radius="md" ta="center">
                        <Text size="xs" c="dimmed">
                          Checks Passed
                        </Text>
                        <Text fw={700}>
                          {wizardResult.summary.checks_passed}/{wizardResult.summary.checks_total}
                        </Text>
                      </Paper>
                      <Paper withBorder p="sm" radius="md" ta="center">
                        <Text size="xs" c="dimmed">
                          Recommendations
                        </Text>
                        <Text fw={700}>{wizardResult.recommendations.length}</Text>
                      </Paper>
                    </SimpleGrid>
                  </Card>

                  <Card withBorder p="md" radius="md">
                    <Text fw={600} mb="md">
                      Checks
                    </Text>
                    <Stack gap="sm">
                      {wizardResult.sections.map((section) => (
                        <Paper key={section.id} withBorder p="sm" radius="md">
                          <Group justify="space-between" align="flex-start">
                            <Group gap="sm" align="flex-start">
                              <Badge color={getWizardStatusColor(section.status)} size="sm">
                                {section.status.toUpperCase()}
                              </Badge>
                              <div>
                                <Text fw={600}>{section.title}</Text>
                                <Text size="xs" c="dimmed">
                                  {section.summary}
                                </Text>
                              </div>
                            </Group>
                            {section.details?.backup_count !== undefined && (
                              <Badge variant="light" color="gray">
                                {section.details.backup_count} backups
                              </Badge>
                            )}
                          </Group>
                          {section.findings && section.findings.length > 0 ? (
                            <Stack gap={6} mt="sm">
                              {section.findings.map((finding, index) => (
                                <Group key={index} gap="xs" align="flex-start">
                                  <Badge size="xs" color={getSeverityColor(finding.severity)}>
                                    {finding.severity}
                                  </Badge>
                                  <Text size="sm">{finding.finding}</Text>
                                </Group>
                              ))}
                            </Stack>
                          ) : (
                            <Text size="xs" c="dimmed" mt="sm">
                              No issues detected.
                            </Text>
                          )}
                        </Paper>
                      ))}
                    </Stack>
                  </Card>

                  <Card withBorder p="md" radius="md">
                    <Group justify="space-between" mb="md">
                      <Text fw={600}>Recommendations</Text>
                      <Badge color={wizardResult.recommendations.length ? "yellow" : "green"}>
                        {wizardResult.recommendations.length ? "Review" : "All Clear"}
                      </Badge>
                    </Group>
                    {wizardResult.recommendations.length > 0 ? (
                      <Stack gap="sm">
                        {wizardResult.recommendations.map((rec) => (
                          <Paper key={rec.id} withBorder p="sm" radius="md">
                            <Group justify="space-between" align="flex-start">
                              <Group gap="sm" align="flex-start">
                                <ThemeIcon size="sm" variant="light" color="yellow">
                                  <IconBulb size={14} />
                                </ThemeIcon>
                                <div>
                                  <Group gap="xs">
                                    <Badge size="xs" color={getSeverityColor(rec.severity)}>
                                      {rec.severity}
                                    </Badge>
                                    <Text fw={600} size="sm">
                                      {rec.title}
                                    </Text>
                                  </Group>
                                  <Text size="sm" c="dimmed">
                                    {rec.description}
                                  </Text>
                                </div>
                              </Group>
                              {rec.can_auto_fix ? (
                                <Button
                                  size="xs"
                                  variant="light"
                                  color="green"
                                  loading={wizardFixing === rec.id}
                                  onClick={() => applyWizardFix(rec.id, rec.action, rec.params || {})}
                                >
                                  Apply Fix
                                </Button>
                              ) : (
                                <Badge size="sm" variant="light" color="gray">
                                  Manual
                                </Badge>
                              )}
                            </Group>
                          </Paper>
                        ))}
                      </Stack>
                    ) : (
                      <Text size="sm" c="dimmed">
                        No remediation required. Your system looks healthy.
                      </Text>
                    )}
                  </Card>

                </>
              )}

              <Card withBorder p="md" radius="md">
                <Group justify="space-between" mb="md">
                  <Text fw={600}>Wizard History</Text>
                  <ActionIcon variant="light" onClick={fetchWizardHistory} loading={wizardHistoryLoading}>
                    <IconRefresh size={16} />
                  </ActionIcon>
                </Group>
                {wizardHistory.length > 0 ? (
                  <Table striped highlightOnHover>
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th>Time</Table.Th>
                        <Table.Th>Health</Table.Th>
                        <Table.Th>Status</Table.Th>
                        <Table.Th>Findings</Table.Th>
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {wizardHistory.map((run) => (
                        <Table.Tr key={run.id}>
                          <Table.Td>
                            <Text size="sm">{new Date(run.timestamp).toLocaleString()}</Text>
                          </Table.Td>
                          <Table.Td>
                            <Badge color={getHealthColor(run.health_score)}>
                              {run.health_score}%
                            </Badge>
                          </Table.Td>
                          <Table.Td>
                            <Badge variant="light">{run.status}</Badge>
                          </Table.Td>
                          <Table.Td>
                            <Text size="sm">{run.findings_count}</Text>
                          </Table.Td>
                        </Table.Tr>
                      ))}
                    </Table.Tbody>
                  </Table>
                ) : (
                  <Box py="md" ta="center">
                    <Text size="sm" c="dimmed">
                      {wizardHistoryLoading ? "Loading wizard history..." : "No wizard runs saved yet."}
                    </Text>
                  </Box>
                )}
              </Card>
            </Stack>
          </Tabs.Panel>

          {/* Audit Tab */}
          <Tabs.Panel value="audit">
            <Stack gap="md">
              <Card withBorder p="md" radius="md">
                <Group justify="space-between" mb="md">
                  <div>
                    <Text fw={600}>System Health Audit</Text>
                    <Text size="sm" c="dimmed">
                      Comprehensive check of database, disk, agents, and backups
                    </Text>
                  </div>
                  <Button
                    leftSection={<IconShieldCheck size={16} />}
                    onClick={runAudit}
                    loading={auditRunning}
                  >
                    Run Audit
                  </Button>
                </Group>

                {audit ? (
                  <Stack gap="md">
                    <SimpleGrid cols={{ base: 1, sm: 4 }}>
                      <Paper withBorder p="md" radius="md" ta="center">
                        <Text size="xs" c="dimmed">
                          Health Score
                        </Text>
                        <Text size="xl" fw={700} c={getHealthColor(audit.health_score)}>
                          {audit.health_score}%
                        </Text>
                      </Paper>
                      <Paper withBorder p="md" radius="md" ta="center">
                        <Text size="xs" c="dimmed">
                          Status
                        </Text>
                        <Text size="xl" fw={700}>
                          {audit.status}
                        </Text>
                      </Paper>
                      <Paper withBorder p="md" radius="md" ta="center">
                        <Text size="xs" c="dimmed">
                          Checks Passed
                        </Text>
                        <Text size="xl" fw={700}>
                          {audit.checks_passed}/{audit.checks_total}
                        </Text>
                      </Paper>
                      <Paper withBorder p="md" radius="md" ta="center">
                        <Text size="xs" c="dimmed">
                          Findings
                        </Text>
                        <Text
                          size="xl"
                          fw={700}
                          c={audit.findings.length === 0 ? "green" : "orange"}
                        >
                          {audit.findings.length}
                        </Text>
                      </Paper>
                    </SimpleGrid>

                    <Progress
                      value={(audit.checks_passed / audit.checks_total) * 100}
                      color={getHealthColor(audit.health_score)}
                      size="lg"
                      radius="xl"
                    />

                    {audit.findings.length > 0 && (
                      <Table striped highlightOnHover>
                        <Table.Thead>
                          <Table.Tr>
                            <Table.Th>Severity</Table.Th>
                            <Table.Th>Domain</Table.Th>
                            <Table.Th>Finding</Table.Th>
                          </Table.Tr>
                        </Table.Thead>
                        <Table.Tbody>
                          {audit.findings.map((f, i) => (
                            <Table.Tr key={i}>
                              <Table.Td>
                                <Badge color={getSeverityColor(f.severity)}>{f.severity}</Badge>
                              </Table.Td>
                              <Table.Td>
                                <Badge variant="light">{f.domain}</Badge>
                              </Table.Td>
                              <Table.Td>{f.finding}</Table.Td>
                            </Table.Tr>
                          ))}
                        </Table.Tbody>
                      </Table>
                    )}
                  </Stack>
                ) : (
                  <Box py="xl" ta="center">
                    <ThemeIcon size={60} variant="light" color="gray" mx="auto">
                      <IconShieldCheck size={30} />
                    </ThemeIcon>
                    <Text c="dimmed" mt="md">
                      No audit run yet
                    </Text>
                    <Text size="sm" c="dimmed">
                      Click &quot;Run Audit&quot; to check system health
                    </Text>
                  </Box>
                )}
              </Card>
            </Stack>
          </Tabs.Panel>

          {/* Edit History Tab */}
          <Tabs.Panel value="history">
            <Card withBorder p="md" radius="md">
              <Group justify="space-between" mb="md">
                <Text fw={600}>Recent File Edits</Text>
                <ActionIcon variant="light" onClick={fetchEditHistory}>
                  <IconRefresh size={16} />
                </ActionIcon>
              </Group>

              {editHistory.length > 0 ? (
                <Table striped highlightOnHover>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Status</Table.Th>
                      <Table.Th>Time</Table.Th>
                      <Table.Th>File</Table.Th>
                      <Table.Th>Agent</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {editHistory.map((edit, i) => (
                      <Table.Tr key={i}>
                        <Table.Td>
                          {edit.success ? (
                            <ThemeIcon size="sm" color="green" variant="light">
                              <IconCheck size={12} />
                            </ThemeIcon>
                          ) : (
                            <ThemeIcon size="sm" color="red" variant="light">
                              <IconX size={12} />
                            </ThemeIcon>
                          )}
                        </Table.Td>
                        <Table.Td>
                          <Text size="sm">{new Date(edit.timestamp).toLocaleString()}</Text>
                        </Table.Td>
                        <Table.Td>
                          <Code>{edit.file}</Code>
                        </Table.Td>
                        <Table.Td>
                          <Badge variant="light">{edit.agent}</Badge>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              ) : (
                <Box py="xl" ta="center">
                  <Text c="dimmed">No edit history yet</Text>
                </Box>
              )}
            </Card>
          </Tabs.Panel>

          {/* Backups Tab */}
          <Tabs.Panel value="backups">
            <Card withBorder p="md" radius="md">
              <Group justify="space-between" mb="md">
                <div>
                  <Text fw={600}>Backup Files</Text>
                  <Text size="sm" c="dimmed">
                    {backups.length} backups stored
                  </Text>
                </div>
                <Group gap="sm">
                  <Button
                    variant="light"
                    color="orange"
                    leftSection={<IconTrash size={16} />}
                    onClick={() => runCleanup(7)}
                    loading={cleanupRunning}
                  >
                    Cleanup (&gt;7 days)
                  </Button>
                  <ActionIcon variant="light" onClick={fetchBackups}>
                    <IconRefresh size={16} />
                  </ActionIcon>
                </Group>
              </Group>

              {backups.length > 0 ? (
                <ScrollArea h={400}>
                  <Table striped highlightOnHover>
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th>Modified</Table.Th>
                        <Table.Th>Size</Table.Th>
                        <Table.Th>Filename</Table.Th>
                        <Table.Th style={{ width: 50 }}>Actions</Table.Th>
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {backups.map((backup, i) => (
                        <Table.Tr key={i}>
                          <Table.Td>
                            <Text size="sm">{new Date(backup.modified).toLocaleString()}</Text>
                          </Table.Td>
                          <Table.Td>
                            <Text size="sm">{formatBytes(backup.size_bytes)}</Text>
                          </Table.Td>
                          <Table.Td>
                            <Tooltip label={backup.filename}>
                              <Code style={{ maxWidth: 300, overflow: "hidden", textOverflow: "ellipsis" }}>
                                {backup.filename.length > 40
                                  ? backup.filename.slice(0, 40) + "..."
                                  : backup.filename}
                              </Code>
                            </Tooltip>
                          </Table.Td>
                          <Table.Td>
                            <ActionIcon
                              variant="subtle"
                              color="red"
                              size="sm"
                              onClick={() => deleteBackup(backup.filename)}
                            >
                              <IconTrash size={14} />
                            </ActionIcon>
                          </Table.Td>
                        </Table.Tr>
                      ))}
                    </Table.Tbody>
                  </Table>
                </ScrollArea>
              ) : (
                <Box py="xl" ta="center">
                  <ThemeIcon size={60} variant="light" color="gray" mx="auto">
                    <IconCloudDownload size={30} />
                  </ThemeIcon>
                  <Text c="dimmed" mt="md">
                    No backup files found
                  </Text>
                </Box>
              )}
            </Card>
          </Tabs.Panel>

          {/* Activity Logs Tab */}
          <Tabs.Panel value="logs">
            <Card withBorder p="md" radius="md">
              <Group justify="space-between" mb="md">
                <Text fw={600}>Activity Logs</Text>
                <ActionIcon variant="light" onClick={fetchLogs}>
                  <IconRefresh size={16} />
                </ActionIcon>
              </Group>

              {logs.length > 0 ? (
                <Timeline active={0} bulletSize={24}>
                  {logs.slice(0, 20).map((log, i) => (
                    <Timeline.Item
                      key={i}
                      bullet={
                        log.status === "success" ? (
                          <IconCheck size={12} />
                        ) : log.status === "warning" ? (
                          <IconAlertTriangle size={12} />
                        ) : (
                          <IconX size={12} />
                        )
                      }
                      color={getStatusColor(log.status)}
                      title={log.action}
                    >
                      <Text c="dimmed" size="sm">
                        {log.details}
                      </Text>
                      <Text size="xs" mt={4} c="dimmed">
                        {new Date(log.timestamp).toLocaleString()}
                      </Text>
                    </Timeline.Item>
                  ))}
                </Timeline>
              ) : (
                <Box py="xl" ta="center">
                  <Text c="dimmed">No activity logs yet</Text>
                </Box>
              )}
            </Card>
          </Tabs.Panel>

          {/* Chat Tab */}
          <Tabs.Panel value="chat">
            <Card withBorder p="md" radius="md">
              <Group justify="space-between" mb="md">
                <Stack gap={2}>
                  <Text fw={600}>Janitor chat</Text>
                  <Text size="xs" c="dimmed">
                    Sessions are saved per user. Archive or delete as needed.
                  </Text>
                </Stack>
              </Group>

              <Box mb="md">
                <Group justify="space-between" align="center" mb="xs">
                  <Text size="xs" fw={600} c="dimmed">
                    Sessions
                  </Text>
                  <Group gap="xs">
                    <Button
                      size="xs"
                      variant="light"
                      leftSection={<IconPlus size={12} />}
                      onClick={handleNewChatSession}
                    >
                      New
                    </Button>
                    <Group gap={6}>
                      <Text size="xs" c="dimmed">Archived</Text>
                      <Switch
                        size="sm"
                        checked={chatShowArchived}
                        onChange={(e) => setChatShowArchived(e.currentTarget.checked)}
                      />
                    </Group>
                  </Group>
                </Group>
                <ScrollArea h={140}>
                  <Stack gap="xs">
                    {chatSessionsLoading && (
                      <Text size="xs" c="dimmed">Loading sessions…</Text>
                    )}
                    {!chatSessionsLoading && chatSessions.length === 0 && (
                      <Text size="xs" c="dimmed">No sessions yet</Text>
                    )}
                    {chatSessions.map((session) => {
                      const label =
                        session.title
                        || session.last_message?.slice(0, 48)
                        || (session.updated_at
                          ? `Session ${new Date(session.updated_at).toLocaleDateString()}`
                          : "Session");
                      const isActive = session.id === chatConversationId;
                      const isArchived = Boolean(session.archived_at);
                      return (
                        <Paper
                          key={session.id}
                          withBorder
                          p="xs"
                          radius="md"
                          onClick={() => handleSelectChatSession(session.id)}
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
                                  handleRenameChatSession(session.id, session.title);
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
                                    handleRestoreChatSession(session.id);
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
                                    handleArchiveChatSession(session.id);
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
                                  handleDeleteChatSession(session.id);
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
                {chatSessionsError && (
                  <Text size="xs" c="red" mt="xs">
                    {chatSessionsError}
                  </Text>
                )}
              </Box>

              <ScrollArea h={300} mb="md">
                <Stack gap="sm">
                  {chatHistoryStatus === "error" && chatHistoryError && (
                    <Alert color="red" title="History error">
                      {chatHistoryError}
                    </Alert>
                  )}
                  {chatHistory.length === 0 && (
                    <Box ta="center" py="xl">
                      <Text c="dimmed">
                        Start a conversation with Janitor.
                      </Text>
                      <Text size="xs" c="dimmed" mt="sm">
                        Try: &quot;run audit&quot;, &quot;cleanup&quot;, &quot;show edit history&quot;
                      </Text>
                    </Box>
                  )}
                  {chatHistory.map((msg, i) => (
                    <Paper
                      key={i}
                      withBorder
                      p="sm"
                      radius="md"
                      bg={
                        msg.role === "user"
                          ? "var(--mantine-color-blue-light)"
                          : msg.role === "error"
                          ? "var(--mantine-color-red-light)"
                          : "var(--surface-2)"
                      }
                      style={{
                        alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
                        maxWidth: "80%",
                      }}
                    >
                      <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                        {msg.content}
                      </Text>
                    </Paper>
                  ))}
                  {chatLoading && (
                    <Group gap="xs">
                      <Loader size="xs" />
                      <Text size="sm" c="dimmed">
                        Janitor is typing...
                      </Text>
                    </Group>
                  )}
                </Stack>
              </ScrollArea>

              <Group gap="sm">
                <TextInput
                  style={{ flex: 1 }}
                  placeholder="Ask Janitor anything..."
                  value={chatMessage}
                  onChange={(e) => setChatMessage(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && sendChatMessage()}
                />
                <Button
                  leftSection={<IconSend size={16} />}
                  onClick={sendChatMessage}
                  loading={chatLoading}
                >
                  Send
                </Button>
              </Group>
            </Card>
          </Tabs.Panel>
        </Tabs>
      </Container>
          </Page>
    </Shell>
  );
}
