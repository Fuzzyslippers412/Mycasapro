import { useState, useEffect, useCallback, useRef } from 'react';
import { apiFetch } from './api';

export interface AgentLiveDetails {
  status: string;
  pendingTasks: number;
  errors: number;
  loaded: boolean;
}

export interface UseSystemStatusReturn {
  agentsActive: number;
  agentsAvailable: number;
  agentsTotal: number;
  systemRunning: boolean;
  isConnected: boolean | null;
  loading: boolean;
  launchSystem: () => Promise<boolean>;
  startAgent: (id: string) => Promise<boolean>;
  agents: Record<string, string>;
  agentDetails: Record<string, AgentLiveDetails>;
}

export function useSystemStatus(): UseSystemStatusReturn {
  const [agentsActive, setAgentsActive] = useState(0);
  const [agentsAvailable, setAgentsAvailable] = useState(0);
  const [agentsTotal, setAgentsTotal] = useState(0);
  const [systemRunning, setSystemRunning] = useState(false);
  const [agents, setAgents] = useState<Record<string, string>>({});
  const [agentDetails, setAgentDetails] = useState<Record<string, AgentLiveDetails>>({});
  const [isConnected, setIsConnected] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);
  const backoffRef = useRef(10000);

  const fetchStatus = useCallback(async () => {
    try {
      const data = await apiFetch<any>(`/api/system/live`);
      setIsConnected(true);
      const stats = data.agents?.stats || {};
      const activeCount = typeof stats.active === "number" ? stats.active : 0;
      const availableCount = typeof stats.available === "number" ? stats.available : 0;
      const totalCount = typeof stats.total === "number" ? stats.total : 0;
      const runningFlag = typeof stats.running === "boolean"
        ? stats.running
        : Boolean(data.running);
      setAgentsActive(activeCount);
      setAgentsAvailable(availableCount);
      setAgentsTotal(totalCount);
      setSystemRunning(runningFlag);
      const rawAgents = data.agents?.agents || {};
      const normalized: Record<string, string> = {};
      const details: Record<string, AgentLiveDetails> = {};
      Object.entries(rawAgents).forEach(([id, a]: any) => {
        const status =
          typeof a === "string"
            ? a
            : a.status || (a.running ? "running" : a.enabled ? "idle" : "offline");
        normalized[id] = status;
        if (typeof a === "object" && a !== null) {
          details[id] = {
            status,
            pendingTasks: a.pending_tasks ?? a.pendingTasks ?? 0,
            errors: a.errors ?? a.error_count ?? 0,
            loaded: Boolean(a.loaded ?? a.running),
          };
        } else {
          details[id] = { status, pendingTasks: 0, errors: 0, loaded: false };
        }
      });
      setAgents(normalized);
      setAgentDetails(details);
      backoffRef.current = 10000;
    } catch {
      setIsConnected(false);
      setSystemRunning(false);
      backoffRef.current = Math.min(backoffRef.current * 1.5, 60000);
    } finally {
      setLoading(false);
    }
  }, []);

  const launchSystem = useCallback(async () => {
    try {
      await apiFetch(`/api/system/startup`, { method: 'POST' });
      await fetchStatus();
      return true;
    } catch {
      return false;
    }
  }, [fetchStatus]);

  const startAgent = useCallback(async (agentId: string) => {
    try {
      await apiFetch(`/api/system/agents/${agentId}/start`, { method: 'POST' });
      await fetchStatus();
      return true;
    } catch {
      return false;
    }
  }, [fetchStatus]);

  useEffect(() => {
    let timeout: any;
    const tick = async () => {
      if (document.visibilityState === 'visible') {
        await fetchStatus();
      }
      timeout = setTimeout(tick, backoffRef.current);
    };
    tick();
    return () => clearTimeout(timeout);
  }, [fetchStatus]);

  useEffect(() => {
    const handler = () => {
      fetchStatus();
    };
    window.addEventListener("mycasa-system-sync", handler as EventListener);
    return () => window.removeEventListener("mycasa-system-sync", handler as EventListener);
  }, [fetchStatus]);

  return {
    agentsActive,
    agentsAvailable,
    agentsTotal,
    systemRunning,
    agents,
    agentDetails,
    isConnected,
    loading,
    launchSystem,
    startAgent,
  };
}
