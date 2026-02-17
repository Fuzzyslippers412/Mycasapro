export function getApiBaseUrl() {
  if (typeof window !== "undefined") {
    const override = window.localStorage.getItem("mycasa_api_base_override");
    if (override) return override;
    const envUrl = process.env.NEXT_PUBLIC_API_URL;
    if (envUrl) {
      try {
        const envParsed = new URL(envUrl);
        const envHost = envParsed.hostname;
        const envPort = envParsed.port || "6709";
        const windowHost = window.location.hostname;
        const envIsLocal = envHost === "localhost" || envHost === "127.0.0.1";
        const windowIsLocal = windowHost === "localhost" || windowHost === "127.0.0.1";
        if (envIsLocal && !windowIsLocal) {
          const safeHost = windowHost.includes(":") && !windowHost.startsWith("[")
            ? `[${windowHost}]`
            : windowHost;
          return `${window.location.protocol}//${safeHost}:${envPort}`;
        }
        return envUrl;
      } catch {
        return envUrl;
      }
    }
    const host = window.location.hostname;
    const safeHost = host.includes(":") && !host.startsWith("[") ? `[${host}]` : host;
    return `${window.location.protocol}//${safeHost}:6709`;
  }
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  return "http://127.0.0.1:6709";
}

const API_URL = getApiBaseUrl();

export class ApiNetworkError extends Error {
  status: number;
  constructor(message: string = "Network error") {
    super(message);
    this.name = "ApiNetworkError";
    this.status = 0;
  }
}

export function isNetworkError(err: unknown): boolean {
  if (!err || typeof err !== "object") return false;
  const name = (err as any).name;
  const message = (err as any).message || "";
  return (
    name === "ApiNetworkError" ||
    name === "AbortError" ||
    message.includes("Failed to fetch") ||
    message.includes("NetworkError")
  );
}

export async function apiFetch<T>(path: string, opts: RequestInit = {}, timeoutMs = 8000): Promise<T> {
  const attemptRequest = async (baseUrl: string): Promise<Response> => {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeoutMs);
    const requestId =
      typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
        ? crypto.randomUUID()
        : `req_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;

    const storedToken = typeof window !== "undefined" ? localStorage.getItem("token") : null;
    try {
      return await fetch(`${baseUrl}${path}`, {
        ...opts,
        headers: {
          "Content-Type": "application/json",
          ...(storedToken ? { "Authorization": `Bearer ${storedToken}` } : {}),
          ...(opts.headers || {}),
          "X-Request-Id": requestId,
        },
        credentials: "include",
        signal: controller.signal,
      });
    } finally {
      clearTimeout(id);
    }
  };

  const getFallbackBase = (): string | null => {
    try {
      const parsed = new URL(API_URL);
      const isLocal = parsed.hostname === "127.0.0.1" || parsed.hostname === "localhost";
      if (!isLocal) return null;
      if (parsed.port !== "8000") return null;
      return `${parsed.protocol}//${parsed.hostname}:6709`;
    } catch {
      return null;
    }
  };

  let res: Response;
  try {
    res = await attemptRequest(API_URL);
  } catch (err: any) {
    const fallback = getFallbackBase();
    if (fallback) {
      try {
        res = await attemptRequest(fallback);
        if (typeof window !== "undefined") {
          window.localStorage.setItem("mycasa_api_base_override", fallback);
        }
      } catch (retryErr: any) {
        const message = retryErr?.name === "AbortError" ? "Request timed out" : retryErr?.message || "Failed to fetch";
        throw new ApiNetworkError(message);
      }
    } else {
      const message = err?.name === "AbortError" ? "Request timed out" : err?.message || "Failed to fetch";
      throw new ApiNetworkError(message);
    }
  }

  if (!res.ok) {
    let err: any = { status: res.status };
    try { err = await res.json(); } catch {}
    throw err;
  }
  return res.json() as Promise<T>;
}

// Chat APIs
export interface ChatResponse {
  response: string;
  conversation_id?: string;
  agent_name?: string;
  timestamp?: string;
  error?: string;
  exit_code?: number;
  routed_to?: string;
  agent_emoji?: string;
  task_created?: {
    task_id?: number | string;
    title?: string;
    due_date?: string | null;
    scheduled_date?: string | null;
  };
}

export async function sendManagerChat(message: string, conversationId?: string) {
  return apiFetch<ChatResponse>("/manager/chat", {
    method: "POST",
    body: JSON.stringify({
      message,
      conversation_id: conversationId || null,
    }),
  }, 60000);
}

export async function sendAgentChat(agentId: string, message: string, conversationId?: string) {
  return apiFetch<ChatResponse>(`/api/agents/${agentId}/chat`, {
    method: "POST",
    body: JSON.stringify({
      message,
      conversation_id: conversationId || null,
    }),
  }, 60000);
}

export async function uploadUserAvatar(file: File) {
  const form = new FormData();
  form.append("file", file);

  const token = typeof window !== "undefined" ? localStorage.getItem("token") || "" : "";
  const res = await fetch(`${API_URL}/api/auth/avatar`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    credentials: "include",
    body: form,
  });

  if (!res.ok) {
    let detail = "Failed to upload avatar";
    try {
      const data = await res.json();
      detail = data?.detail || detail;
    } catch {}
    throw new Error(detail);
  }

  return res.json();
}

