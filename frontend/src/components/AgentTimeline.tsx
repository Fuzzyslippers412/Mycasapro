"use client";

import { useState, useEffect } from "react";
import { getApiBaseUrl } from "@/lib/api";
import {
  Card,
  Text,
  Group,
  Badge,
  Stack,
  Timeline,
  Skeleton,
  Box,
  ActionIcon,
  Tooltip,
} from "@mantine/core";
import {
  IconRefresh,
  IconRobot,
  IconCoin,
  IconTool,
  IconShield,
  IconTrash,
  IconMail,
  IconCheck,
  IconAlertTriangle,
  IconClock,
  IconActivity,
} from "@tabler/icons-react";

const API_URL = getApiBaseUrl();

interface AgentEvent {
  id: string;
  agent: string;
  action: string;
  details?: string;
  status: "success" | "failed" | "pending";
  created_at: string;
}

const agentIcons: Record<string, React.ElementType> = {
  finance: IconCoin,
  maintenance: IconTool,
  security: IconShield,
  "security-manager": IconShield,
  janitor: IconTrash,
  mail: IconMail,
  "mail-skill": IconMail,
  backup: IconTrash,
  "backup-recovery": IconTrash,
  manager: IconRobot,
};

const agentColors: Record<string, string> = {
  finance: "green",
  maintenance: "blue",
  security: "red",
  "security-manager": "red",
  janitor: "orange",
  mail: "violet",
  "mail-skill": "violet",
  backup: "gray",
  "backup-recovery": "gray",
  manager: "indigo",
};

function formatTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  
  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  
  return date.toLocaleDateString();
}

export function AgentTimeline() {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const fetchEvents = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${API_URL}/api/telemetry/entries?limit=20&category=agent_task`);
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const data = await res.json();
      const mapped = (data.entries || []).map((e: any) => ({
        id: e.id,
        agent: e.source || "system",
        action: e.operation || "Activity",
        details: e.error || (e.metadata ? JSON.stringify(e.metadata) : undefined),
        status: e.status === "error" ? "failed" : "success",
        created_at: e.timestamp || new Date().toISOString(),
      }));
      setEvents(mapped);
    } catch (e) {
      setError((e as Error).message);
      setEvents([]);
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => {
    fetchEvents();
    const interval = setInterval(fetchEvents, 30000);
    return () => clearInterval(interval);
  }, []);
  
  if (loading && events.length === 0) {
    return (
      <Card withBorder padding="lg" radius="md">
        <Skeleton height={20} width={150} mb="md" />
        <Stack gap="md">
          {[1, 2, 3].map((i) => <Skeleton key={i} height={50} />)}
        </Stack>
      </Card>
    );
  }
  
  return (
    <Card withBorder padding="lg" radius="md" className="agent-timeline-card">
      <Group justify="space-between" mb="md">
        <Group gap="xs">
          <IconActivity size={16} style={{ color: "var(--mantine-color-dimmed)" }} />
          <Text fw={600}>Agent Activity</Text>
        </Group>
        <Tooltip label="Refresh">
          <ActionIcon variant="subtle" size="sm" onClick={fetchEvents} loading={loading}>
            <IconRefresh size={16} />
          </ActionIcon>
        </Tooltip>
      </Group>
      
      {events.length === 0 ? (
        <Box py="xl" style={{ textAlign: "center" }}>
          <IconClock size={40} stroke={1.5} style={{ color: "var(--mantine-color-dimmed)" }} />
          <Text c="dimmed" mt="sm" size="sm">No recent activity</Text>
        </Box>
      ) : (
        <Timeline active={events.length - 1} bulletSize={24} lineWidth={2}>
          {events.slice(0, 8).map((event) => {
            const Icon = agentIcons[event.agent] || IconRobot;
            const color = agentColors[event.agent] || "gray";
            
            return (
              <Timeline.Item
                key={event.id}
                bullet={<Icon size={12} />}
                color={event.status === "failed" ? "red" : color}
                title={
                  <Group gap="xs">
                    <Text size="sm" fw={500} tt="capitalize">{event.agent}</Text>
                    {event.status === "failed" && (
                      <Badge size="xs" color="red" variant="light">Failed</Badge>
                    )}
                    {event.status === "pending" && (
                      <Badge size="xs" color="yellow" variant="light">Pending</Badge>
                    )}
                  </Group>
                }
              >
                <Text size="xs" c="dimmed">{event.action}</Text>
                {event.details && (
                  <Text size="xs" c="dimmed" lineClamp={1}>{event.details}</Text>
                )}
                <Text size="xs" c="dimmed" mt={4}>{formatTime(event.created_at)}</Text>
              </Timeline.Item>
            );
          })}
        </Timeline>
      )}
    </Card>
  );
}
