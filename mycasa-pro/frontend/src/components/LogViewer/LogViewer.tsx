"use client";

import { useState, useEffect, useRef } from "react";
import { getApiBaseUrl } from "@/lib/api";
import {
  Box,
  Stack,
  Paper,
  Text,
  Group,
  Select,
  TextInput,
  Button,
  Badge,
  ScrollArea,
  ActionIcon,
  Tooltip,
  Alert,
} from "@mantine/core";
import {
  IconSearch,
  IconRefresh,
  IconDownload,
  IconAlertTriangle,
  IconLock,
} from "@tabler/icons-react";

const API_URL = getApiBaseUrl();

interface LogEntry {
  id: number;
  timestamp: string;
  level: string;
  agent: string;
  action: string;
  details: string;
  status: string;
}

export function LogViewer() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [filteredLogs, setFilteredLogs] = useState<LogEntry[]>([]);
  const [levelFilter, setLevelFilter] = useState<string>("all");
  const [agentFilter, setAgentFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [autoScroll, setAutoScroll] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const fetchLogs = async () => {
    try {
      const res = await fetch(`${API_URL}/api/audit/events?limit=100`);
      if (res.ok) {
        const data = await res.json();
        const logEntries: LogEntry[] = (data.events || []).map((e: any) => ({
          id: e.id,
          timestamp: e.created_at || e.timestamp,
          level: e.status || e.event_type,
          agent: e.source || e.agent || "system",
          action: e.event_type || e.action || "event",
          details: typeof e.payload === "string" ? e.payload : JSON.stringify(e.payload || e.details || {}),
          status: e.status || "info",
        }));
        setLogs(logEntries);
        setError(null);
      } else {
        setError(`Failed to fetch logs (HTTP ${res.status})`);
      }
    } catch (error) {
      console.error("Failed to fetch logs:", error);
      setError("Failed to connect to backend");
    }
  };

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    // Filter logs based on search query
    let filtered = logs;

    if (levelFilter !== "all") {
      filtered = filtered.filter((log) => log.level.toLowerCase() === levelFilter.toLowerCase());
    }

    if (agentFilter !== "all") {
      filtered = filtered.filter((log) => log.agent.toLowerCase() === agentFilter.toLowerCase());
    }

    if (searchQuery) {
      filtered = filtered.filter(
        (log) =>
          log.action.toLowerCase().includes(searchQuery.toLowerCase()) ||
          log.details.toLowerCase().includes(searchQuery.toLowerCase()) ||
          log.agent.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    setFilteredLogs(filtered);
  }, [logs, searchQuery, levelFilter, agentFilter]);

  useEffect(() => {
    // Auto-scroll to bottom
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [filteredLogs, autoScroll]);

  const getLevelColor = (level: string) => {
    switch (level.toLowerCase()) {
      case "error":
      case "critical":
        return "red";
      case "warning":
        return "orange";
      case "success":
        return "green";
      default:
        return "blue";
    }
  };

  const handleExport = () => {
    const logText = filteredLogs
      .map(
        (log) =>
          `[${log.timestamp}] [${log.level.toUpperCase()}] [${log.agent}] ${log.action}${
            log.details ? ` - ${log.details}` : ""
          }`
      )
      .join("\n");

    const blob = new Blob([logText], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `mycasa-logs-${new Date().toISOString()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Stack gap="md">
      {error && (
        <Alert icon={<IconAlertTriangle size={16} />} color="red" title="Logs unavailable" variant="light">
          {error}
        </Alert>
      )}
      {/* Filters */}
      <Paper p="md" withBorder>
        <Group justify="space-between" align="flex-end">
          <Group>
            <Select
              label="Level"
              data={[
                { value: "all", label: "All Levels" },
                { value: "info", label: "Info" },
                { value: "warning", label: "Warning" },
                { value: "error", label: "Error" },
              ]}
              value={levelFilter}
              onChange={(value) => setLevelFilter(value || "all")}
              style={{ width: 150 }}
            />

            <Select
              label="Agent"
              data={[
                { value: "all", label: "All Agents" },
                { value: "manager", label: "Manager" },
                { value: "finance", label: "Finance" },
                { value: "maintenance", label: "Maintenance" },
                { value: "contractors", label: "Contractors" },
                { value: "projects", label: "Projects" },
                { value: "janitor", label: "Janitor" },
                { value: "security", label: "Security" },
              ]}
              value={agentFilter}
              onChange={(value) => setAgentFilter(value || "all")}
              style={{ width: 180 }}
            />

            <TextInput
              label="Search"
              placeholder="Filter logs..."
              leftSection={<IconSearch size={16} />}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.currentTarget.value)}
              style={{ width: 250 }}
            />
          </Group>

          <Group>
            <Tooltip label="Refresh">
              <ActionIcon variant="light" onClick={fetchLogs}>
                <IconRefresh size={18} />
              </ActionIcon>
            </Tooltip>
            <Tooltip label="Export">
              <ActionIcon variant="light" onClick={handleExport}>
                <IconDownload size={18} />
              </ActionIcon>
            </Tooltip>
            <Tooltip label="Audit logs are immutable">
              <ActionIcon variant="light" color="gray" disabled>
                <IconLock size={18} style={{ opacity: 0.35 }} />
              </ActionIcon>
            </Tooltip>
          </Group>
        </Group>
      </Paper>

      {/* Log Stream */}
      <Paper p="md" withBorder>
        <Group justify="space-between" mb="md">
          <Group>
            <Text fw={600}>System Logs</Text>
            <Badge>{filteredLogs.length} entries</Badge>
          </Group>
          <Button
            size="xs"
            variant={autoScroll ? "filled" : "light"}
            onClick={() => setAutoScroll(!autoScroll)}
          >
            Auto-scroll: {autoScroll ? "ON" : "OFF"}
          </Button>
        </Group>

        <ScrollArea
          h={600}
          viewportRef={scrollRef}
          style={{
            background: "var(--surface-2)",
            border: "1px solid var(--border-1)",
            borderRadius: 8,
          }}
        >
          <Box p="md" style={{ fontFamily: "var(--font-mono, ui-monospace, SFMono-Regular, Menlo, monospace)", fontSize: "12px" }}>
            {filteredLogs.length === 0 ? (
              <Text c="dimmed" ta="center" py="xl">
                No logs to display
              </Text>
            ) : (
              <Stack gap={2}>
                {filteredLogs.map((log) => (
                  <Group key={log.id} gap="xs" wrap="nowrap">
                    <Text c="dimmed" size="xs" style={{ minWidth: 180 }}>
                      {new Date(log.timestamp).toLocaleString()}
                    </Text>
                    <Badge size="xs" color={getLevelColor(log.level)} style={{ minWidth: 60 }}>
                      {log.level}
                    </Badge>
                    <Badge size="xs" variant="light" style={{ minWidth: 100 }}>
                      {log.agent}
                    </Badge>
                    <Text size="xs" style={{ flex: 1 }}>
                      {log.action}
                    </Text>
                  </Group>
                ))}
              </Stack>
            )}
          </Box>
        </ScrollArea>
      </Paper>
    </Stack>
  );
}
