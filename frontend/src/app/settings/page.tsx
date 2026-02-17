"use client";
import { Shell } from "@/components/layout/Shell";
import { Page } from "@/components/layout/Page";
import { LaunchModal } from "@/components/LaunchModal";
import { ConnectorMarketplace } from "@/components/ConnectorMarketplace";
import { WidgetManager } from "@/components/WidgetManager";
import { apiFetch, getApiBaseUrl, isNetworkError } from "@/lib/api";

import {
  Card, Text, Title, Stack, Tabs, Switch, Group, TextInput, Button,
  Divider, Select, NumberInput, Badge, Paper, Box, ActionIcon, Tooltip,
  Alert, Code, Textarea, PasswordInput, SimpleGrid, ThemeIcon,
  Accordion, Checkbox, Progress, Transition, rem, Drawer, Table, Loader, ScrollArea, Modal,
  SegmentedControl, CopyButton,
} from "@mantine/core";
import { tokens } from "@/theme/tokens";
import {
  IconSettings, IconBell, IconShield, IconDatabase,
  IconRocket, IconBrandWhatsapp, IconMail, IconCpu, IconTool,
  IconCoin, IconUsers, IconFolders, IconAlertCircle, IconCheck,
  IconDownload, IconUpload, IconTrash, IconRefresh, IconKey, IconHome,
  IconWand, IconLayout, IconChecklist, IconExternalLink, IconCopy
} from "@tabler/icons-react";
import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import * as api from "@/lib/api";
import { notifications } from "@mantine/notifications";
import { ContextStackedBar } from "@/components/ContextStackedBar";

const getErrorMessage = (err: any, fallback: string) =>
  err?.detail || err?.message || (typeof err === "string" ? err : fallback);

const formatBytes = (value: number | null | undefined) => {
  if (!value && value !== 0) return "—";
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  if (value < 1024 * 1024 * 1024) return `${(value / (1024 * 1024)).toFixed(1)} MB`;
  return `${(value / (1024 * 1024 * 1024)).toFixed(1)} GB`;
};

// Agent Config Card with status indicator
function AgentConfigCard({
  name,
  icon: Icon,
  color,
  enabled,
  onToggle,
  status = "idle",
  loading = false,
  children,
}: {
  name: string;
  icon: React.ElementType;
  color: string;
  enabled: boolean;
  onToggle: () => void;
  status?: "idle" | "running" | "error";
  loading?: boolean;
  children?: React.ReactNode;
}) {
  const statusColors = {
    idle: tokens.colors.neutral[400],
    running: tokens.colors.success[500],
    error: tokens.colors.error[500],
  };

  return (
    <Card
      withBorder
      radius="lg"
      p="md"
      style={{
        borderLeft: enabled ? `4px solid ${statusColors[status]}` : undefined,
        opacity: enabled ? 1 : 0.7,
        transition: "all 200ms ease",
      }}
    >
      <Group justify="space-between" mb={children && enabled ? "md" : 0}>
        <Group gap="sm">
          <Box style={{ position: "relative" }}>
            <ThemeIcon size="lg" variant="light" color={enabled ? color : "gray"} radius="md">
              <Icon size={20} />
            </ThemeIcon>
            {enabled && (
              <Box
                style={{
                  position: "absolute",
                  bottom: -2,
                  right: -2,
                  width: 10,
                  height: 10,
                  borderRadius: "50%",
                  backgroundColor: statusColors[status],
                  border: "2px solid var(--mantine-color-body)",
                }}
                className={status === "running" ? "animate-pulse" : ""}
              />
            )}
          </Box>
          <div>
            <Text fw={600}>{name}</Text>
            <Text size="xs" c="dimmed">
              {enabled ? (status === "running" ? "Running" : "Active") : "Disabled"}
            </Text>
          </div>
        </Group>
        <Switch
          checked={enabled}
          onChange={onToggle}
          color={color}
          disabled={loading}
          styles={{
            track: {
              transition: "background 200ms ease",
              opacity: loading ? 0.5 : 1,
            },
          }}
        />
      </Group>
      <Transition mounted={enabled && !!children} transition="slide-down" duration={200}>
        {(styles) => (
          <Box
            style={{
              ...styles,
              borderTop: "1px solid var(--mantine-color-default-border)",
              marginTop: rem(12),
              paddingTop: rem(12),
            }}
          >
            {children}
          </Box>
        )}
      </Transition>
    </Card>
  );
}

// Connector Config Card with connection status
function ConnectorCard({
  name,
  icon: Icon,
  color,
  connected,
  account,
  lastSync,
  onConnect,
  onDisconnect,
  disabled = false,
  disabledReason = "Not available",
}: {
  name: string;
  icon: React.ElementType;
  color: string;
  connected: boolean;
  account?: string;
  lastSync?: string;
  onConnect: () => void;
  onDisconnect: () => void;
  disabled?: boolean;
  disabledReason?: string;
}) {
  return (
    <Paper
      withBorder
      radius="lg"
      p="md"
      style={{
        borderLeft: connected ? `4px solid ${tokens.colors.success[500]}` : undefined,
        opacity: disabled ? 0.6 : 1,
        transition: "all 200ms ease",
      }}
    >
      <Group justify="space-between">
        <Group gap="sm">
          <Box style={{ position: "relative" }}>
            <ThemeIcon size="lg" variant="light" color={connected ? color : "gray"} radius="md">
              <Icon size={20} />
            </ThemeIcon>
            {connected && (
              <Box
                style={{
                  position: "absolute",
                  bottom: -2,
                  right: -2,
                  width: 10,
                  height: 10,
                  borderRadius: "50%",
                  backgroundColor: tokens.colors.success[500],
                  border: "2px solid var(--mantine-color-body)",
                }}
              />
            )}
          </Box>
          <div>
            <Group gap="xs">
              <Text fw={500}>{name}</Text>
              {connected && (
                <Badge size="xs" color="success" variant="light">
                  Connected
                </Badge>
              )}
              {disabled && (
                <Badge size="xs" color="gray" variant="light">
                  Unavailable
                </Badge>
              )}
            </Group>
            {connected && account ? (
              <Text size="xs" c="dimmed">{account}</Text>
            ) : (
              <Text size="xs" c="dimmed">{disabled ? disabledReason : "Not connected"}</Text>
            )}
            {connected && lastSync && (
              <Text size="xs" c="dimmed">Last sync: {lastSync}</Text>
            )}
          </div>
        </Group>
        {connected ? (
          <Button size="xs" variant="subtle" color="red" onClick={onDisconnect}>
            Disconnect
          </Button>
        ) : disabled ? (
          <Button size="xs" variant="light" color="gray" disabled>
            Unavailable
          </Button>
        ) : (
          <Button size="xs" variant="light" color={color} onClick={onConnect}>
            Connect
          </Button>
        )}
      </Group>
    </Paper>
  );
}

// Save confirmation component
function SaveConfirmation({ visible, onClose }: { visible: boolean; onClose: () => void }) {
  return (
    <Transition mounted={visible} transition="slide-up" duration={200}>
      {(styles) => (
        <Paper
          style={{
            ...styles,
            position: "fixed",
            bottom: 24,
            left: "50%",
            transform: "translateX(-50%)",
            zIndex: 1000,
            padding: "12px 24px",
            backgroundColor: tokens.colors.success[500],
            color: "white",
            borderRadius: 12,
            boxShadow: tokens.shadow.elevated,
            display: "flex",
            alignItems: "center",
            gap: 12,
          }}
        >
          <IconCheck size={20} />
          <Text size="sm" fw={500}>Settings saved successfully</Text>
          <ActionIcon variant="transparent" color="white" size="sm" onClick={onClose}>
            <IconRefresh size={16} />
          </ActionIcon>
        </Paper>
      )}
    </Transition>
  );
}

