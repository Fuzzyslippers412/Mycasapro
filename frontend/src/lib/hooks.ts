"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import * as api from "./api";

// Generic fetch hook
function useFetch<T>(
  fetcher: () => Promise<T>,
  deps: any[] = []
): { data: T | null; loading: boolean; error: Error | null; refetch: () => void } {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const hasLoadedRef = useRef(false);

  const fetch = useCallback(async () => {
    if (!hasLoadedRef.current) {
      setLoading(true);
    }
    setError(null);
    try {
      const result = await fetcher();
      setData(result);
    } catch (e) {
      setError(e as Error);
    } finally {
      setLoading(false);
      hasLoadedRef.current = true;
    }
  }, deps);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { data, loading, error, refetch: fetch };
}

// ============ STATUS ============

export function useSystemStatus(refreshInterval?: number) {
  const result = useFetch(() => api.getSystemStatus(), []);

  useEffect(() => {
    if (refreshInterval) {
      const interval = setInterval(() => result.refetch(), refreshInterval);
      return () => clearInterval(interval);
    }
  }, [refreshInterval, result.refetch]);

  return result;
}

export function useQuickStatus(refreshInterval?: number) {
  const result = useFetch(() => api.getQuickStatus(), []);

  useEffect(() => {
    if (refreshInterval) {
      const interval = setInterval(() => result.refetch(), refreshInterval);
      return () => clearInterval(interval);
    }
  }, [refreshInterval, result.refetch]);

  return result;
}

export function useFullStatus() {
  return useFetch(() => api.getFullStatus(), []);
}

// ============ TASKS ============

export function useTasks(params?: Parameters<typeof api.getTasks>[0]) {
  return useFetch(
    () => api.getTasks(params),
    [params?.status, params?.priority, params?.limit]
  );
}

// ============ BILLS ============

export function useBills(includePaid = false) {
  return useFetch(() => api.getBills(includePaid), [includePaid]);
}

// ============ INBOX ============

export function useInboxMessages(params?: Parameters<typeof api.getInboxMessages>[0]) {
  return useFetch(
    () => api.getInboxMessages(params),
    [params?.source, params?.unread_only, params?.limit]
  );
}

export function useUnreadCount() {
  return useFetch(() => api.getUnreadCount(), []);
}

// ============ SECURITY ============

export function useSecurityStatus() {
  return useFetch(() => api.getSecurityStatus(), []);
}

// ============ INDICATORS ============

export function useIndicatorDiagnostics(refreshInterval?: number) {
  const result = useFetch(() => api.getIndicatorDiagnostics(), []);

  useEffect(() => {
    if (refreshInterval) {
      const interval = setInterval(() => result.refetch(), refreshInterval);
      return () => clearInterval(interval);
    }
  }, [refreshInterval, result.refetch]);

  return result;
}

// ============ AGENTS ============

export function useAgentStatus() {
  return useFetch(() => api.getAgentStatus(), []);
}

// ============ AUDIT EVENTS ============

export function useAuditEvents(limit: number = 50) {
  return useFetch(() => api.getAuditEvents(limit), [limit]);
}

// ============ JANITOR WIZARD ============

export function useJanitorWizardHistory(limit: number = 1) {
  return useFetch(() => api.getJanitorWizardHistory(limit), [limit]);
}

// ============ COMBINED DASHBOARD DATA ============

export interface DashboardData {
  status: api.QuickStatus | null;
  tasks: api.Task[];
  bills: api.Bill[];
  messages: api.InboxMessage[];
  unreadCount: { gmail: number; whatsapp: number; total: number } | null;
  security: api.SecurityStatus | null;
  loading: boolean;
  error: Error | null;
  statusError: Error | null;
  tasksError: Error | null;
  billsError: Error | null;
  messagesError: Error | null;
  unreadError: Error | null;
  securityError: Error | null;
  degraded: boolean;
}

export function useDashboardData(
  refreshInterval: number = 30000,
  autoRefresh: boolean = true
): DashboardData & { refetch: () => void } {
  const status = useQuickStatus(autoRefresh ? refreshInterval : undefined);
  const tasks = useTasks({ status: "pending", limit: 10 });
  const bills = useBills(false);
  const messages = useInboxMessages({ limit: 10 });
  const unreadCount = useUnreadCount();
  const security = useSecurityStatus();

  const loading = status.loading || tasks.loading || bills.loading;
  const statusError = status.error || null;
  const tasksError = tasks.error || null;
  const billsError = bills.error || null;
  const messagesError = messages.error || null;
  const unreadError = unreadCount.error || null;
  const securityError = security.error || null;
  const error = statusError;
  const degraded = !statusError && Boolean(tasksError || billsError || messagesError || unreadError || securityError);

  const refetch = useCallback(() => {
    status.refetch();
    tasks.refetch();
    bills.refetch();
    messages.refetch();
    unreadCount.refetch();
    security.refetch();
  }, []);

  useEffect(() => {
    const handler = () => refetch();
    window.addEventListener("mycasa-system-sync", handler as EventListener);
    return () => window.removeEventListener("mycasa-system-sync", handler as EventListener);
  }, [refetch]);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      tasks.refetch();
      bills.refetch();
      messages.refetch();
      unreadCount.refetch();
      security.refetch();
    }, refreshInterval);
    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, tasks.refetch, bills.refetch, messages.refetch, unreadCount.refetch, security.refetch]);

  return {
    status: status.data,
    tasks: tasks.data || [],
    bills: bills.data || [],
    messages: messages.data || [],
    unreadCount: unreadCount.data,
    security: security.data,
    loading,
    error,
    statusError,
    tasksError,
    billsError,
    messagesError,
    unreadError,
    securityError,
    degraded,
    refetch,
  };
}
