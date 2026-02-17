"use client";

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from "react";
import { getApiBaseUrl } from "@/lib/api";

const API_URL = getApiBaseUrl();

// ============ TYPES ============
export interface SystemStatus {
  backendOnline: boolean;
  agentsActive: number;
  agentsTotal: number;
  tasksCompleted: number;
  tasksPending: number;
  errors: number;
  costToday: number;
  lastCheck: Date;
  message: string;
}

interface StatusContextType {
  status: SystemStatus;
  loading: boolean;
  refresh: () => Promise<void>;
  launchAgents: () => Promise<boolean>;
}

// ============ DEFAULT STATUS ============
const defaultStatus: SystemStatus = {
  backendOnline: false,
  agentsActive: 0,
  agentsTotal: 6,
  tasksCompleted: 0,
  tasksPending: 0,
  errors: 0,
  costToday: 0,
  lastCheck: new Date(),
  message: "Checking backend...",
};

// ============ CONTEXT ============
const StatusContext = createContext<StatusContextType>({
  status: defaultStatus,
  loading: true,
  refresh: async () => {},
  launchAgents: async () => false,
});

// ============ PROVIDER ============
export function StatusProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<SystemStatus>(defaultStatus);
  const [loading, setLoading] = useState(true);

  const checkStatus = useCallback(async () => {
    try {
      // Check health first
      const healthRes = await fetch(`${API_URL}/health`, { 
        signal: AbortSignal.timeout(3000) 
      });
      
      if (!healthRes.ok) {
        setStatus(prev => ({
          ...prev,
          backendOnline: false,
          message: "Backend not responding",
          lastCheck: new Date(),
        }));
        return;
      }

      // Get system monitor data
      const monitorRes = await fetch(`${API_URL}/api/system/monitor`);
      if (monitorRes.ok) {
        const data = await monitorRes.json();
        const resources = data.resources || {};
        const processes = data.processes || [];
        
        // Count completed tasks from processes
        const completed = processes.reduce((sum: number, p: any) => 
          sum + (p.completed || 0), 0);
        
        setStatus({
          backendOnline: true,
          agentsActive: resources.agents_active || 0,
          agentsTotal: resources.agents_total || 6,
          tasksCompleted: completed,
          tasksPending: processes.reduce((sum: number, p: any) => 
            sum + (p.pending_tasks || 0), 0),
          errors: processes.reduce((sum: number, p: any) => 
            sum + (p.error_count || 0), 0),
          costToday: resources.cost_today || 0,
          lastCheck: new Date(),
          message: resources.agents_active > 0 
            ? `${resources.agents_active}/${resources.agents_total} agents running` 
            : "System idle - click 🚀 to launch agents",
        });
      }
    } catch (e) {
      setStatus(prev => ({
        ...prev,
        backendOnline: false,
        message: "Backend offline",
        lastCheck: new Date(),
      }));
    } finally {
      setLoading(false);
    }
  }, []);

  const launchAgents = useCallback(async (): Promise<boolean> => {
    try {
      const res = await fetch(`${API_URL}/system/launch`, { method: "POST" });
      if (res.ok) {
        // Refresh status after launch
        await checkStatus();
        return true;
      }
      return false;
    } catch {
      return false;
    }
  }, [checkStatus]);

  // Initial check and periodic refresh
  useEffect(() => {
    checkStatus();
    const interval = setInterval(checkStatus, 10000); // Every 10 seconds
    return () => clearInterval(interval);
  }, [checkStatus]);

  return (
    <StatusContext.Provider value={{ status, loading, refresh: checkStatus, launchAgents }}>
      {children}
    </StatusContext.Provider>
  );
}

// ============ HOOK ============
export function useStatus() {
  return useContext(StatusContext);
}

// ============ STATUS BADGE COMPONENT ============
export function StatusBadge({ compact = false }: { compact?: boolean }) {
  const { status, loading } = useStatus();

  if (loading) {
    return null;
  }

  if (!status.backendOnline) {
    return (
      <span style={{ 
        display: "inline-flex", 
        alignItems: "center", 
        gap: 4,
        color: "var(--mantine-color-red-6)",
        fontSize: compact ? 12 : 14,
      }}>
        <span style={{ 
          width: 8, 
          height: 8, 
          borderRadius: "50%", 
          background: "var(--mantine-color-red-6)",
        }} />
        {!compact && "Offline"}
      </span>
    );
  }

  if (status.agentsActive === 0) {
    return (
      <span style={{ 
        display: "inline-flex", 
        alignItems: "center", 
        gap: 4,
        color: "var(--mantine-color-yellow-6)",
        fontSize: compact ? 12 : 14,
      }}>
        <span style={{ 
          width: 8, 
          height: 8, 
          borderRadius: "50%", 
          background: "var(--mantine-color-yellow-6)",
        }} />
        {!compact && "Idle"}
      </span>
    );
  }

  return (
    <span style={{ 
      display: "inline-flex", 
      alignItems: "center", 
      gap: 4,
      color: "var(--mantine-color-green-6)",
      fontSize: compact ? 12 : 14,
    }}>
      <span style={{ 
        width: 8, 
        height: 8, 
        borderRadius: "50%", 
        background: "var(--mantine-color-green-6)",
      }} />
      {!compact && `${status.agentsActive}/${status.agentsTotal} Active`}
    </span>
  );
}