export default function SettingsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const apiBase = getApiBaseUrl();

  const [launching, setLaunching] = useState(false);
  const [showLaunchModal, setShowLaunchModal] = useState(false);
  const [showSaveConfirmation, setShowSaveConfirmation] = useState(false);
  const [activeTab, setActiveTab] = useState(searchParams.get("tab") || "general");

  // Backend connectivity
  const [backendConnected, setBackendConnected] = useState<boolean | null>(null);
  
  // System running state
  const [systemRunning, setSystemRunning] = useState(false);
  const [systemLoading, setSystemLoading] = useState(false);
  const [lastBackup, setLastBackup] = useState<string | null>(null);
  const [lastShutdown, setLastShutdown] = useState<string | null>(null);
  
  // Inbox sync state
  const [inboxEnabled, setInboxEnabled] = useState(false);
  const [inboxLaunching, setInboxLaunching] = useState(false);
  const [inboxStatus, setInboxStatus] = useState<string | null>(null);
  const [mailSettings, setMailSettings] = useState({
    allowAgentReplies: false,
    allowWhatsappReplies: false,
    allowEmailReplies: false,
    gmailEnabled: true,
    whatsappEnabled: true,
  });
  const [mailSettingsSaving, setMailSettingsSaving] = useState(false);
  const [mailSettingsError, setMailSettingsError] = useState<string | null>(null);
  const [connectorStatus, setConnectorStatus] = useState<{
    whatsapp?: { connected: boolean; phone?: string | null; status?: string; error?: string };
    gmail?: { connected: boolean; accounts: string[]; status?: string };
  }>({});
  
  // Database stats
  const [dbStats, setDbStats] = useState<{
    size_formatted: string;
    last_backup: string | null;
  }>({ size_formatted: "Loading...", last_backup: null });
  const [dbLoading, setDbLoading] = useState(false);
  const [backupModalOpen, setBackupModalOpen] = useState(false);
  const [backupList, setBackupList] = useState<any[]>([]);
  const [backupListLoading, setBackupListLoading] = useState(false);
  const [backupListError, setBackupListError] = useState<string | null>(null);
  const [backupRestoring, setBackupRestoring] = useState<string | null>(null);

  // Data counts for clean slate
  const [dataCounts, setDataCounts] = useState({
    inbox_messages: 0,
    unread_messages: 0,
    pending_tasks: 0,
    completed_tasks: 0,
    unpaid_bills: 0,
    paid_bills: 0,
    activity_events: 0,
    portfolio_holdings: 0,
    projects: 0,
    contractors: 0,
  });
  
  // Agent states - use API-compatible IDs
  const [agents, setAgents] = useState<Record<string, boolean>>({
    finance: true,
    maintenance: true,
    contractors: true,
    projects: true,
    "security-manager": true,
    janitor: true,
    "backup-recovery": false,
  });
  const [agentToggling, setAgentToggling] = useState<string | null>(null);

  // Agent context budgets
  const [contextAgents, setContextAgents] = useState<any[]>([]);
  const [contextAgentsLoading, setContextAgentsLoading] = useState(false);
  const [contextAgentsError, setContextAgentsError] = useState<string | null>(null);
  const [selectedContextAgent, setSelectedContextAgent] = useState<string | null>(null);
  const [agentContextDetail, setAgentContextDetail] = useState<any>(null);
  const [agentContextLoading, setAgentContextLoading] = useState(false);
  const [agentContextError, setAgentContextError] = useState<string | null>(null);
  const [contextWindowTokens, setContextWindowTokens] = useState(0);
  const [reservedOutputTokens, setReservedOutputTokens] = useState(0);
  const [contextBudgets, setContextBudgets] = useState<Record<string, number>>({});
  const [contextSaving, setContextSaving] = useState(false);
  const [simulateState, setSimulateState] = useState<"idle" | "loading" | "error">("idle");
  const [simulateResult, setSimulateResult] = useState<any>(null);
  const [explainOpen, setExplainOpen] = useState(false);

  const makeDefaultSettings = () => ({
    autoRefresh: true,
    systemCostCap: 1000,
    dailySpendLimit: 350,
    approvalThreshold: 500,
    householdName: "",
    timezone: "America/Los_Angeles",
    notifications: {
      inApp: true,
      push: false,
      email: false,
      alertEmail: "",
      whatsapp: false,
      urgentOnly: false,
      dailySummary: true,
      weeklyReport: true,
    },
    security: {
      auditLogging: true,
      threatMonitoring: true,
      credentialRotationDays: 90,
    },
  });
  // Settings state
  const [settings, setSettings] = useState(makeDefaultSettings);
  const [savedSettings, setSavedSettings] = useState(makeDefaultSettings);
  const [settingsSaving, setSettingsSaving] = useState(false);
  const defaultLlmState = {
    provider: "openai-compatible",
    baseUrl: "https://api.venice.ai/api/v1",
    model: "qwen3-coder-next",
    apiKey: "",
    apiKeySet: false,
    authType: "api_key",
    oauthConnected: false,
    oauthExpiresAt: null as number | null,
    oauthResourceUrl: null as string | null,
  };
  const defaultLlmRuntime = {
    ready: false,
    provider: "",
    model: "",
    baseUrl: "",
    authType: "",
    error: "",
  };
  const [llmActive, setLlmActive] = useState({ ...defaultLlmState });
  const [llmConfig, setLlmConfig] = useState({ ...defaultLlmState });
  const [llmRuntime, setLlmRuntime] = useState({ ...defaultLlmRuntime });
  const [llmSaving, setLlmSaving] = useState(false);
  const [llmError, setLlmError] = useState<string | null>(null);
  const [llmSaved, setLlmSaved] = useState(false);
  const readInputValue = (eventOrValue: any) => {
    if (typeof eventOrValue === "string") return eventOrValue;
    return eventOrValue?.currentTarget?.value ?? "";
  };
  const providerDefaults = (provider: string) => {
    if (provider === "openai") {
      return { baseUrl: "https://api.openai.com/v1", model: "gpt-4o-mini" };
    }
    if (provider === "anthropic") {
      return { baseUrl: "", model: "claude-3-5-sonnet" };
    }
    return { baseUrl: "https://api.venice.ai/api/v1", model: "qwen3-coder-next" };
  };
  const qwenDefaults = () => {
    const currentModel = llmConfig.model || "";
    const model = currentModel.toLowerCase().startsWith("qwen") ? currentModel : "qwen3-coder-next";
    return {
      baseUrl: llmConfig.oauthResourceUrl || llmActive.oauthResourceUrl || "https://dashscope.aliyuncs.com/compatible-mode/v1",
      model,
      provider: "openai-compatible",
    };
  };
  const [identity, setIdentity] = useState({
    soul: "",
    user: "",
    security: "",
    tools: "",
    heartbeat: "",
    memory: "",
  });
  const [identityStatus, setIdentityStatus] = useState<any>(null);
  const [identityLoading, setIdentityLoading] = useState(false);
  const [identitySaving, setIdentitySaving] = useState(false);
  const [identityError, setIdentityError] = useState<string | null>(null);
  const [templateModalOpen, setTemplateModalOpen] = useState(false);
  const [templateLoading, setTemplateLoading] = useState(false);
  const [templateError, setTemplateError] = useState<string | null>(null);
  const [templateData, setTemplateData] = useState<Record<string, string>>({});
  const [templateFile, setTemplateFile] = useState("soul");
  const [qwenOauth, setQwenOauth] = useState({
    status: "idle" as "idle" | "starting" | "pending" | "success" | "error",
    sessionId: null as string | null,
    userCode: "",
    verificationUri: "",
    verificationUriComplete: "",
    intervalSeconds: 5,
    expiresAt: "",
    error: null as string | null,
  });
  const qwenPollRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const QWEN_OAUTH_STORAGE_KEY = "mycasa_qwen_oauth_pending_v1";
  const llmDirty = useMemo(() => {
    const configChanged =
      llmConfig.provider !== llmActive.provider ||
      llmConfig.baseUrl !== llmActive.baseUrl ||
      llmConfig.model !== llmActive.model ||
      llmConfig.authType !== llmActive.authType;
    const keyChanged = llmConfig.authType === "api_key" && llmConfig.apiKey.trim().length > 0;
    return configChanged || keyChanged;
  }, [llmConfig, llmActive]);
  const settingsDirty = useMemo(
    () => JSON.stringify(settings) !== JSON.stringify(savedSettings),
    [settings, savedSettings]
  );

  useEffect(() => {
    setActiveTab(searchParams.get("tab") || "general");
  }, [searchParams]);

  useEffect(() => {
    setLlmSaved(false);
  }, [llmConfig.provider, llmConfig.baseUrl, llmConfig.model, llmConfig.authType, llmConfig.apiKey]);

  const handleTabChange = (value: string | null) => {
    const next = value || "general";
    setActiveTab(next);
    const params = new URLSearchParams(window.location.search);
    if (next === "general") {
      params.delete("tab");
    } else {
      params.set("tab", next);
    }
    const query = params.toString();
    router.replace(query ? `/settings?${query}` : "/settings", { scroll: false });
  };

  const refreshSystemStatus = useCallback(async () => {
    try {
      const data = await apiFetch<any>("/api/system/status");
      setBackendConnected(true);
      setSystemRunning(data.running);
      setLastBackup(data.last_backup);
      setLastShutdown(data.last_shutdown);
      if (data.agents_enabled) {
        // Map API agent keys to our state keys
        const apiAgents = data.agents_enabled;
        setAgents((prev) => ({
          ...prev,
          finance: apiAgents.finance ?? prev.finance,
          maintenance: apiAgents.maintenance ?? prev.maintenance,
          contractors: apiAgents.contractors ?? prev.contractors,
          projects: apiAgents.projects ?? prev.projects,
          "security-manager": apiAgents["security-manager"] ?? apiAgents.security ?? prev["security-manager"],
          janitor: apiAgents.janitor ?? prev.janitor,
          "backup-recovery": apiAgents["backup-recovery"] ?? apiAgents.backup ?? prev["backup-recovery"],
        }));
      }
    } catch (e) {
      if (!isNetworkError(e)) {
        console.error("Failed to fetch system status:", e);
      }
      setBackendConnected(false);
    }
  }, []);

  // Fetch system status on load
  useEffect(() => {
    refreshSystemStatus();

    // Poll every 10 seconds
    const interval = setInterval(refreshSystemStatus, 10000);
    return () => clearInterval(interval);
  }, [refreshSystemStatus]);

  const fetchSystemSettings = useCallback(async () => {
    try {
      const data = await apiFetch<any>("/api/settings/system");
      const merge = (prev: typeof llmConfig) => ({
        ...prev,
        provider: data.llm_provider ?? prev.provider,
        baseUrl: data.llm_base_url ?? prev.baseUrl,
        model: data.llm_model ?? prev.model,
        apiKeySet: Boolean(data.llm_api_key_set),
        authType: data.llm_auth_type ?? prev.authType,
        oauthConnected: Boolean(data.llm_oauth_connected),
        oauthExpiresAt: data.llm_oauth_expires_at ?? null,
        oauthResourceUrl: data.llm_oauth_resource_url ?? null,
        apiKey: "",
      });
      setLlmRuntime({
        ready: Boolean(data.llm_runtime_ready),
        provider: data.llm_runtime_provider || "",
        model: data.llm_runtime_model || "",
        baseUrl: data.llm_runtime_base_url || "",
        authType: data.llm_runtime_auth_type || "",
        error: data.llm_runtime_error || "",
      });
      setLlmActive((prev) => merge(prev));
      setLlmConfig((prev) => merge(prev));

      const systemPatch = {
        autoRefresh: data.auto_refresh ?? true,
        systemCostCap: typeof data.monthly_cost_cap === "number" ? data.monthly_cost_cap : 1000,
        dailySpendLimit: typeof data.daily_spend_limit === "number" ? data.daily_spend_limit : 350,
        approvalThreshold: typeof data.approval_threshold === "number" ? data.approval_threshold : 500,
        householdName: data.household_name ?? "",
        timezone: data.timezone ?? "America/Los_Angeles",
      };
      setSettings((prev) => ({ ...prev, ...systemPatch }));
      setSavedSettings((prev) => ({ ...prev, ...systemPatch }));
    } catch (e) {
      // Non-blocking; leave defaults
    }
  }, []);

  const fetchNotificationSettings = useCallback(async () => {
    try {
      const data = await apiFetch<any>("/api/settings/notifications");
      const notifPatch = {
        inApp: Boolean(data.in_app),
        push: Boolean(data.push),
        email: Boolean(data.email),
        alertEmail: data.alert_email || "",
        whatsapp: Boolean(data.whatsapp),
        urgentOnly: Boolean(data.urgent_only),
        dailySummary: Boolean(data.daily_summary),
        weeklyReport: Boolean(data.weekly_report),
      };
      setSettings((prev) => ({ ...prev, notifications: { ...prev.notifications, ...notifPatch } }));
      setSavedSettings((prev) => ({ ...prev, notifications: { ...prev.notifications, ...notifPatch } }));
    } catch (e) {
      // Non-blocking; leave defaults
    }
  }, []);

  const fetchSecuritySettings = useCallback(async () => {
    try {
      const data = await apiFetch<any>("/api/settings/agent/security");
      const securityPatch = {
        auditLogging: Boolean(data.audit_logging),
        threatMonitoring: Boolean(data.threat_monitoring),
        credentialRotationDays:
          typeof data.credential_rotation_days === "number" ? data.credential_rotation_days : 90,
      };
      setSettings((prev) => ({ ...prev, security: { ...prev.security, ...securityPatch } }));
      setSavedSettings((prev) => ({ ...prev, security: { ...prev.security, ...securityPatch } }));
    } catch (e) {
      // Non-blocking; leave defaults
    }
  }, []);

  const fetchMailSettings = useCallback(async () => {
    setMailSettingsError(null);
    try {
      const data = await apiFetch<any>("/api/settings/agent/mail");
      setMailSettings({
        allowAgentReplies: Boolean(data.allow_agent_replies),
        allowWhatsappReplies: Boolean(data.allow_whatsapp_replies),
        allowEmailReplies: Boolean(data.allow_email_replies),
        gmailEnabled: Boolean(data.gmail_enabled),
        whatsappEnabled: Boolean(data.whatsapp_enabled),
      });
    } catch (e) {
      setMailSettingsError(getErrorMessage(e, "Failed to load inbox reply settings"));
    }
  }, []);

  const fetchConnectorStatus = useCallback(async () => {
    try {
      const [wa, google] = await Promise.all([
        apiFetch<any>("/api/connectors/whatsapp/status"),
        apiFetch<any>("/api/google/status"),
      ]);
      setConnectorStatus({
        whatsapp: {
          connected: Boolean(wa?.connected),
          phone: wa?.phone || null,
          status: wa?.status,
          error: wa?.error,
        },
        gmail: {
          connected: Boolean(google?.accounts?.length),
          accounts: Array.isArray(google?.accounts) ? google.accounts : [],
          status: google?.auth_status,
        },
      });
    } catch (e) {
      // Leave defaults; UI will show unknown
    }
  }, []);

  const fetchIdentity = useCallback(async () => {
    setIdentityLoading(true);
    setIdentityError(null);
    try {
      const data = await apiFetch<any>("/api/identity");
      setIdentityStatus(data.status || null);
      const payload = data.identity || {};
      setIdentity({
        soul: payload.soul || "",
        user: payload.user || "",
        security: payload.security || "",
        tools: payload.tools || "",
        heartbeat: payload.heartbeat || "",
        memory: payload.memory || "",
      });
    } catch (e) {
      setIdentityError(getErrorMessage(e, "Failed to load identity"));
    } finally {
      setIdentityLoading(false);
    }
  }, []);

  const fetchTemplates = useCallback(async () => {
    setTemplateLoading(true);
    setTemplateError(null);
    try {
      const data = await apiFetch<any>("/api/identity/templates");
      setTemplateData(data.templates || {});
    } catch (e) {
      setTemplateError(getErrorMessage(e, "Failed to load templates"));
    } finally {
      setTemplateLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSystemSettings();
    fetchNotificationSettings();
    fetchSecuritySettings();
    fetchMailSettings();
    fetchConnectorStatus();
    fetchIdentity();
  }, [fetchSystemSettings, fetchNotificationSettings, fetchSecuritySettings, fetchMailSettings, fetchConnectorStatus, fetchIdentity]);

  useEffect(() => () => stopQwenPolling(), []);

  useEffect(() => {
    if (llmConfig.authType !== "qwen-oauth") {
      stopQwenPolling();
      setQwenOauth((prev) => ({ ...prev, status: "idle", error: null }));
      clearQwenPending();
    }
  }, [llmConfig.authType]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const raw = window.localStorage.getItem(QWEN_OAUTH_STORAGE_KEY);
    if (!raw) return;
    try {
      const data = JSON.parse(raw);
      const expiresAt = Date.parse(data.expires_at || "");
      if (Number.isFinite(expiresAt) && Date.now() > expiresAt) {
        clearQwenPending();
        return;
      }
      if (data.session_id && data.user_code && data.verification_uri) {
        setQwenOauth({
          status: "pending",
          sessionId: data.session_id,
          userCode: data.user_code,
          verificationUri: data.verification_uri,
          verificationUriComplete: data.verification_uri_complete || "",
          intervalSeconds: data.interval_seconds || 5,
          expiresAt: data.expires_at || "",
          error: null,
        });
        scheduleQwenPoll(data.session_id, data.interval_seconds || 5);
      }
    } catch {
      clearQwenPending();
    }
  }, []);
  
  // Fetch database stats
  useEffect(() => {
    const fetchDbStats = async () => {
      try {
        const data = await apiFetch<any>("/database/stats");
        setDbStats({
          size_formatted: data.size_formatted || "Unknown",
          last_backup: data.last_backup,
        });
      } catch (e) {
        setDbStats({ size_formatted: "Error", last_backup: null });
      }
    };
    fetchDbStats();
  }, []);

  // Fetch data counts for clean slate
  const refreshDataCounts = useCallback(async (silent = true) => {
    try {
      const counts = await apiFetch<any>("/api/data/counts");
      setDataCounts(counts);
    } catch (e) {
      if (!silent) {
        notifications.show({
          title: "Refresh Failed",
          message: getErrorMessage(e, "Unable to refresh counts"),
          color: "red",
        });
      } else if (!isNetworkError(e)) {
        console.error("Failed to fetch data counts:", e);
      }
    }
  }, []);

  const fetchBackups = useCallback(async () => {
    setBackupListLoading(true);
    setBackupListError(null);
    try {
      const data = await apiFetch<any>("/backup/list");
      const backups = data?.backups || [];
      setBackupList(backups);
      if (!backups.length) {
        setBackupListError("No backups found.");
      }
    } catch (e) {
      setBackupListError(getErrorMessage(e, "Could not load backups"));
    } finally {
      setBackupListLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshDataCounts();
  }, [refreshDataCounts]);
  
  // Check inbox sync status on load
  useEffect(() => {
    const checkStatus = async () => {
      try {
        const data = await apiFetch<any>("/inbox/sync-status");
        setInboxEnabled(data.enabled);
      } catch (e) {
        if (!isNetworkError(e)) {
          console.error("Failed to check inbox status:", e);
        }
      }
    };
    checkStatus();
  }, []);

  // Fetch agent context list
  useEffect(() => {
    const fetchContextAgents = async () => {
      setContextAgentsLoading(true);
      setContextAgentsError(null);
      try {
        const data = await api.getAgentsContext();
        const agentsList = data?.agents || [];
        setContextAgents(agentsList);
        if (!selectedContextAgent && agentsList.length > 0) {
          setSelectedContextAgent(agentsList[0].id);
        }
      } catch (e: any) {
        setContextAgentsError(e?.detail || "Failed to load agent context list");
      } finally {
        setContextAgentsLoading(false);
      }
    };
    fetchContextAgents();
  }, []);

  // Fetch selected agent context detail
  useEffect(() => {
    if (!selectedContextAgent) return;
    const fetchContextDetail = async () => {
      setAgentContextLoading(true);
      setAgentContextError(null);
      try {
        const data = await api.getAgentContext(selectedContextAgent);
        setAgentContextDetail(data);
        setContextWindowTokens(data.context_window_tokens);
        setReservedOutputTokens(data.reserved_output_tokens);
        setContextBudgets(data.budgets || {});
      } catch (e: any) {
        setAgentContextError(e?.detail || "Failed to load agent context detail");
      } finally {
        setAgentContextLoading(false);
      }
    };
    fetchContextDetail();
  }, [selectedContextAgent]);
  
  // Handle system toggle (ON/OFF)
  const handleSystemToggle = async () => {
    setSystemLoading(true);
    try {
      if (systemRunning) {
        // SHUTDOWN: Save state + backup
        const data = await apiFetch<any>("/api/system/shutdown", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ agents_enabled: agents, settings })
        });
        
        if (data.success) {
          setSystemRunning(false);
          setLastBackup(data.backup?.timestamp);
          notifications.show({
            title: "🔴 System Stopped",
            message: `State saved & backup created: ${data.backup?.timestamp || "OK"}`,
            color: "orange",
            autoClose: 5000,
          });
        } else {
          throw new Error(data.error || "Shutdown failed");
        }
      } else {
        // STARTUP: Restore state
        const data = await apiFetch<any>("/api/system/startup", {
          method: "POST"
        });
        
        if (data.success) {
          setSystemRunning(true);
          if (data.agents_enabled) {
            setAgents(prev => ({ ...prev, ...data.agents_enabled }));
          }
          if (data.last_backup) {
            setLastBackup(data.last_backup);
          }
          notifications.show({
            title: "🟢 System Online",
            message: data.restored_from 
              ? `Restored from: ${new Date(data.restored_from).toLocaleString()}`
              : "System started successfully",
            color: "green",
            autoClose: 5000,
          });
        } else {
          throw new Error(data.error || "Startup failed");
        }
      }
    } catch (e: any) {
      notifications.show({
        title: "❌ Error",
        message: e.message || "System toggle failed",
        color: "red",
        autoClose: 5000,
      });
    } finally {
      setSystemLoading(false);
    }
  };

  const handleSaveLlmSettings = async () => {
    setLlmSaving(true);
    setLlmError(null);
    setLlmSaved(false);
    try {
      const payload: any = {
        llm_provider: llmConfig.provider,
        llm_base_url: llmConfig.baseUrl,
        llm_model: llmConfig.model,
        llm_auth_type: llmConfig.authType,
      };
      if (llmConfig.authType === "qwen-oauth") {
        const qwen = qwenDefaults();
        payload.llm_provider = qwen.provider;
        payload.llm_base_url = qwen.baseUrl;
        payload.llm_model = qwen.model;
        payload.llm_auth_type = "qwen-oauth";
      }
      if (llmConfig.apiKey.trim()) {
        payload.llm_api_key = llmConfig.apiKey.trim();
      }
      const res = await apiFetch<any>("/api/settings/system", {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      if (res?.settings) {
        const merge = (prev: typeof llmConfig) => ({
          ...prev,
          provider: res.settings.llm_provider ?? prev.provider,
          baseUrl: res.settings.llm_base_url ?? prev.baseUrl,
          model: res.settings.llm_model ?? prev.model,
          apiKeySet: Boolean(res.settings.llm_api_key_set),
          authType: res.settings.llm_auth_type ?? prev.authType,
          oauthConnected: Boolean(res.settings.llm_oauth_connected),
          oauthExpiresAt: res.settings.llm_oauth_expires_at ?? null,
          oauthResourceUrl: res.settings.llm_oauth_resource_url ?? null,
          apiKey: "",
        });
        setLlmActive((prev) => merge(prev));
        setLlmConfig((prev) => merge(prev));
        setLlmRuntime({
          ready: Boolean(res.settings.llm_runtime_ready),
          provider: res.settings.llm_runtime_provider || "",
          model: res.settings.llm_runtime_model || "",
          baseUrl: res.settings.llm_runtime_base_url || "",
          authType: res.settings.llm_runtime_auth_type || "",
          error: res.settings.llm_runtime_error || "",
        });
      } else {
        setLlmConfig((prev) => ({
          ...prev,
          apiKey: "",
          apiKeySet: Boolean(res?.settings?.llm_api_key_set),
        }));
      }
      setLlmSaved(true);
      notifications.show({
        title: "LLM settings saved",
        message: "Qwen connection updated.",
        color: "green",
      });
    } catch (e: any) {
      setLlmError(e?.detail || e?.message || "Failed to save LLM settings");
      notifications.show({
        title: "Save failed",
        message: e?.detail || e?.message || "Failed to save LLM settings",
        color: "red",
      });
    } finally {
      setLlmSaving(false);
    }
  };

  const handleSaveIdentity = async () => {
    setIdentitySaving(true);
    setIdentityError(null);
    try {
      await apiFetch<any>("/api/identity", {
        method: "PUT",
        body: JSON.stringify(identity),
      });
      notifications.show({
        title: "Identity updated",
        message: "Tenant identity files saved.",
        color: "green",
      });
      fetchIdentity();
    } catch (e) {
      const message = getErrorMessage(e, "Failed to save identity");
      setIdentityError(message);
      notifications.show({
        title: "Identity save failed",
        message,
        color: "red",
      });
    } finally {
      setIdentitySaving(false);
    }
  };

  const handleRestoreIdentity = async (scope: "selected" | "all") => {
    const files = scope === "selected" ? [templateFile] : undefined;
    const confirmText =
      scope === "selected"
        ? `Restore ${templateFile.toUpperCase()} from template? This will overwrite your edits.`
        : "Restore ALL identity files from templates? This will overwrite your edits.";
    if (typeof window !== "undefined" && !window.confirm(confirmText)) return;
    setIdentitySaving(true);
    setIdentityError(null);
    try {
      await apiFetch<any>("/api/identity/restore", {
        method: "POST",
        body: JSON.stringify({ files }),
      });
      notifications.show({
        title: "Templates restored",
        message: scope === "selected" ? "Selected file restored." : "All identity files restored.",
        color: "green",
      });
      fetchIdentity();
    } catch (e) {
      const message = getErrorMessage(e, "Failed to restore templates");
      setIdentityError(message);
      notifications.show({
        title: "Restore failed",
        message,
        color: "red",
      });
    } finally {
      setIdentitySaving(false);
    }
  };

  const handleSaveSettings = async () => {
    if (!settingsDirty) return;
    setSettingsSaving(true);
    try {
      await apiFetch<any>("/api/settings/system", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          auto_refresh: settings.autoRefresh,
          monthly_cost_cap: settings.systemCostCap,
          daily_spend_limit: settings.dailySpendLimit,
          approval_threshold: settings.approvalThreshold,
          household_name: settings.householdName,
          timezone: settings.timezone,
        }),
      });

      await apiFetch<any>("/api/settings/notifications", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          in_app: settings.notifications.inApp,
          push: settings.notifications.push,
          email: settings.notifications.email,
          alert_email: settings.notifications.alertEmail,
          whatsapp: settings.notifications.whatsapp,
          urgent_only: settings.notifications.urgentOnly,
          daily_summary: settings.notifications.dailySummary,
          weekly_report: settings.notifications.weeklyReport,
        }),
      });

      await apiFetch<any>("/api/settings/agent/security", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          audit_logging: settings.security.auditLogging,
          threat_monitoring: settings.security.threatMonitoring,
          credential_rotation_days: settings.security.credentialRotationDays,
        }),
      });

      setSavedSettings(JSON.parse(JSON.stringify(settings)));
      notifications.show({
        title: "Settings saved",
        message: "System, notifications, and security settings updated.",
        color: "green",
      });
      if (typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent("mycasa-settings-sync"));
      }
      setShowSaveConfirmation(true);
      setTimeout(() => setShowSaveConfirmation(false), 3000);
    } catch (e) {
      notifications.show({
        title: "Save failed",
        message: getErrorMessage(e, "Could not save settings"),
        color: "red",
      });
    } finally {
      setSettingsSaving(false);
    }
  };

  const handleClearLlmKey = async () => {
    setLlmSaving(true);
    setLlmError(null);
    try {
      const res = await apiFetch<any>("/api/settings/system", {
        method: "PUT",
        body: JSON.stringify({ llm_api_key: "" }),
      });
      if (res?.settings) {
        const merge = (prev: typeof llmConfig) => ({
          ...prev,
          provider: res.settings.llm_provider || prev.provider,
          baseUrl: res.settings.llm_base_url || prev.baseUrl,
          model: res.settings.llm_model || prev.model,
          apiKeySet: Boolean(res.settings.llm_api_key_set),
          authType: res.settings.llm_auth_type || prev.authType,
          oauthConnected: Boolean(res.settings.llm_oauth_connected),
          oauthExpiresAt: res.settings.llm_oauth_expires_at ?? null,
          oauthResourceUrl: res.settings.llm_oauth_resource_url ?? null,
          apiKey: "",
        });
        setLlmActive((prev) => merge(prev));
        setLlmConfig((prev) => merge(prev));
        setLlmRuntime({
          ready: Boolean(res.settings.llm_runtime_ready),
          provider: res.settings.llm_runtime_provider || "",
          model: res.settings.llm_runtime_model || "",
          baseUrl: res.settings.llm_runtime_base_url || "",
          authType: res.settings.llm_runtime_auth_type || "",
          error: res.settings.llm_runtime_error || "",
        });
      } else {
        setLlmConfig((prev) => ({
          ...prev,
          apiKey: "",
          apiKeySet: Boolean(res?.settings?.llm_api_key_set),
        }));
      }
      notifications.show({
        title: "LLM key cleared",
        message: "API key removed.",
        color: "yellow",
      });
    } catch (e: any) {
      setLlmError(e?.detail || e?.message || "Failed to clear API key");
      notifications.show({
        title: "Clear failed",
        message: e?.detail || e?.message || "Failed to clear API key",
        color: "red",
      });
    } finally {
      setLlmSaving(false);
    }
  };

  const stopQwenPolling = () => {
    if (qwenPollRef.current) {
      clearTimeout(qwenPollRef.current);
      qwenPollRef.current = null;
    }
  };

  const clearQwenPending = () => {
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(QWEN_OAUTH_STORAGE_KEY);
    }
  };

  const persistQwenPending = (payload: {
    session_id: string;
    user_code: string;
    verification_uri: string;
    verification_uri_complete?: string;
    interval_seconds: number;
    expires_at: string;
  }) => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(QWEN_OAUTH_STORAGE_KEY, JSON.stringify(payload));
  };

  const scheduleQwenPoll = (sessionId: string, intervalSeconds: number) => {
    stopQwenPolling();
    qwenPollRef.current = setTimeout(async () => {
      try {
        const res = await api.pollQwenOAuth(sessionId);
        if (res.status === "pending") {
          const nextInterval = res.interval_seconds ?? intervalSeconds;
          setQwenOauth((prev) => ({ ...prev, status: "pending", intervalSeconds: nextInterval }));
          scheduleQwenPoll(sessionId, nextInterval);
          return;
        }
        if (res.status === "success") {
          clearQwenPending();
          setQwenOauth((prev) => ({ ...prev, status: "success", error: null }));
          setLlmConfig((prev) => ({
            ...prev,
            authType: "qwen-oauth",
            oauthConnected: true,
            oauthExpiresAt: res.expires_at ?? prev.oauthExpiresAt,
            oauthResourceUrl: res.resource_url ?? prev.oauthResourceUrl,
            provider: "openai-compatible",
            baseUrl: res.resource_url ?? prev.baseUrl,
            model: prev.model?.toLowerCase().startsWith("qwen") ? prev.model : "qwen3-coder-next",
          }));
          setLlmActive((prev) => ({
            ...prev,
            authType: "qwen-oauth",
            oauthConnected: true,
            oauthExpiresAt: res.expires_at ?? prev.oauthExpiresAt,
            oauthResourceUrl: res.resource_url ?? prev.oauthResourceUrl,
            provider: "openai-compatible",
            baseUrl: res.resource_url ?? prev.baseUrl,
            model: prev.model?.toLowerCase().startsWith("qwen") ? prev.model : "qwen3-coder-next",
          }));
          try {
            const latest = await apiFetch<any>("/api/settings/system");
            setLlmRuntime({
              ready: Boolean(latest.llm_runtime_ready),
              provider: latest.llm_runtime_provider || "",
              model: latest.llm_runtime_model || "",
              baseUrl: latest.llm_runtime_base_url || "",
              authType: latest.llm_runtime_auth_type || "",
              error: latest.llm_runtime_error || "",
            });
          } catch {
            // leave runtime as-is
          }
          notifications.show({
            title: "Qwen connected",
            message: "OAuth sign-in complete. Chat is ready.",
            color: "green",
          });
          return;
        }
        if (res.status === "expired") {
          clearQwenPending();
          setQwenOauth((prev) => ({ ...prev, status: "error", error: "Device code expired. Please start again." }));
          return;
        }
        clearQwenPending();
        setQwenOauth((prev) => ({ ...prev, status: "error", error: res.message || "OAuth failed." }));
      } catch (e: any) {
        clearQwenPending();
        setQwenOauth((prev) => ({ ...prev, status: "error", error: e?.detail || e?.message || "OAuth failed." }));
      }
    }, Math.max(2, intervalSeconds) * 1000);
  };

  const handleStartQwenOAuth = async () => {
    stopQwenPolling();
    setQwenOauth({
      status: "starting",
      sessionId: null,
      userCode: "",
      verificationUri: "",
      verificationUriComplete: "",
      intervalSeconds: 5,
      expiresAt: "",
      error: null,
    });
    try {
      const res = await api.startQwenOAuth();
      setQwenOauth({
        status: "pending",
        sessionId: res.session_id,
        userCode: res.user_code,
        verificationUri: res.verification_uri,
        verificationUriComplete: res.verification_uri_complete || "",
        intervalSeconds: res.interval_seconds,
        expiresAt: res.expires_at,
        error: null,
      });
      persistQwenPending(res);
      setLlmConfig((prev) => ({ ...prev, authType: "qwen-oauth" }));
      const targetUrl = res.verification_uri_complete || res.verification_uri;
      if (!targetUrl) {
        throw new Error("Qwen OAuth did not return a verification URL.");
      }
      const opened = window.open(targetUrl, "_blank", "noopener,noreferrer");
      if (!opened) {
        notifications.show({
          title: "Popup blocked",
          message: "Use the “Open sign‑in page” button below to continue.",
          color: "yellow",
        });
      }
      scheduleQwenPoll(res.session_id, res.interval_seconds);
    } catch (e: any) {
      if (isNetworkError(e)) {
        notifications.show({
          title: "Qwen OAuth failed",
          message: "Unable to reach the backend or Qwen auth service. Check your connection and API logs.",
          color: "red",
        });
        setQwenOauth((prev) => ({
          ...prev,
          status: "error",
          error: "Unable to reach the backend or Qwen auth service.",
        }));
        return;
      }
      const detail = e?.detail;
      const message =
        (typeof detail === "string" ? detail : detail?.message) ||
        e?.message ||
        "Failed to start Qwen OAuth.";
      setQwenOauth((prev) => ({
        ...prev,
        status: "error",
        error: message,
      }));
    }
  };

  const handleDisconnectQwenOAuth = async () => {
    stopQwenPolling();
    clearQwenPending();
    try {
      await api.disconnectQwenOAuth();
      setQwenOauth((prev) => ({ ...prev, status: "idle", sessionId: null, userCode: "", error: null }));
      setLlmConfig((prev) => ({
        ...prev,
        authType: "api_key",
        oauthConnected: false,
        oauthExpiresAt: null,
        oauthResourceUrl: null,
      }));
      setLlmActive((prev) => ({
        ...prev,
        authType: "api_key",
        oauthConnected: false,
        oauthExpiresAt: null,
        oauthResourceUrl: null,
      }));
      setLlmRuntime((prev) => ({
        ...prev,
        ready: false,
      }));
      notifications.show({
        title: "Qwen disconnected",
        message: "OAuth tokens cleared.",
        color: "yellow",
      });
    } catch (e: any) {
      notifications.show({
        title: "Disconnect failed",
        message: e?.detail || e?.message || "Unable to disconnect Qwen OAuth.",
        color: "red",
      });
    }
  };

  const toggleAgent = async (agentId: string) => {
    const currentEnabled = agents[agentId];
    setAgentToggling(agentId);
    try {
      const endpoint = currentEnabled
        ? `/personas/${agentId}/disable`
        : `/personas/${agentId}/enable`;

      await apiFetch<any>(endpoint, { method: "PATCH" });
      setAgents(prev => ({ ...prev, [agentId]: !currentEnabled }));
      notifications.show({
        title: currentEnabled ? "Agent Disabled" : "Agent Enabled",
        message: `${agentId} has been ${currentEnabled ? "disabled" : "enabled"}`,
        color: currentEnabled ? "orange" : "green",
        autoClose: 2000,
      });
    } catch (e) {
      notifications.show({
        title: "Error",
        message: getErrorMessage(e, "Could not toggle agent"),
        color: "red",
      });
    } finally {
      setAgentToggling(null);
    }
  };

  const updateMailSetting = async (patch: Partial<typeof mailSettings>) => {
    setMailSettingsSaving(true);
    setMailSettingsError(null);
    try {
      const res = await apiFetch<any>("/api/settings/agent/mail", {
        method: "PUT",
        body: JSON.stringify({
          allow_agent_replies: patch.allowAgentReplies ?? mailSettings.allowAgentReplies,
          allow_whatsapp_replies: patch.allowWhatsappReplies ?? mailSettings.allowWhatsappReplies,
          allow_email_replies: patch.allowEmailReplies ?? mailSettings.allowEmailReplies,
          gmail_enabled: patch.gmailEnabled ?? mailSettings.gmailEnabled,
          whatsapp_enabled: patch.whatsappEnabled ?? mailSettings.whatsappEnabled,
        }),
      });
      if (res?.settings) {
        setMailSettings({
          allowAgentReplies: Boolean(res.settings.allow_agent_replies),
          allowWhatsappReplies: Boolean(res.settings.allow_whatsapp_replies),
          allowEmailReplies: Boolean(res.settings.allow_email_replies),
          gmailEnabled: Boolean(res.settings.gmail_enabled),
          whatsappEnabled: Boolean(res.settings.whatsapp_enabled),
        });
      } else {
        setMailSettings((prev) => ({ ...prev, ...patch }));
      }
      notifications.show({
        title: "Inbox settings updated",
        message: "Reply controls saved.",
        color: "green",
        autoClose: 2000,
      });
    } catch (e) {
      setMailSettingsError(getErrorMessage(e, "Failed to update inbox reply settings"));
      notifications.show({
        title: "Update failed",
        message: getErrorMessage(e, "Failed to update inbox reply settings"),
        color: "red",
      });
    } finally {
      setMailSettingsSaving(false);
    }
  };

  const handleContextSave = async () => {
    if (!selectedContextAgent) return;
    setContextSaving(true);
    setAgentContextError(null);
    try {
      if (reservedOutputTokens >= contextWindowTokens) {
        throw new Error("reserved_output_tokens must be less than context_window_tokens");
      }
      await api.updateAgentContext(selectedContextAgent, {
        context_window_tokens: contextWindowTokens,
        reserved_output_tokens: reservedOutputTokens,
        budgets_json: contextBudgets,
      });
      const data = await api.getAgentContext(selectedContextAgent);
      setAgentContextDetail(data);
      setContextWindowTokens(data.context_window_tokens);
      setReservedOutputTokens(data.reserved_output_tokens);
      setContextBudgets(data.budgets || {});
    } catch (e: any) {
      setAgentContextError(e?.detail || e?.message || "Failed to update context");
    } finally {
      setContextSaving(false);
    }
  };

  const handleContextSimulate = async () => {
    if (!selectedContextAgent) return;
    setSimulateState("loading");
    setSimulateResult(null);
    try {
      const lastRun = agentContextDetail?.last_run;
      const included = lastRun?.included_summary || {};
      const result = await api.simulateAgentContext(selectedContextAgent, {
        context_window_tokens: contextWindowTokens,
        reserved_output_tokens: reservedOutputTokens,
        budgets_json: contextBudgets,
        component_tokens: lastRun?.component_tokens || {},
        history_token_counts: included?.history?.token_counts || [],
        retrieval_token_counts: included?.retrieval?.token_counts || [],
        tool_result_token_counts: included?.tool_results?.token_counts || [],
        retrieval_header_tokens: included?.retrieval?.header_tokens || 0,
        tool_header_tokens: included?.tool_results?.header_tokens || 0,
        user_tokens: included?.user_message?.tokens || lastRun?.component_tokens?.other || 0,
      });
      setSimulateResult(result);
      setSimulateState("idle");
    } catch (e: any) {
      setSimulateState("error");
      setSimulateResult({ error: e?.detail || "Simulation failed" });
    }
  };

  // Helper to format backup timestamp (20260128_215532 -> Jan 28, 2026 9:55 PM)
  const formatBackupTimestamp = (ts: string | null): string => {
    if (!ts) return "Never";
    try {
      // Parse format: YYYYMMDD_HHMMSS
      const match = ts.match(/(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})/);
      if (match) {
        const [, year, month, day, hour, min, sec] = match;
        const date = new Date(
          parseInt(year), parseInt(month) - 1, parseInt(day),
          parseInt(hour), parseInt(min), parseInt(sec)
        );
        return date.toLocaleString();
      }
      return ts;
    } catch {
      return ts;
    }
  };

  const handleLaunch = () => {
    setShowLaunchModal(true);
  };

  const handleLaunchComplete = (success: boolean) => {
    setShowLaunchModal(false);
    if (success) {
      notifications.show({
        title: "✅ System Online",
        message: "System started successfully",
        color: "green",
        autoClose: 3000,
      });
      // Force a page refresh to update status
      window.location.reload();
    } else {
      notifications.show({
        title: "❌ Launch Failed",
        message: "Check backend connection and try again",
        color: "red",
        autoClose: 5000,
      });
    }
  };
  
  const handleInboxLaunch = async () => {
    setInboxLaunching(true);
    setInboxStatus(null);
    try {
      const data = await apiFetch<any>("/api/inbox/launch", { method: "POST" });
      if (data.success) {
        setInboxEnabled(true);
        setInboxStatus(`Synced: ${data.gmail || 0} emails, ${data.whatsapp || 0} WhatsApp messages`);
      } else {
        setInboxStatus("Failed to launch inbox sync");
      }
    } catch (e) {
      setInboxStatus(getErrorMessage(e, "Error connecting to backend"));
    } finally {
      setInboxLaunching(false);
    }
  };
  
  const handleInboxStop = async () => {
    try {
      await apiFetch<any>("/api/inbox/stop", { method: "POST" });
      setInboxEnabled(false);
      setInboxStatus("Inbox sync stopped");
    } catch (e) {
      setInboxStatus(getErrorMessage(e, "Error stopping sync"));
    }
  };

  const lastContextRun = agentContextDetail?.last_run;
  const lastContextStatus = lastContextRun?.status || "never";
  const lastContextStatusColor =
    lastContextStatus === "blocked" ? "red" : lastContextStatus === "trimmed" ? "yellow" : "green";

  return (
    <Shell>
      <Page title="Settings" subtitle="Configuration & preferences">
      <LaunchModal 
        opened={showLaunchModal} 
        onClose={() => setShowLaunchModal(false)}
        onComplete={handleLaunchComplete}
      />
      <Modal
        opened={backupModalOpen}
        onClose={() => setBackupModalOpen(false)}
        title="Import Backup"
        size="lg"
      >
        <Stack gap="md">
          <Group justify="space-between">
            <Text size="sm" c="dimmed">
              Select a backup to restore. This will overwrite current data.
            </Text>
            <Button size="xs" variant="light" onClick={fetchBackups} loading={backupListLoading}>
              Refresh
            </Button>
          </Group>

          {backupListLoading && (
            <Group gap="xs">
              <Loader size="sm" />
              <Text size="sm">Loading backups…</Text>
            </Group>
          )}

          {!backupListLoading && backupListError && (
            <Alert color="red" variant="light" title="Backup list unavailable">
              {backupListError}
            </Alert>
          )}

          {!backupListLoading && !backupListError && (
            backupList.length > 0 ? (
              <Table striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Backup</Table.Th>
                    <Table.Th>Created</Table.Th>
                    <Table.Th>Size</Table.Th>
                    <Table.Th />
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {backupList.map((backup) => (
                    <Table.Tr key={backup.name}>
                      <Table.Td>
                        <Text size="sm" fw={600}>{backup.name}</Text>
                        <Text size="xs" c="dimmed">{backup.path}</Text>
                      </Table.Td>
                      <Table.Td>
                        <Text size="sm">
                          {backup.timestamp
                            ? new Date(backup.timestamp).toLocaleString()
                            : "Unknown"}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <Text size="sm">{formatBytes(backup.size_bytes)}</Text>
                      </Table.Td>
                      <Table.Td>
                        <Button
                          size="xs"
                          color="red"
                          variant="light"
                          loading={backupRestoring === backup.name}
                          onClick={async () => {
                            if (!confirm(`Restore backup ${backup.name}? This will overwrite current data.`)) return;
                            setBackupRestoring(backup.name);
                            try {
                              const result = await apiFetch<any>(`/backup/restore/${backup.name}`, { method: "POST" });
                              if (result?.success === false) {
                                throw new Error(result?.error || "Restore failed");
                              }
                              notifications.show({
                                title: "Backup restored",
                                message: "Data restored. Reloading the page.",
                                color: "green",
                              });
                              setBackupModalOpen(false);
                              setTimeout(() => window.location.reload(), 800);
                            } catch (e) {
                              notifications.show({
                                title: "Restore failed",
                                message: getErrorMessage(e, "Could not restore backup"),
                                color: "red",
                              });
                            } finally {
                              setBackupRestoring(null);
                            }
                          }}
                        >
                          Restore
                        </Button>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            ) : (
              <Text size="sm" c="dimmed">
                No backups found.
              </Text>
            )
          )}
        </Stack>
      </Modal>
      <Modal
        opened={templateModalOpen}
        onClose={() => setTemplateModalOpen(false)}
        title="Template comparison"
        size="xl"
      >
        <Stack gap="md">
          {templateLoading && (
            <Group gap="xs">
              <Loader size="sm" />
              <Text size="sm">Loading templates…</Text>
            </Group>
          )}
          {templateError && (
            <Alert color="red">{templateError}</Alert>
          )}
          <SimpleGrid cols={{ base: 1, md: 2 }}>
            <Textarea
              label={`Current ${templateFile.toUpperCase()}.md`}
              value={(identity as any)[templateFile] || ""}
              minRows={12}
              readOnly
            />
            <Textarea
              label={`Template ${templateFile.toUpperCase()}.md`}
              value={templateData[templateFile] || ""}
              minRows={12}
              readOnly
            />
          </SimpleGrid>
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setTemplateModalOpen(false)}>
              Close
            </Button>
            <Button color="red" variant="light" onClick={() => handleRestoreIdentity("selected")}>
              Restore selected
            </Button>
          </Group>
        </Stack>
      </Modal>
      <Stack gap="md" className="settings-page">
        {/* Header */}
        <Group justify="space-between" className="settings-header">
          <div>
            <Text fw={600}>System status</Text>
            <Text size="xs" c="dimmed">
              Backend connection and runtime state
            </Text>
          </div>
          <Group gap="md">
            {/* Backend Status */}
            <Badge 
              size="lg" 
              variant="dot" 
              color={backendConnected === null ? "gray" : backendConnected ? "blue" : "red"}
            >
              {backendConnected === null ? "Connecting..." : backendConnected ? "Backend Connected" : "Backend Offline"}
            </Badge>
            
            {/* System Status Badge */}
            <Badge 
              size="lg" 
              variant="dot" 
              color={systemRunning ? "green" : "gray"}
            >
              {systemRunning ? "System Online" : "System Offline"}
            </Badge>
            
            {/* System ON/OFF Button */}
            <Button 
              leftSection={systemRunning ? <IconShield size={18} /> : <IconRocket size={18} />} 
              size="md"
              onClick={handleSystemToggle}
              loading={systemLoading}
              disabled={!backendConnected}
              variant={systemRunning ? "light" : "gradient"}
              color={systemRunning ? "red" : undefined}
              gradient={systemRunning ? undefined : { from: "indigo", to: "violet" }}
            >
              {systemRunning ? "Turn Off System" : "Turn On System"}
            </Button>
          </Group>
        </Group>
        
        {/* Backend Offline Warning */}
        {backendConnected === false && (
          <Alert icon={<IconAlertCircle size={16} />} color="red" title="Backend offline">
            <Stack gap={6}>
              <Text size="sm">
                We can’t reach the API at <Code>{apiBase}</Code>. Start the backend and retry.
              </Text>
              <Group gap="xs" wrap="wrap">
                <Code>MYCASA_API_PORT=6709 ./start_all.sh</Code>
                <Button
                  size="xs"
                  variant="light"
                  color="red"
                  leftSection={<IconRefresh size={14} />}
                  onClick={refreshSystemStatus}
                >
                  Retry
                </Button>
              </Group>
            </Stack>
          </Alert>
        )}
        
        {/* Last Backup Info */}
        {lastBackup && backendConnected && (
          <Alert icon={<IconDatabase size={16} />} color="blue" variant="light">
            Last backup: {formatBackupTimestamp(lastBackup)}
            {lastShutdown && ` • Last shutdown: ${new Date(lastShutdown).toLocaleString()}`}
          </Alert>
        )}

        <Tabs value={activeTab} onChange={handleTabChange} orientation="vertical" style={{ minHeight: 600 }} className="settings-tabs">
          <Tabs.List style={{ width: 200 }} className="settings-tabs-list">
            <Tabs.Tab value="general" leftSection={<IconSettings size={16} />}>
              General
            </Tabs.Tab>
            <Tabs.Tab value="identity" leftSection={<IconHome size={16} />}>
              Identity
            </Tabs.Tab>
            <Tabs.Tab value="agents" leftSection={<IconCpu size={16} />}>
              Agents
            </Tabs.Tab>
            <Tabs.Tab value="connectors" leftSection={<IconKey size={16} />}>
              Connectors
            </Tabs.Tab>
            <Tabs.Tab value="notifications" leftSection={<IconBell size={16} />}>
              Notifications
            </Tabs.Tab>
            <Tabs.Tab value="security" leftSection={<IconShield size={16} />}>
              Security
            </Tabs.Tab>
            <Tabs.Tab value="data" leftSection={<IconDatabase size={16} />}>
              Data
            </Tabs.Tab>
            <Tabs.Tab value="dashboard" leftSection={<IconLayout size={16} />}>
              Dashboard
            </Tabs.Tab>
          </Tabs.List>

          {/* GENERAL TAB */}
          <Tabs.Panel value="general" pl="md" style={{ flex: 1 }}>
            <Stack gap="md">
              <Card withBorder p="lg" radius="md">
                <Text fw={600} mb="md">System Settings</Text>
                <Stack gap="md">
                  <Group justify="space-between">
                    <div>
                      <Text size="sm">Auto-refresh Dashboard</Text>
                      <Text size="xs" c="dimmed">Update widgets every 30 seconds</Text>
                    </div>
                    <Switch 
                      checked={settings.autoRefresh} 
                      onChange={() => setSettings(s => ({...s, autoRefresh: !s.autoRefresh}))}
                    />
                  </Group>
                  <Divider />
                  <Group justify="space-between" align="flex-start">
                    <div>
                      <Text size="sm">Monthly System Cost Cap</Text>
                      <Text size="xs" c="dimmed">Alert when model API costs approach limit</Text>
                    </div>
                    <NumberInput 
                      value={settings.systemCostCap}
                      onChange={(v) => setSettings(s => ({...s, systemCostCap: Number(v)}))}
                      prefix="$"
                      w={120}
                      size="sm"
                    />
                  </Group>
                  <Divider />
                  <Group justify="space-between" align="flex-start">
                    <div>
                      <Text size="sm">Daily Spend Limit</Text>
                      <Text size="xs" c="dimmed">Daily cap for automated spending actions</Text>
                    </div>
                    <NumberInput
                      value={settings.dailySpendLimit}
                      onChange={(v) => setSettings(s => ({...s, dailySpendLimit: Number(v)}))}
                      prefix="$"
                      w={120}
                      size="sm"
                    />
                  </Group>
                  <Divider />
                  <Group justify="space-between" align="flex-start">
                    <div>
                      <Text size="sm">Approval Threshold</Text>
                      <Text size="xs" c="dimmed">Require approval for costs above this amount</Text>
                    </div>
                    <NumberInput 
                      value={settings.approvalThreshold}
                      onChange={(v) => setSettings(s => ({...s, approvalThreshold: Number(v)}))}
                      prefix="$"
                      w={120}
                      size="sm"
                    />
                  </Group>
                </Stack>
              </Card>

              <Card withBorder p="lg" radius="md">
                <Group justify="space-between" mb="md" align="flex-start">
                  <div>
                  <Group justify="space-between" align="flex-start">
                    <div>
                      <Text fw={600}>LLM Provider</Text>
                      <Text size="xs" c="dimmed">
                        Active runtime config from the backend. Draft changes apply after you save.
                      </Text>
                    </div>
                    <Badge
                      color={llmActive.authType === "qwen-oauth" ? (llmActive.oauthConnected ? "green" : "yellow") : (llmActive.apiKeySet ? "green" : "yellow")}
                      variant="light"
                    >
                      {llmActive.authType === "qwen-oauth"
                        ? (llmActive.oauthConnected ? "Qwen OAuth connected" : "Qwen OAuth not connected")
                        : (llmActive.apiKeySet ? "API key connected" : "API key not connected")}
                    </Badge>
                  </Group>
                  <Group gap="xs" mt="xs">
                    <Badge color="blue" variant="light">
                      Provider: {llmActive.provider || "not set"}
                    </Badge>
                    <Badge color="gray" variant="light">
                      Model: {llmActive.model || "default"}
                    </Badge>
                    <Badge color="gray" variant="light">
                      Base URL: {llmActive.baseUrl || "not set"}
                    </Badge>
                    <Tooltip
                      label={
                        llmRuntime.ready
                          ? `Runtime ready • ${llmRuntime.provider || "unknown"} • ${llmRuntime.model || "default"}`
                          : llmRuntime.error || "Runtime not initialized"
                      }
                    >
                      <Badge color={llmRuntime.ready ? "green" : "red"} variant="light">
                        Runtime: {llmRuntime.ready ? "Ready" : "Not ready"}
                      </Badge>
                    </Tooltip>
                    {llmDirty && (
                      <Badge color="yellow" variant="light">
                        Unsaved changes
                      </Badge>
                    )}
                  </Group>
                  </div>
                  <Badge color="violet" variant="light">Model Core</Badge>
                </Group>
                <Stack gap="sm">
                  <SegmentedControl
                    fullWidth
                    value={llmConfig.authType}
                    onChange={(value) =>
                      setLlmConfig((s) => {
                        const nextAuth = value as "api_key" | "qwen-oauth";
                        if (nextAuth === "qwen-oauth") {
                          const qwen = qwenDefaults();
                          return {
                            ...s,
                            authType: nextAuth,
                            provider: qwen.provider,
                            baseUrl: qwen.baseUrl,
                            model: qwen.model,
                          };
                        }
                        const defaults = providerDefaults(s.provider || "openai");
                        return {
                          ...s,
                          authType: nextAuth,
                          baseUrl: s.baseUrl || defaults.baseUrl,
                          model: s.model || defaults.model,
                        };
                      })
                    }
                    data={[
                      { value: "qwen-oauth", label: "Qwen OAuth" },
                      { value: "api_key", label: "API Key" },
                    ]}
                  />
                  <Select
                    label="Provider"
                    data={[
                      { value: "openai-compatible", label: "OpenAI-compatible (Qwen/Venice)" },
                      { value: "openai", label: "OpenAI" },
                      { value: "anthropic", label: "Anthropic" },
                    ]}
                    value={llmConfig.provider}
                    onChange={(v) =>
                      v &&
                      setLlmConfig((s) => {
                        const defaults = providerDefaults(v);
                        return {
                          ...s,
                          provider: v,
                          authType: v === "openai-compatible" ? s.authType : "api_key",
                          baseUrl: defaults.baseUrl,
                          model: defaults.model,
                        };
                      })
                    }
                    disabled={llmConfig.authType === "qwen-oauth"}
                  />
                  <TextInput
                    label="Base URL"
                    placeholder="https://api.venice.ai/api/v1"
                    value={llmConfig.baseUrl}
                    onChange={(e) => setLlmConfig((s) => ({ ...s, baseUrl: readInputValue(e) }))}
                    disabled={
                      (llmConfig.authType === "qwen-oauth" && llmConfig.oauthConnected) ||
                      llmConfig.provider === "anthropic"
                    }
                  />
                  <TextInput
                    label="Model"
                    placeholder="qwen3-coder-next"
                    value={llmConfig.model}
                    onChange={(e) => setLlmConfig((s) => ({ ...s, model: readInputValue(e) }))}
                  />
                  {llmConfig.authType === "api_key" && (
                    <PasswordInput
                      label="API Key"
                      placeholder={llmConfig.apiKeySet ? "Key stored" : "Enter API key"}
                      value={llmConfig.apiKey}
                      onChange={(e) => setLlmConfig((s) => ({ ...s, apiKey: readInputValue(e) }))}
                      description={llmConfig.apiKeySet ? "A key is already saved. Enter a new one to replace it." : undefined}
                    />
                  )}

                  {llmConfig.authType === "qwen-oauth" && (
                    <Stack gap="xs">
                      <Group justify="space-between">
                        <Group gap="xs">
                          <Badge color={llmActive.oauthConnected ? "green" : "yellow"} variant="light">
                            {llmActive.oauthConnected ? "Connected" : "Not connected"}
                          </Badge>
                          {llmActive.oauthConnected && llmActive.oauthExpiresAt && (
                            <Text size="xs" c="dimmed">
                              Expires {new Date(llmActive.oauthExpiresAt).toLocaleString()}
                            </Text>
                          )}
                        </Group>
                        {llmActive.oauthConnected ? (
                          <Button size="xs" variant="subtle" color="red" onClick={handleDisconnectQwenOAuth}>
                            Disconnect
                          </Button>
                        ) : (
                          <Button size="xs" loading={qwenOauth.status === "starting"} onClick={handleStartQwenOAuth}>
                            Connect Qwen
                          </Button>
                        )}
                      </Group>

                      {qwenOauth.status === "pending" && (
                        <Alert color="blue" variant="light">
                          <Stack gap={6}>
                            <Text size="sm">
                              Complete Qwen sign‑in in your browser, then return here.
                            </Text>
                            <Group gap="xs">
                              <Code>{qwenOauth.userCode}</Code>
                              <CopyButton value={qwenOauth.userCode}>
                                {({ copied, copy }) => (
                                  <ActionIcon variant="light" color={copied ? "green" : "gray"} onClick={copy}>
                                    <IconCopy size={14} />
                                  </ActionIcon>
                                )}
                              </CopyButton>
                              <Button
                                size="xs"
                                variant="light"
                                leftSection={<IconExternalLink size={14} />}
                                onClick={() => {
                                  const url = qwenOauth.verificationUriComplete || qwenOauth.verificationUri;
                                  if (url) window.open(url, "_blank", "noopener,noreferrer");
                                }}
                              >
                                Open sign‑in page
                              </Button>
                            </Group>
                            {qwenOauth.expiresAt && (
                              <Text size="xs" c="dimmed">
                                Code expires {new Date(qwenOauth.expiresAt).toLocaleString()}
                              </Text>
                            )}
                          </Stack>
                        </Alert>
                      )}

                      {qwenOauth.status === "error" && qwenOauth.error && (
                        <Alert color="red" variant="light">
                          {qwenOauth.error}
                        </Alert>
                      )}
                    </Stack>
                  )}
                  {llmError && (
                    <Text size="xs" c="red">
                      {llmError}
                    </Text>
                  )}
                  <Group gap="sm">
                    <Button size="sm" loading={llmSaving} onClick={handleSaveLlmSettings}>
                      Save LLM Settings
                    </Button>
                    <Button
                      size="sm"
                      variant="subtle"
                      color="red"
                      disabled={llmConfig.authType !== "api_key" || !llmConfig.apiKeySet || llmSaving}
                      onClick={handleClearLlmKey}
                    >
                      Clear API Key
                    </Button>
                    {llmSaved && (
                      <Text size="xs" c="green">
                        Saved
                      </Text>
                    )}
                  </Group>
                </Stack>
              </Card>

              <Card withBorder p="lg" radius="md">
                <Text fw={600} mb="md">Household</Text>
                <Stack gap="sm">
                  <TextInput
                    label="Household Name"
                    placeholder="Tenkiang Residence"
                    value={settings.householdName}
                    onChange={(e) => setSettings((prev) => ({ ...prev, householdName: readInputValue(e) }))}
                  />
                  <Select 
                    label="Timezone" 
                    placeholder="Select timezone"
                    data={[
                      { value: "America/Los_Angeles", label: "Pacific Time (PT)" },
                      { value: "America/New_York", label: "Eastern Time (ET)" },
                      { value: "America/Chicago", label: "Central Time (CT)" },
                    ]}
                    value={settings.timezone}
                    onChange={(value) =>
                      setSettings((prev) => ({ ...prev, timezone: value || prev.timezone }))
                    }
                  />
                </Stack>
              </Card>

              <Card withBorder p="lg" radius="md">
                <Group justify="space-between" mb="md">
                  <div>
                    <Text fw={600}>💰 Investment Goals</Text>
                    <Text size="xs" c="dimmed">Finance agent uses these to guide recommendations</Text>
                  </div>
                  <Badge color="teal" variant="light">Finance Agent</Badge>
                </Group>
                <Stack gap="md">
                  <Select 
                    label="Investment Style"
                    description="How aggressively should the agent manage your portfolio?"
                    data={[
                      { value: "conservative", label: "Conservative - Preserve capital, low risk" },
                      { value: "moderate", label: "Moderate - Balanced growth and safety" },
                      { value: "aggressive", label: "Aggressive - Maximum growth, higher risk" },
                      { value: "speculative", label: "Speculative - High risk/high reward" },
                    ]}
                    defaultValue="moderate"
                  />
                  <NumberInput 
                    label="Target Annual Return (%)"
                    description="Your expected yearly portfolio growth"
                    placeholder="12"
                    suffix="%"
                    min={1}
                    max={50}
                    defaultValue={12}
                  />
                  <NumberInput 
                    label="Max Single Position (%)"
                    description="Maximum % of portfolio in one stock"
                    placeholder="15"
                    suffix="%"
                    min={5}
                    max={50}
                    defaultValue={15}
                  />
                  <Select 
                    label="Focus Sectors"
                    description="Industries you want to prioritize"
                    data={[
                      { value: "tech", label: "Technology & Automation" },
                      { value: "dividend", label: "Dividend & Income" },
                      { value: "growth", label: "High Growth" },
                      { value: "value", label: "Value Investing" },
                      { value: "balanced", label: "Balanced / Diversified" },
                    ]}
                    defaultValue="balanced"
                  />
                  <Textarea 
                    label="Investment Notes"
                    description="Any specific goals or constraints for the Finance agent"
                    placeholder="e.g., Building retirement fund, saving for college, want exposure to the technology sector..."
                    minRows={3}
                  />
                  <Divider my="xs" />
                  <Text size="sm" fw={500}>Alerts & Recommendations</Text>
                  <SimpleGrid cols={2}>
                    <Switch 
                      label="Rebalancing alerts"
                      description="When positions drift from targets"
                      defaultChecked
                    />
                    <Switch 
                      label="Buy recommendations"
                      description="Suggest new positions"
                      defaultChecked
                    />
                    <Switch 
                      label="Sell alerts"
                      description="When to trim or exit"
                      defaultChecked
                    />
                    <Switch 
                      label="Earnings warnings"
                      description="Before company reports"
                      defaultChecked
                    />
                  </SimpleGrid>
                </Stack>
              </Card>
            </Stack>
          </Tabs.Panel>

          {/* IDENTITY TAB */}
          <Tabs.Panel value="identity" pl="md" style={{ flex: 1 }}>
            <Stack gap="md">
              <Card withBorder p="lg" radius="md">
                <Group justify="space-between" align="flex-start">
                  <div>
                    <Text fw={600}>Tenant Identity</Text>
                    <Text size="xs" c="dimmed">
                      These files define who Galidima is, who it serves, and the household context.
                    </Text>
                  </div>
                  <Badge color={identityStatus?.ready ? "green" : "yellow"} variant="light">
                    {identityStatus?.ready ? "Ready" : "Missing required files"}
                  </Badge>
                </Group>
                {identityStatus?.missing_required?.length > 0 && (
                  <Text size="xs" c="dimmed" mt="sm">
                    Missing: {identityStatus.missing_required.join(", ")}
                  </Text>
                )}
                {identityLoading && (
                  <Group gap="xs" mt="sm">
                    <Loader size="sm" />
                    <Text size="xs" c="dimmed">Loading identity files...</Text>
                  </Group>
                )}
                {identityError && (
                  <Alert color="red" mt="sm">
                    {identityError}
                  </Alert>
                )}
              </Card>

              <Card withBorder p="lg" radius="md">
                <Stack gap="sm">
                  <Group justify="space-between" align="flex-end">
                    <Select
                      label="Template file"
                      data={[
                        { value: "soul", label: "SOUL.md" },
                        { value: "user", label: "USER.md" },
                        { value: "security", label: "SECURITY.md" },
                        { value: "tools", label: "TOOLS.md" },
                        { value: "heartbeat", label: "HEARTBEAT.md" },
                        { value: "memory", label: "MEMORY.md" },
                      ]}
                      value={templateFile}
                      onChange={(value) => setTemplateFile(value || "soul")}
                      w={220}
                    />
                    <Group gap="xs">
                      <Button
                        variant="light"
                        onClick={async () => {
                          if (!Object.keys(templateData).length) {
                            await fetchTemplates();
                          }
                          setTemplateModalOpen(true);
                        }}
                        disabled={templateLoading}
                      >
                        Compare to template
                      </Button>
                      <Button variant="default" onClick={() => handleRestoreIdentity("selected")}>
                        Restore selected
                      </Button>
                      <Button color="red" variant="light" onClick={() => handleRestoreIdentity("all")}>
                        Restore all
                      </Button>
                    </Group>
                  </Group>
                  <Textarea
                    label="SOUL.md"
                    description="Persona, principles, and voice"
                    minRows={4}
                    value={identity.soul}
                    onChange={(e) => setIdentity((prev) => ({ ...prev, soul: readInputValue(e) }))}
                  />
                  <Textarea
                    label="USER.md"
                    description="Who the system serves"
                    minRows={4}
                    value={identity.user}
                    onChange={(e) => setIdentity((prev) => ({ ...prev, user: readInputValue(e) }))}
                  />
                  <Textarea
                    label="SECURITY.md"
                    description="Trust boundaries and privacy rules"
                    minRows={4}
                    value={identity.security}
                    onChange={(e) => setIdentity((prev) => ({ ...prev, security: readInputValue(e) }))}
                  />
                  <Textarea
                    label="TOOLS.md"
                    description="Household specifics, contacts, preferences"
                    minRows={4}
                    value={identity.tools}
                    onChange={(e) => setIdentity((prev) => ({ ...prev, tools: readInputValue(e) }))}
                  />
                  <Textarea
                    label="HEARTBEAT.md"
                    description="Proactive checklist for Galidima"
                    minRows={4}
                    value={identity.heartbeat}
                    onChange={(e) => setIdentity((prev) => ({ ...prev, heartbeat: readInputValue(e) }))}
                  />
                  <Textarea
                    label="MEMORY.md"
                    description="Curated long-term memory"
                    minRows={4}
                    value={identity.memory}
                    onChange={(e) => setIdentity((prev) => ({ ...prev, memory: readInputValue(e) }))}
                  />
                </Stack>
                <Group justify="flex-end" mt="md">
                  <Button variant="default" onClick={fetchIdentity} disabled={identityLoading}>
                    Reload
                  </Button>
                  <Button onClick={handleSaveIdentity} loading={identitySaving}>
                    Save Identity
                  </Button>
                </Group>
              </Card>
            </Stack>
          </Tabs.Panel>

          {/* AGENTS TAB */}
          <Tabs.Panel value="agents" pl="md" style={{ flex: 1 }}>
            <Tabs defaultValue="roster">
              <Tabs.List>
                <Tabs.Tab value="roster" leftSection={<IconCpu size={14} />}>Roster</Tabs.Tab>
                <Tabs.Tab value="context" leftSection={<IconChecklist size={14} />}>Context</Tabs.Tab>
              </Tabs.List>

              <Tabs.Panel value="roster" pt="md">
                <Stack gap="md">
                  <Alert icon={<IconAlertCircle size={16} />} color="blue">
                    Enable or disable agents. Disabled agents will not process tasks.
                  </Alert>

                  <SimpleGrid cols={{ base: 1, md: 2 }}>
                    <AgentConfigCard
                      name="Finance Manager (Mamadou)"
                      icon={IconCoin}
                      color="green"
                      enabled={agents.finance}
                      onToggle={() => toggleAgent("finance")}
                      loading={agentToggling === "finance"}
                    >
                      <Stack gap="xs">
                        <NumberInput
                          label="Daily Spend Limit"
                          prefix="$"
                          defaultValue={350}
                          size="xs"
                        />
                        <NumberInput
                          label="Monthly Budget"
                          prefix="$"
                          defaultValue={10000}
                          size="xs"
                        />
                      </Stack>
                    </AgentConfigCard>

                    <AgentConfigCard
                      name="Maintenance Agent (Ousmane)"
                      icon={IconTool}
                      color="blue"
                      enabled={agents.maintenance}
                      onToggle={() => toggleAgent("maintenance")}
                      loading={agentToggling === "maintenance"}
                    >
                      <Checkbox
                        label="Auto-schedule recurring tasks"
                        size="xs"
                        defaultChecked
                      />
                    </AgentConfigCard>

                    <AgentConfigCard
                      name="Contractors Agent (Malik)"
                      icon={IconUsers}
                      color="orange"
                      enabled={agents.contractors}
                      onToggle={() => toggleAgent("contractors")}
                      loading={agentToggling === "contractors"}
                    />

                    <AgentConfigCard
                      name="Projects Agent (Zainab)"
                      icon={IconFolders}
                      color="violet"
                      enabled={agents.projects}
                      onToggle={() => toggleAgent("projects")}
                      loading={agentToggling === "projects"}
                    />

                    <AgentConfigCard
                      name="Security Manager (Aicha)"
                      icon={IconShield}
                      color="red"
                      enabled={agents["security-manager"]}
                      onToggle={() => toggleAgent("security-manager")}
                      loading={agentToggling === "security-manager"}
                    >
                      <Checkbox
                        label="Enable threat monitoring"
                        size="xs"
                        defaultChecked
                      />
                    </AgentConfigCard>

                    <AgentConfigCard
                      name="Janitor (Sule)"
                      icon={IconDatabase}
                      color="gray"
                      enabled={agents.janitor}
                      onToggle={() => toggleAgent("janitor")}
                      loading={agentToggling === "janitor"}
                    />

                    <AgentConfigCard
                      name="Backup & Recovery"
                      icon={IconRefresh}
                      color="cyan"
                      enabled={agents["backup-recovery"]}
                      onToggle={() => toggleAgent("backup-recovery")}
                      loading={agentToggling === "backup-recovery"}
                    >
                      <Select
                        label="Backup Frequency"
                        data={["Daily", "Weekly", "Monthly"]}
                        defaultValue="Daily"
                        size="xs"
                      />
                    </AgentConfigCard>
                  </SimpleGrid>
                </Stack>
              </Tabs.Panel>

              <Tabs.Panel value="context" pt="md">
                <Stack gap="md">
                  {contextAgentsLoading && contextAgents.length === 0 ? (
                    <Card withBorder p="lg" radius="md">
                      <Group>
                        <Loader size="sm" />
                        <Text size="sm">Loading agents…</Text>
                      </Group>
                    </Card>
                  ) : contextAgentsError ? (
                    <Alert icon={<IconAlertCircle size={16} />} color="red" variant="light">
                      {contextAgentsError}
                    </Alert>
                  ) : (
                    <>
                      <Card withBorder p="lg" radius="md">
                        <Group justify="space-between" align="center">
                          <div>
                            <Text fw={600}>Context Budgets</Text>
                            <Text size="xs" c="dimmed">Enforced on every run.</Text>
                          </div>
                          <Select
                            label="Agent"
                            value={selectedContextAgent}
                            onChange={(value) => setSelectedContextAgent(value)}
                            data={contextAgents.map((agent) => ({
                              value: agent.id,
                              label: `${agent.name} (${agent.model})`,
                            }))}
                          />
                        </Group>
                      </Card>

                      {agentContextLoading ? (
                        <Card withBorder p="lg" radius="md">
                          <Group>
                            <Loader size="sm" />
                            <Text size="sm">Loading context…</Text>
                          </Group>
                        </Card>
                      ) : agentContextError ? (
                        <Alert icon={<IconAlertCircle size={16} />} color="red" variant="light">
                          {agentContextError}
                        </Alert>
                      ) : agentContextDetail ? (
                        <>
                          <Card withBorder p="lg" radius="md">
                            <Group justify="space-between">
                              <div>
                                <Text size="sm" c="dimmed">Context headroom (last run)</Text>
                                <Text size="xl" fw={700}>
                                  {lastContextRun?.headroom ?? 0} tokens
                                </Text>
                              </div>
                              <Badge color={lastContextStatusColor} variant="light">
                                {lastContextStatus}
                              </Badge>
                            </Group>
                            <Divider my="md" />
                            <ContextStackedBar
                              contextWindow={contextWindowTokens}
                              reservedOutput={reservedOutputTokens}
                              tokens={lastContextRun?.component_tokens || {}}
                            />
                          </Card>

                          <Card withBorder p="lg" radius="md">
                            <Group justify="space-between" align="center">
                              <div>
                                <Text fw={600}>Budgets</Text>
                                <Text size="xs" c="dimmed">Adjust and save to enforce.</Text>
                              </div>
                              <Button size="xs" onClick={handleContextSave} loading={contextSaving}>
                                Save
                              </Button>
                            </Group>
                            <Divider my="md" />
                            <Stack gap="sm">
                              <NumberInput
                                label="Context window"
                                value={contextWindowTokens}
                                onChange={(v) => setContextWindowTokens(Number(v))}
                                min={8192}
                                max={1000000}
                                disabled
                              />
                              <NumberInput
                                label="Reserved output tokens"
                                value={reservedOutputTokens}
                                onChange={(v) => setReservedOutputTokens(Number(v))}
                                min={0}
                              />
                              <NumberInput
                                label="System budget"
                                value={contextBudgets.system || 0}
                                onChange={(v) => setContextBudgets((b) => ({ ...b, system: Number(v) }))}
                                min={0}
                              />
                              <NumberInput
                                label="Memory budget"
                                value={contextBudgets.memory || 0}
                                onChange={(v) => setContextBudgets((b) => ({ ...b, memory: Number(v) }))}
                                min={0}
                              />
                              <NumberInput
                                label="History budget"
                                value={contextBudgets.history || 0}
                                onChange={(v) => setContextBudgets((b) => ({ ...b, history: Number(v) }))}
                                min={0}
                              />
                              <NumberInput
                                label="Retrieval budget"
                                value={contextBudgets.retrieval || 0}
                                onChange={(v) => setContextBudgets((b) => ({ ...b, retrieval: Number(v) }))}
                                min={0}
                              />
                              <NumberInput
                                label="Tool results budget"
                                value={contextBudgets.tool_results || 0}
                                onChange={(v) => setContextBudgets((b) => ({ ...b, tool_results: Number(v) }))}
                                min={0}
                              />
                              <NumberInput
                                label="Safety margin"
                                value={contextBudgets.safety_margin || 0}
                                onChange={(v) => setContextBudgets((b) => ({ ...b, safety_margin: Number(v) }))}
                                min={0}
                              />
                            </Stack>
                          </Card>

                          <Card withBorder p="lg" radius="md">
                            <Group justify="space-between">
                              <div>
                                <Text fw={600}>Simulate</Text>
                                <Text size="xs" c="dimmed">Preview trims with current budgets.</Text>
                              </div>
                              <Button size="xs" onClick={handleContextSimulate} loading={simulateState === "loading"}>
                                Run simulation
                              </Button>
                            </Group>
                            <Divider my="md" />
                            {simulateState === "loading" ? (
                              <Group gap="xs">
                                <Loader size="sm" />
                                <Text size="sm">Simulating…</Text>
                              </Group>
                            ) : simulateState === "error" ? (
                              <Alert icon={<IconAlertCircle size={16} />} color="red" variant="light">
                                {simulateResult?.error || "Simulation failed"}
                              </Alert>
                            ) : simulateResult ? (
                              <Stack gap="xs">
                                <Group justify="space-between">
                                  <Text size="sm">Status</Text>
                                  <Badge variant="light">{simulateResult.status}</Badge>
                                </Group>
                                <Group justify="space-between">
                                  <Text size="sm">Headroom</Text>
                                  <Text size="sm" fw={600}>{simulateResult.headroom} tokens</Text>
                                </Group>
                                {simulateResult.trimming_applied?.length ? (
                                  <Textarea
                                    label="Trimming applied"
                                    value={JSON.stringify(simulateResult.trimming_applied, null, 2)}
                                    readOnly
                                    minRows={4}
                                  />
                                ) : (
                                  <Text size="xs" c="dimmed">No trimming required.</Text>
                                )}
                              </Stack>
                            ) : (
                              <Text size="xs" c="dimmed">Run a simulation to preview trims.</Text>
                            )}
                          </Card>

                          <Card withBorder p="lg" radius="md">
                            <Group justify="space-between">
                              <div>
                                <Text fw={600}>Run history</Text>
                                <Text size="xs" c="dimmed">Last 50 runs</Text>
                              </div>
                              <Button size="xs" variant="light" onClick={() => setExplainOpen(true)} disabled={!lastContextRun}>
                                Explain last prompt
                              </Button>
                            </Group>
                            <Divider my="md" />
                            {agentContextDetail?.runs?.length ? (
                              <ScrollArea>
                                <Table withRowBorders striped>
                                  <Table.Thead>
                                    <Table.Tr>
                                      <Table.Th>Timestamp</Table.Th>
                                      <Table.Th>Status</Table.Th>
                                      <Table.Th>Input tokens</Table.Th>
                                      <Table.Th>Output tokens</Table.Th>
                                      <Table.Th>Headroom</Table.Th>
                                    </Table.Tr>
                                  </Table.Thead>
                                  <Table.Tbody>
                                    {agentContextDetail.runs.map((run: any) => (
                                      <Table.Tr key={run.id}>
                                        <Table.Td>{run.started_at ? new Date(run.started_at).toLocaleString() : "—"}</Table.Td>
                                        <Table.Td>{run.status}</Table.Td>
                                        <Table.Td>{run.input_tokens}</Table.Td>
                                        <Table.Td>{run.output_tokens}</Table.Td>
                                        <Table.Td>{run.headroom}</Table.Td>
                                      </Table.Tr>
                                    ))}
                                  </Table.Tbody>
                                </Table>
                              </ScrollArea>
                            ) : (
                              <Text size="sm" c="dimmed">No runs yet.</Text>
                            )}
                          </Card>

                          <Drawer
                            opened={explainOpen}
                            onClose={() => setExplainOpen(false)}
                            title="Explain last prompt"
                            position="right"
                            size="lg"
                          >
                            {lastContextRun?.included_summary?.prompt_preview ? (
                              <Stack gap="md">
                                {Object.entries(lastContextRun.included_summary.prompt_preview).map(([key, value]: any) => (
                                  <Card withBorder radius="md" p="sm" key={key}>
                                    <Text size="sm" fw={600}>{key}</Text>
                                    <Text size="xs" c="dimmed">Head</Text>
                                    <Textarea value={value.head} readOnly minRows={3} />
                                    <Text size="xs" c="dimmed" mt="sm">Tail</Text>
                                    <Textarea value={value.tail} readOnly minRows={3} />
                                  </Card>
                                ))}
                              </Stack>
                            ) : (
                              <Text size="sm" c="dimmed">No prompt preview available.</Text>
                            )}
                          </Drawer>
                        </>
                      ) : (
                        <Text size="sm" c="dimmed">Select an agent to view context.</Text>
                      )}
                    </>
                  )}
                </Stack>
              </Tabs.Panel>
            </Tabs>
          </Tabs.Panel>

          {/* CONNECTORS TAB */}
          <Tabs.Panel value="connectors" pl="md" style={{ flex: 1 }}>
            <Stack gap="md">
              {/* Inbox Sync Control */}
              <Card withBorder p="lg" radius="md">
                <Group justify="space-between" mb="md">
                  <div>
                    <Text fw={600}>Inbox Sync (Email & WhatsApp)</Text>
                    <Text size="xs" c="dimmed">
                      {inboxEnabled ? "Running - syncs every 15 minutes" : "Not running - click Launch to start"}
                    </Text>
                  </div>
                  <Badge color={inboxEnabled ? "green" : "gray"} variant="light">
                    {inboxEnabled ? "Active" : "Stopped"}
                  </Badge>
                </Group>
                
                <Group gap="sm">
                  {!inboxEnabled ? (
                    <Button 
                      leftSection={<IconRocket size={16} />}
                      loading={inboxLaunching}
                      onClick={handleInboxLaunch}
                    >
                      Launch Inbox Sync
                    </Button>
                  ) : (
                    <Button 
                      variant="light"
                      color="red"
                      onClick={handleInboxStop}
                    >
                      Stop Sync
                    </Button>
                  )}
                </Group>
                
                {inboxStatus && (
                  <Alert 
                    mt="md" 
                    color={inboxStatus.includes("Error") || inboxStatus.includes("Failed") ? "red" : "blue"}
                    icon={inboxStatus.includes("Error") ? <IconAlertCircle size={16} /> : <IconCheck size={16} />}
                  >
                    {inboxStatus}
                  </Alert>
                )}
              </Card>
              
              <Divider />
              
              <Text fw={600}>Reply Controls</Text>
              <Card withBorder p="lg" radius="md">
                <Stack gap="sm">
                  <Group justify="space-between">
                    <div>
                      <Text fw={600}>Allow agent replies</Text>
                      <Text size="xs" c="dimmed">Enable automated replies for inbox messages.</Text>
                    </div>
                    <Switch
                      checked={mailSettings.allowAgentReplies}
                      onChange={(e) => updateMailSetting({ allowAgentReplies: e.currentTarget.checked })}
                      disabled={mailSettingsSaving}
                    />
                  </Group>
                  <Group justify="space-between">
                    <div>
                      <Text fw={600}>WhatsApp replies</Text>
                      <Text size="xs" c="dimmed">Allow sending WhatsApp replies from the inbox.</Text>
                    </div>
                    <Switch
                      checked={mailSettings.allowWhatsappReplies}
                      onChange={(e) => updateMailSetting({ allowWhatsappReplies: e.currentTarget.checked })}
                      disabled={mailSettingsSaving || !mailSettings.allowAgentReplies}
                    />
                  </Group>
                  <Group justify="space-between">
                    <div>
                      <Text fw={600}>Email replies</Text>
                      <Text size="xs" c="dimmed">Allow sending email replies from the inbox.</Text>
                    </div>
                    <Switch
                      checked={mailSettings.allowEmailReplies}
                      onChange={(e) => updateMailSetting({ allowEmailReplies: e.currentTarget.checked })}
                      disabled={mailSettingsSaving || !mailSettings.allowAgentReplies}
                    />
                  </Group>
                  {mailSettingsError && (
                    <Alert color="red" variant="light" icon={<IconAlertCircle size={16} />}>
                      {mailSettingsError}
                    </Alert>
                  )}
                </Stack>
              </Card>

              <Divider />
              
              <Text fw={600}>Connected Accounts</Text>
              <ConnectorCard
                name="WhatsApp"
                icon={IconBrandWhatsapp}
                color="green"
                connected={Boolean(connectorStatus.whatsapp?.connected)}
                account={
                  connectorStatus.whatsapp?.phone
                    ? connectorStatus.whatsapp.phone
                    : connectorStatus.whatsapp?.connected
                      ? "Connected"
                      : "Not connected"
                }
                lastSync={connectorStatus.whatsapp?.status || "Unknown"}
                onConnect={() => {}}
                onDisconnect={() => {}}
              />
              <ConnectorCard
                name="Gmail"
                icon={IconMail}
                color="red"
                connected={Boolean(connectorStatus.gmail?.connected)}
                account={
                  connectorStatus.gmail?.accounts?.length
                    ? connectorStatus.gmail.accounts[0]
                    : connectorStatus.gmail?.connected
                      ? "Connected"
                      : "Not connected"
                }
                lastSync={connectorStatus.gmail?.status || "Unknown"}
                onConnect={() => {}}
                onDisconnect={() => {}}
              />

              <Divider my="sm" />
              
              <Text fw={600}>Other Integrations</Text>
              <ConnectorCard
                name="Calendar"
                icon={IconHome}
                color="blue"
                connected={false}
                disabled
                disabledReason="Calendar connector not configured"
                onConnect={() => {}}
                onDisconnect={() => {}}
              />
              
              <Divider my="lg" label="Connector Marketplace" labelPosition="center" />
              
              {/* Full Connector Marketplace (LobeHub-inspired) */}
              <ConnectorMarketplace />
            </Stack>
          </Tabs.Panel>

          {/* NOTIFICATIONS TAB */}
          <Tabs.Panel value="notifications" pl="md" style={{ flex: 1 }}>
            <Card withBorder p="lg" radius="md">
              <Text fw={600} mb="md">Notification Preferences</Text>
              <Stack gap="md">
                <Group justify="space-between">
                  <div>
                    <Text size="sm">In-App Notifications</Text>
                    <Text size="xs" c="dimmed">Show notifications in the dashboard</Text>
                  </div>
                  <Switch 
                    checked={settings.notifications.inApp}
                    onChange={() => setSettings(s => ({...s, notifications: { ...s.notifications, inApp: !s.notifications.inApp }}))}
                  />
                </Group>
                <Divider />
                <Group justify="space-between">
                  <div>
                    <Text size="sm">Push Notifications</Text>
                    <Text size="xs" c="dimmed">Browser push notifications</Text>
                  </div>
                  <Switch 
                    checked={settings.notifications.push}
                    onChange={() => setSettings(s => ({...s, notifications: { ...s.notifications, push: !s.notifications.push }}))}
                  />
                </Group>
                <Divider />
                <Group justify="space-between">
                  <div>
                    <Text size="sm">Email Alerts</Text>
                    <Text size="xs" c="dimmed">Send critical alerts via email</Text>
                  </div>
                  <Switch 
                    checked={settings.notifications.email}
                    onChange={() => setSettings(s => ({...s, notifications: { ...s.notifications, email: !s.notifications.email }}))}
                  />
                </Group>
                {settings.notifications.email && (
                  <TextInput
                    label="Alert Email"
                    placeholder="alerts@example.com"
                    value={settings.notifications.alertEmail}
                    onChange={(e) => setSettings(s => ({...s, notifications: { ...s.notifications, alertEmail: readInputValue(e) }}))}
                  />
                )}
                <Divider />
                <Group justify="space-between">
                  <div>
                    <Text size="sm">Urgent Only</Text>
                    <Text size="xs" c="dimmed">Only notify on urgent events</Text>
                  </div>
                  <Switch
                    checked={settings.notifications.urgentOnly}
                    onChange={() => setSettings(s => ({...s, notifications: { ...s.notifications, urgentOnly: !s.notifications.urgentOnly }}))}
                  />
                </Group>
                <Divider />
                <Group justify="space-between">
                  <div>
                    <Text size="sm">Daily Summary</Text>
                    <Text size="xs" c="dimmed">Send a daily summary digest</Text>
                  </div>
                  <Switch
                    checked={settings.notifications.dailySummary}
                    onChange={() => setSettings(s => ({...s, notifications: { ...s.notifications, dailySummary: !s.notifications.dailySummary }}))}
                  />
                </Group>
                <Divider />
                <Group justify="space-between">
                  <div>
                    <Text size="sm">Weekly Report</Text>
                    <Text size="xs" c="dimmed">Send a weekly system report</Text>
                  </div>
                  <Switch
                    checked={settings.notifications.weeklyReport}
                    onChange={() => setSettings(s => ({...s, notifications: { ...s.notifications, weeklyReport: !s.notifications.weeklyReport }}))}
                  />
                </Group>
              </Stack>
            </Card>
          </Tabs.Panel>

          {/* SECURITY TAB */}
          <Tabs.Panel value="security" pl="md" style={{ flex: 1 }}>
            <Stack gap="md">
              <Card withBorder p="lg" radius="md">
                <Text fw={600} mb="md">Access Control</Text>
                <Stack gap="md">
                  <Group justify="space-between" align="flex-start">
                    <div>
                      <Text size="sm">Approval Threshold</Text>
                      <Text size="xs" c="dimmed">Require approval above ${settings.approvalThreshold.toFixed(0)}</Text>
                    </div>
                    <Button size="xs" variant="light" onClick={() => handleTabChange("general")}>
                      Edit in General
                    </Button>
                  </Group>
                  <Divider />
                  <Group justify="space-between">
                    <div>
                      <Text size="sm">Audit Logging</Text>
                      <Text size="xs" c="dimmed">Log all agent actions</Text>
                    </div>
                    <Switch
                      checked={settings.security.auditLogging}
                      onChange={() => setSettings(s => ({...s, security: { ...s.security, auditLogging: !s.security.auditLogging }}))}
                    />
                  </Group>
                  <Divider />
                  <Group justify="space-between">
                    <div>
                      <Text size="sm">Threat Monitoring</Text>
                      <Text size="xs" c="dimmed">Detect anomalies and unusual behavior</Text>
                    </div>
                    <Switch
                      checked={settings.security.threatMonitoring}
                      onChange={() => setSettings(s => ({...s, security: { ...s.security, threatMonitoring: !s.security.threatMonitoring }}))}
                    />
                  </Group>
                  <Divider />
                  <Group justify="space-between" align="flex-start">
                    <div>
                      <Text size="sm">Credential Rotation</Text>
                      <Text size="xs" c="dimmed">Rotate credentials every N days</Text>
                    </div>
                    <NumberInput
                      value={settings.security.credentialRotationDays}
                      onChange={(v) => setSettings(s => ({...s, security: { ...s.security, credentialRotationDays: Number(v) }}))}
                      min={30}
                      max={365}
                      w={120}
                      size="sm"
                    />
                  </Group>
                </Stack>
              </Card>

              <Card withBorder p="lg" radius="md">
                <Text fw={600} mb="md">API Keys</Text>
                <Text size="sm" c="dimmed" mb="md">
                  API keys are managed through environment variables. Check TOOLS.md for configuration.
                </Text>
                <Button 
                  variant="light" 
                  leftSection={<IconKey size={16} />}
                  onClick={() => {
                    notifications.show({
                      title: "API Keys",
                      message: "API keys are configured via environment variables (ANTHROPIC_API_KEY, ELEVENLABS_API_KEY, etc.)",
                      color: "blue",
                    });
                  }}
                >
                  View Info
                </Button>
              </Card>
            </Stack>
          </Tabs.Panel>

          {/* DATA TAB */}
          <Tabs.Panel value="data" pl="md" style={{ flex: 1 }}>
            <Stack gap="md">
              <Card withBorder p="lg" radius="md">
                <Text fw={600} mb="md">Export & Import</Text>
                <Group>
                  <Button 
                    variant="light" 
                    leftSection={<IconDownload size={16} />}
                    onClick={async () => {
                      try {
                        const data = await apiFetch<any>("/backup/export", { method: "POST" });
                        if (data?.success === false) {
                          throw new Error(data.error || "Backup failed");
                        }
                        notifications.show({
                          title: "Backup Created",
                          message: data.message || "Backup exported successfully",
                          color: "green",
                        });
                        try {
                          const stats = await apiFetch<any>("/database/stats");
                          setDbStats({
                            size_formatted: stats.size_formatted,
                            last_backup: stats.last_backup,
                          });
                        } catch {}
                      } catch (e) {
                        notifications.show({
                          title: "Export Failed",
                          message: getErrorMessage(e, "Could not export backup"),
                          color: "red",
                        });
                      }
                    }}
                  >
                    Export Backup
                  </Button>
                  <Button
                    variant="light"
                    leftSection={<IconUpload size={16} />}
                    onClick={() => {
                      setBackupModalOpen(true);
                      fetchBackups();
                    }}
                  >
                    Import Backup
                  </Button>
                </Group>
              </Card>

              <Card withBorder p="lg" radius="md">
                <Text fw={600} mb="md">Database</Text>
                <Stack gap="sm">
                  <Group justify="space-between">
                    <Text size="sm">Database Size</Text>
                    <Text size="sm" fw={500}>{dbStats.size_formatted}</Text>
                  </Group>
                  <Group justify="space-between">
                    <Text size="sm">Last Backup</Text>
                    <Text size="sm" fw={500}>
                      {dbStats.last_backup 
                        ? new Date(dbStats.last_backup).toLocaleString()
                        : "Never"}
                    </Text>
                  </Group>
                  <Divider my="xs" />
                  <Button 
                    variant="light" 
                    leftSection={<IconDatabase size={16} />}
                    loading={dbLoading}
                    onClick={async () => {
                      setDbLoading(true);
                      try {
                        const data = await apiFetch<any>("/backup/export", { method: "POST" });
                        if (data?.success === false) {
                          throw new Error(data.error || "Backup failed");
                        }
                        notifications.show({
                          title: "Backup Created",
                          message: "Database backed up successfully",
                          color: "green",
                        });
                        try {
                          const stats = await apiFetch<any>("/database/stats");
                          setDbStats({
                            size_formatted: stats.size_formatted,
                            last_backup: stats.last_backup,
                          });
                        } catch {}
                      } catch (e) {
                        notifications.show({
                          title: "Backup Failed",
                          message: getErrorMessage(e, "Could not create backup"),
                          color: "red",
                        });
                      } finally {
                        setDbLoading(false);
                      }
                    }}
                  >
                    Create Backup
                  </Button>
                </Stack>
              </Card>

              {/* Clean Slate Section */}
              <Card withBorder p="lg" radius="md">
                <Group justify="space-between" mb="md">
                  <div>
                    <Text fw={600}>Clean Slate</Text>
                    <Text size="xs" c="dimmed">Mark items as complete or clear specific data</Text>
                  </div>
                  <Button
                    variant="light"
                    size="xs"
                    onClick={async () => {
                      await refreshDataCounts(false);
                    }}
                  >
                    Refresh Counts
                  </Button>
                </Group>

                <Stack gap="md">
                  {/* Mark All Complete Section */}
                  <Box>
                    <Text size="sm" fw={500} mb="xs">Mark All As Done</Text>
                    <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="sm">
                      <Button
                        variant="light"
                        color="blue"
                        leftSection={<IconMail size={16} />}
                        onClick={async () => {
                          try {
                            const data = await apiFetch<any>("/api/data/inbox/mark-all-read", { method: "POST" });
                            notifications.show({
                              title: "Messages Marked Read",
                              message: data.message,
                              color: "green",
                            });
                            void refreshDataCounts();
                          } catch (e) {
                            notifications.show({
                              title: "Error",
                              message: getErrorMessage(e, "Could not mark messages as read"),
                              color: "red",
                            });
                          }
                        }}
                      >
                        Mark All Messages Read
                        {dataCounts.unread_messages > 0 && (
                          <Badge ml="xs" size="xs" variant="filled" color="red">{dataCounts.unread_messages}</Badge>
                        )}
                      </Button>

                      <Button
                        variant="light"
                        color="teal"
                        leftSection={<IconChecklist size={16} />}
                        onClick={async () => {
                          try {
                            const data = await apiFetch<any>("/api/data/tasks/mark-all-complete", { method: "POST" });
                            notifications.show({
                              title: "Tasks Completed",
                              message: data.message,
                              color: "green",
                            });
                            void refreshDataCounts();
                          } catch (e) {
                            notifications.show({
                              title: "Error",
                              message: getErrorMessage(e, "Could not complete tasks"),
                              color: "red",
                            });
                          }
                        }}
                      >
                        Complete All Tasks
                        {dataCounts.pending_tasks > 0 && (
                          <Badge ml="xs" size="xs" variant="filled" color="orange">{dataCounts.pending_tasks}</Badge>
                        )}
                      </Button>

                      <Button
                        variant="light"
                        color="green"
                        leftSection={<IconCoin size={16} />}
                        onClick={async () => {
                          try {
                            const data = await apiFetch<any>("/api/data/bills/mark-all-paid", { method: "POST" });
                            notifications.show({
                              title: "Bills Paid",
                              message: data.message,
                              color: "green",
                            });
                            void refreshDataCounts();
                          } catch (e) {
                            notifications.show({
                              title: "Error",
                              message: getErrorMessage(e, "Could not mark bills as paid"),
                              color: "red",
                            });
                          }
                        }}
                      >
                        Mark All Bills Paid
                        {dataCounts.unpaid_bills > 0 && (
                          <Badge ml="xs" size="xs" variant="filled" color="yellow">{dataCounts.unpaid_bills}</Badge>
                        )}
                      </Button>

                      <Button
                        variant="light"
                        color="gray"
                        leftSection={<IconRefresh size={16} />}
                        onClick={async () => {
                          try {
                            const data = await apiFetch<any>("/api/data/activity/clear", { method: "POST" });
                            notifications.show({
                              title: "Activity Cleared",
                              message: data.message,
                              color: "green",
                            });
                            void refreshDataCounts();
                          } catch (e) {
                            notifications.show({
                              title: "Error",
                              message: getErrorMessage(e, "Could not clear activity"),
                              color: "red",
                            });
                          }
                        }}
                      >
                        Clear Recent Activity
                        {dataCounts.activity_events > 0 && (
                          <Badge ml="xs" size="xs" variant="light">{dataCounts.activity_events}</Badge>
                        )}
                      </Button>
                    </SimpleGrid>
                  </Box>

                  <Divider />

                  {/* Clear Data Section */}
                  <Box>
                    <Text size="sm" fw={500} mb="xs">Clear Data (Delete)</Text>
                    <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="sm">
                      <Button
                        variant="subtle"
                        color="red"
                        size="xs"
                        leftSection={<IconTrash size={14} />}
                        onClick={async () => {
                          if (!confirm("Delete all inbox messages?")) return;
                          try {
                            const data = await apiFetch<any>("/api/data/inbox/clear", { method: "POST" });
                            notifications.show({ title: "Inbox Cleared", message: data.message, color: "orange" });
                            void refreshDataCounts();
                          } catch (e) {
                            notifications.show({
                              title: "Error",
                              message: getErrorMessage(e, "Could not clear inbox"),
                              color: "red",
                            });
                          }
                        }}
                      >
                        Clear Inbox ({dataCounts.inbox_messages})
                      </Button>

                      <Button
                        variant="subtle"
                        color="red"
                        size="xs"
                        leftSection={<IconTrash size={14} />}
                        onClick={async () => {
                          if (!confirm("Delete all tasks?")) return;
                          try {
                            const data = await apiFetch<any>("/api/data/tasks/clear", { method: "POST" });
                            notifications.show({ title: "Tasks Cleared", message: data.message, color: "orange" });
                            void refreshDataCounts();
                          } catch (e) {
                            notifications.show({
                              title: "Error",
                              message: getErrorMessage(e, "Could not clear tasks"),
                              color: "red",
                            });
                          }
                        }}
                      >
                        Clear Tasks ({dataCounts.pending_tasks + dataCounts.completed_tasks})
                      </Button>

                      <Button
                        variant="subtle"
                        color="red"
                        size="xs"
                        leftSection={<IconTrash size={14} />}
                        onClick={async () => {
                          if (!confirm("Delete all bills?")) return;
                          try {
                            const data = await apiFetch<any>("/api/data/bills/clear", { method: "POST" });
                            notifications.show({ title: "Bills Cleared", message: data.message, color: "orange" });
                            void refreshDataCounts();
                          } catch (e) {
                            notifications.show({
                              title: "Error",
                              message: getErrorMessage(e, "Could not clear bills"),
                              color: "red",
                            });
                          }
                        }}
                      >
                        Clear Bills ({dataCounts.unpaid_bills + dataCounts.paid_bills})
                      </Button>

                      <Button
                        variant="subtle"
                        color="red"
                        size="xs"
                        leftSection={<IconTrash size={14} />}
                        onClick={async () => {
                          if (!confirm("Clear all portfolio holdings?")) return;
                          try {
                            const data = await apiFetch<any>("/api/data/portfolio/clear", { method: "POST" });
                            notifications.show({ title: "Portfolio Cleared", message: data.message, color: "orange" });
                            void refreshDataCounts();
                          } catch (e) {
                            notifications.show({
                              title: "Error",
                              message: getErrorMessage(e, "Could not clear portfolio"),
                              color: "red",
                            });
                          }
                        }}
                      >
                        Clear Portfolio ({dataCounts.portfolio_holdings})
                      </Button>
                    </SimpleGrid>
                  </Box>

                  <Divider />

                  {/* Full Clean Slate */}
                  <Box>
                    <Text size="sm" fw={500} mb="xs">Full Clean Slate</Text>
                    <Button
                      variant="light"
                      color="violet"
                      fullWidth
                      leftSection={<IconWand size={16} />}
                        onClick={async () => {
                          if (!confirm("This will clear inbox, tasks, bills, and activity. Portfolio and contractors will be preserved. Continue?")) return;
                          try {
                            const data = await apiFetch<any>("/api/data/clean-slate", { method: "POST" });
                            notifications.show({
                              title: "Clean Slate Complete",
                              message: data.message,
                              color: "green",
                            });
                            void refreshDataCounts();
                          } catch (e) {
                            notifications.show({
                              title: "Error",
                              message: getErrorMessage(e, "Clean slate failed"),
                              color: "red",
                            });
                          }
                        }}
                      >
                        Start Fresh (Keep Portfolio & Contractors)
                    </Button>
                  </Box>
                </Stack>
              </Card>

              <Card withBorder p="lg" radius="md" style={{ borderColor: "var(--mantine-color-red-6)" }}>
                <Text fw={600} mb="md" c="red">Danger Zone</Text>
                <Text size="sm" c="dimmed" mb="md">
                  These actions cannot be undone. A backup will be created first.
                </Text>
                <Group>
                  <Button 
                    color="red" 
                    variant="light" 
                    leftSection={<IconTrash size={16} />}
                    onClick={async () => {
                      if (!confirm("Are you sure? This will delete all tasks, transactions, jobs, and messages.")) {
                        return;
                      }
                      try {
                        const data = await apiFetch<any>("/database/clear", { method: "POST" });
                        if (data?.success === false) {
                          throw new Error(data.error || "Clear failed");
                        }
                        notifications.show({
                          title: "Data Cleared",
                          message: "All data has been cleared. Settings preserved.",
                          color: "orange",
                        });
                      } catch (e) {
                        notifications.show({
                          title: "Clear Failed",
                          message: getErrorMessage(e, "Could not clear data"),
                          color: "red",
                        });
                      }
                    }}
                  >
                    Clear All Data
                  </Button>
                  <Button 
                    color="red" 
                    variant="light" 
                    leftSection={<IconRefresh size={16} />}
                    onClick={async () => {
                      if (!confirm("Are you sure? This will reset the database to factory defaults.")) {
                        return;
                      }
                      try {
                        const data = await apiFetch<any>("/database/reset", { method: "POST" });
                        if (data?.success === false) {
                          throw new Error(data.error || "Reset failed");
                        }
                        notifications.show({
                          title: "Database Reset",
                          message: "Database has been reset. Previous data was backed up.",
                          color: "orange",
                        });
                        // Refresh page to reload data
                        window.location.reload();
                      } catch (e) {
                        notifications.show({
                          title: "Reset Failed",
                          message: getErrorMessage(e, "Could not reset database"),
                          color: "red",
                        });
                      }
                    }}
                  >
                    Reset to Defaults
                  </Button>
                </Group>
              </Card>
            </Stack>
          </Tabs.Panel>

          {/* DASHBOARD TAB */}
          <Tabs.Panel value="dashboard" pl="md" style={{ flex: 1 }}>
            <Stack gap="md">
              <Card withBorder p="lg" radius="md">
                <WidgetManager />
              </Card>
            </Stack>
          </Tabs.Panel>
        </Tabs>

        {/* Floating Save Button */}
        {settingsDirty && (
          <Paper
            shadow="lg"
            radius="lg"
            p="md"
            style={{
              position: "fixed",
              bottom: "calc(24px + var(--global-chat-offset, 0px))",
              right: 24,
              zIndex: 100,
              display: "flex",
              alignItems: "center",
              gap: 12,
              backgroundColor: "var(--mantine-color-body)",
              border: "1px solid var(--mantine-color-default-border)",
            }}
          >
            <Text size="sm" c="dimmed">Unsaved changes</Text>
            <Button size="sm" loading={settingsSaving} onClick={handleSaveSettings}>
              Save Settings
            </Button>
          </Paper>
        )}
      </Stack>

      {/* Save Confirmation Toast */}
      <SaveConfirmation
        visible={showSaveConfirmation}
        onClose={() => setShowSaveConfirmation(false)}
      />
          </Page>
    </Shell>
  );
}