export async function getAgentChatHistory(agentId: string, conversationId?: string, limit: number = 50) {
  const params = new URLSearchParams();
  if (conversationId) params.set("conversation_id", conversationId);
  params.set("limit", limit.toString());
  return apiFetch<{ conversation_id: string; messages: any[]; total: number }>(
    `/api/agents/${agentId}/history?${params.toString()}`
  );
}

// Agent context APIs
export interface AgentContextSummary {
  id: string;
  name: string;
  model: string;
  provider: string;
  context_window_tokens: number;
  reserved_output_tokens: number;
  budgets: Record<string, number>;
  last_run?: any;
}

export interface AgentContextDetail extends AgentContextSummary {
  runs?: any[];
  headroom?: number;
  breakdown?: Record<string, number>;
  [key: string]: unknown;
}

export async function getAgentsContext() {
  return apiFetch<{ agents: AgentContextSummary[] }>("/api/agents");
}

export async function getAgentContext(agentIdentifier: string) {
  return apiFetch<AgentContextDetail>(`/api/agents/${agentIdentifier}/context`);
}

export async function updateAgentContext(agentIdentifier: string, payload: any) {
  return apiFetch(`/api/agents/${agentIdentifier}/context`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function getAgentRuns(agentIdentifier: string, limit: number = 50) {
  return apiFetch(`/api/agents/${agentIdentifier}/runs?limit=${limit}`);
}

export async function simulateAgentContext(agentIdentifier: string, payload: any) {
  return apiFetch(`/api/agents/${agentIdentifier}/simulate-context`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// Qwen OAuth (device flow)
export async function startQwenOAuth() {
  return apiFetch<{
    session_id: string;
    user_code: string;
    verification_uri: string;
    verification_uri_complete?: string;
    expires_at: string;
    interval_seconds: number;
  }>("/api/llm/qwen/oauth/start", { method: "POST" });
}

export async function pollQwenOAuth(sessionId: string) {
  return apiFetch<{
    status: "pending" | "success" | "error" | "expired";
    message?: string;
    interval_seconds?: number;
    expires_at?: number;
    resource_url?: string;
  }>("/api/llm/qwen/oauth/poll", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId }),
  });
}

export async function disconnectQwenOAuth() {
  return apiFetch<{ success: boolean }>("/api/llm/qwen/oauth", { method: "DELETE" });
}

// Status APIs
export async function getStatus() {
  return apiFetch<StatusResponse>("/status");
}

export async function getFullStatus() {
  return apiFetch<FullStatusResponse>("/status/full");
}

// Task APIs
export async function getTasks(params?: { status?: string; priority?: string; limit?: number }) {
  const queryParams = new URLSearchParams();
  if (params?.status) queryParams.append('status', params.status);
  if (params?.priority) queryParams.append('priority', params.priority);
  if (params?.limit) queryParams.append('limit', params.limit.toString());

  const queryString = queryParams.toString();
  const response = await apiFetch<{ tasks: Task[]; total: number }>("/tasks" + (queryString ? `?${queryString}` : ""));
  return response.tasks || [];
}

export async function createTask(task: Partial<Task>) {
  return apiFetch<Task>("/tasks", {
    method: "POST",
    body: JSON.stringify(task),
  });
}

export async function completeTask(taskId: number) {
  return apiFetch<Task>(`/tasks/${taskId}/complete`, {
    method: "PATCH",
  });
}

// Bill APIs
export async function getBills(includePaid: boolean = false) {
  const response = await apiFetch<{ bills: Bill[] }>(`/bills?include_paid=${includePaid}`);
  return response.bills || [];
}

export async function payBill(billId: number) {
  return apiFetch<Bill>(`/bills/${billId}/pay`, {
    method: "PATCH",
  });
}

// Portfolio APIs
export async function getPortfolio() {
  return apiFetch<PortfolioData>("/portfolio");
}

export async function addHolding(holding: Partial<Holding>) {
  return apiFetch<Holding>("/portfolio/holdings", {
    method: "POST",
    body: JSON.stringify(holding),
  });
}

export async function deleteHolding(ticker: string) {
  return apiFetch(`/portfolio/holdings/${ticker}`, {
    method: "DELETE",
  });
}

export async function updateCash(cash: number) {
  return apiFetch("/portfolio/cash", {
    method: "PUT",
    body: JSON.stringify({ cash }),
  });
}

// Inbox APIs
export async function getInboxMessages(params?: { source?: string; unread_only?: boolean; limit?: number }) {
  const queryParams = new URLSearchParams();
  if (params?.source) queryParams.append('source', params.source);
  if (params?.unread_only !== undefined) queryParams.append('unread_only', params.unread_only.toString());
  if (params?.limit) queryParams.append('limit', params.limit.toString());

  const queryString = queryParams.toString();
  const response = await apiFetch<{ messages: InboxMessage[]; count: number }>(`/inbox/messages` + (queryString ? `?${queryString}` : ""));
  return response.messages || [];
}

export async function getUnreadCount() {
  return apiFetch<UnreadCount>("/inbox/unread-count");
}

export async function markMessageAsRead(messageId: number) {
  return apiFetch<InboxMessage>(`/inbox/messages/${messageId}/read`, {
    method: "PATCH",
  });
}

// Security APIs
export async function getSecurityStatus() {
  return apiFetch<SecurityStatus>("/security");
}

// System APIs
export async function getSystemStatus() {
  return apiFetch<SystemStatus>("/system/status");
}

export async function getQuickStatus() {
  return apiFetch<QuickStatus>("/status");
}

// Personas/Agents APIs
export async function getAgentStatus() {
  return apiFetch<Persona[]>("/personas");
}

export async function getPersona(personaId: string) {
  return apiFetch<Persona>(`/personas/${personaId}`);
}

export async function enablePersona(personaId: string) {
  return apiFetch<Persona>(`/personas/${personaId}/enable`, {
    method: "PATCH",
  });
}

export async function disablePersona(personaId: string) {
  return apiFetch<Persona>(`/personas/${personaId}/disable`, {
    method: "PATCH",
  });
}

// Audit APIs
export async function getAuditEvents(limit: number = 50) {
  return apiFetch<{ events: AuditEvent[] }>(`/api/audit/events?limit=${limit}`);
}

// Janitor Wizard APIs
export interface JanitorWizardRun {
  id: number;
  timestamp: string;
  health_score: number;
  status: string;
  findings_count: number;
  checks_passed: number;
  checks_total: number;
}

export async function getJanitorWizardHistory(limit: number = 1) {
  return apiFetch<{ runs: JanitorWizardRun[] }>(`/api/janitor/wizard/history?limit=${limit}`);
}

// Types
export interface StatusResponse {
  status: string;
  timestamp: string;
  uptime: number;
  version: string;
}

export interface FullStatusResponse extends StatusResponse {
  system: SystemInfo;
  agents: AgentStatus[];
  services: ServiceStatus[];
}

export interface SystemInfo {
  cpu: number;
  memory: number;
  disk: number;
  network: NetworkInfo;
}

export interface NetworkInfo {
  upload: number;
  download: number;
}

export interface AgentStatus {
  id: string;
  name: string;
  status: 'online' | 'offline' | 'busy';
  last_seen: string;
  tasks_completed: number;
}

export interface ServiceStatus {
  name: string;
  status: 'running' | 'stopped' | 'error';
  uptime: number;
}

export interface AuditEvent {
  id: number;
  event_id: string;
  event_type: string;
  source: string;
  payload: any;
  status: string;
  attempts: number;
  last_error?: string | null;
  created_at?: string | null;
}

export interface Task {
  id: number;
  title: string;
  description: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  priority: 'low' | 'medium' | 'high' | 'critical';
  assigned_to: string;
  created_at: string;
  updated_at: string;
  due_date?: string;
}

export interface Bill {
  id: number;
  vendor: string;
  amount: number;
  due_date: string;
  category: string;
  status: 'pending' | 'paid' | 'overdue';
  created_at: string;
  paid_at?: string;
}

export interface PortfolioData {
  holdings: Holding[];
  total_value: number;
  cash: number;
  last_updated: string;
}

export interface Holding {
  id: number;
  ticker: string;
  shares: number;
  current_price: number;
  purchase_price: number;
  asset_type: string;
  sector: string;
  purchase_date: string;
  value: number;
}

export interface InboxMessage {
  id: number;
  source: string;
  subject: string;
  content: string;
  sender: string;
  timestamp: string;
  read: boolean;
  priority: 'low' | 'medium' | 'high';
  category: string;
}

export interface UnreadCount {
  gmail: number;
  whatsapp: number;
  total: number;
}

export interface SecurityStatus {
  incidents: SecurityIncident[];
  last_scan: string;
  overall_risk: 'low' | 'medium' | 'high' | 'critical';
  vulnerabilities: Vulnerability[];
}

export interface SecurityIncident {
  id: number;
  type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  timestamp: string;
  resolved: boolean;
}

export interface Vulnerability {
  id: string;
  name: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  fixed: boolean;
}

export interface SystemStatus {
  running?: boolean;
  last_shutdown?: string | null;
  last_startup?: string | null;
  last_backup?: string | null;
  agents_enabled?: Record<string, boolean>;
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  network_in: number;
  network_out: number;
  uptime: number;
  load_average: number[];
}

// Quick status from /status endpoint
export interface QuickStatus {
  mode: string;
  timestamp: string;
  facts: {
    agents: Record<string, { state: string; doing: string | null }>;
    galidima_connected: boolean | null;
    tasks: { pending: number; upcoming: any[] };
    alerts: any[];
    recent_changes: Array<{
      agent: string;
      action: string;
      status: string;
      time: string;
      details?: string;
    }>;
  };
}

export interface Persona {
  id: string;
  name: string;
  description: string;
  status: 'enabled' | 'disabled';
  capabilities: string[];
  last_active: string;
  tasks_completed: number;
}
