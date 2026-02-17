"use client";

import { createContext, useContext, useState, useCallback, ReactNode } from "react";

interface Agent {
  id: string;
  displayName: string;
  name: string;
  emoji: string;
  color: string;
}

// Agent definitions for reference
export const AGENTS: Agent[] = [
  { id: "manager", displayName: "Galidima", name: "Manager", emoji: "🏠", color: "violet" },
  { id: "finance", displayName: "Mamadou", name: "Finance Manager", emoji: "💰", color: "teal" },
  { id: "maintenance", displayName: "Ousmane", name: "Maintenance Manager", emoji: "🔧", color: "blue" },
  { id: "security", displayName: "Aïcha", name: "Security Manager", emoji: "🛡️", color: "red" },
  { id: "contractors", displayName: "Malik", name: "Contractors Manager", emoji: "👷", color: "orange" },
  { id: "projects", displayName: "Zainab", name: "Projects Manager", emoji: "📋", color: "grape" },
  { id: "janitor", displayName: "Salimata", name: "Janitor", emoji: "🧹", color: "cyan" },
  { id: "mail-skill", displayName: "Amina", name: "Mail Agent", emoji: "✉️", color: "violet" },
  { id: "backup-recovery", displayName: "Backup", name: "Backup & Recovery", emoji: "🗄️", color: "gray" },
];

interface AgentContextValue {
  // Currently targeted agent (null = manager/default)
  targetAgent: Agent | null;
  // Select an agent to talk to
  selectAgent: (agentId: string | null, options?: { greet?: boolean }) => void;
  // Clear agent selection (back to manager)
  clearAgent: () => void;
  // Send a message to the console with optional agent targeting
  sendToConsole: (message: string, agentId?: string) => void;
  // Get agent by ID
  getAgent: (id: string) => Agent | undefined;
  // Focus the console input
  focusConsole: () => void;
  // Whether the console should be focused
  shouldFocusConsole: boolean;
  setShouldFocusConsole: (v: boolean) => void;
}

const AgentContext = createContext<AgentContextValue | undefined>(undefined);

export function AgentProvider({ children }: { children: ReactNode }) {
  const [targetAgent, setTargetAgent] = useState<Agent | null>(null);
  const [shouldFocusConsole, setShouldFocusConsole] = useState(false);

  const getAgent = useCallback((id: string) => {
    return AGENTS.find(a => a.id === id);
  }, []);

  const selectAgent = useCallback((agentId: string | null, options?: { greet?: boolean }) => {
    if (agentId === null || agentId === "manager") {
      setTargetAgent(null);
    } else {
      const agent = AGENTS.find(a => a.id === agentId);
      setTargetAgent(agent || null);

      // Auto-send greeting to agent for immediate feedback
      if (agent && options?.greet !== false) {
        setTimeout(() => {
          const event = new CustomEvent("galidima-chat-send", {
            detail: {
              message: `Hello ${agent.displayName}! I want to talk to you.`,
              source: "agent-selection",
              agentId: agent.id
            }
          });
          window.dispatchEvent(event);
        }, 300); // Small delay to let UI update first
      }
    }
    setShouldFocusConsole(true);
  }, []);

  const clearAgent = useCallback(() => {
    setTargetAgent(null);
  }, []);

  const focusConsole = useCallback(() => {
    setShouldFocusConsole(true);
  }, []);

  const sendToConsole = useCallback((message: string, agentId?: string) => {
    // If an agentId is provided, select that agent first
    if (agentId && agentId !== "manager") {
      const agent = AGENTS.find(a => a.id === agentId);
      if (agent) {
        setTargetAgent(agent);
      }
    }
    
    // Dispatch event to SystemConsole
    const event = new CustomEvent("galidima-chat-send", {
      detail: { message, source: "agent-context", agentId }
    });
    window.dispatchEvent(event);
  }, []);

  return (
    <AgentContext.Provider
      value={{
        targetAgent,
        selectAgent,
        clearAgent,
        sendToConsole,
        getAgent,
        focusConsole,
        shouldFocusConsole,
        setShouldFocusConsole,
      }}
    >
      {children}
    </AgentContext.Provider>
  );
}

export function useAgentContext() {
  const context = useContext(AgentContext);
  if (!context) {
    throw new Error("useAgentContext must be used within an AgentProvider");
  }
  return context;
}
