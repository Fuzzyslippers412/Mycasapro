"use client";

import { useState } from "react";
import {
  Group,
  Badge,
  Text,
  Tooltip,
  ActionIcon,
  Box,
  Menu,
  Loader,
} from "@mantine/core";
import {
  IconPower,
  IconSettings,
} from "@tabler/icons-react";
import Link from "next/link";
import { useSystemStatus } from "@/lib/useSystemStatus";

interface SystemStatusBarProps {
  compact?: boolean;
  showCost?: boolean;
  showActions?: boolean;
}

export function SystemStatusBar({
  compact = false,
  showCost = true,
  showActions = true,
}: SystemStatusBarProps) {
  const {
    agentsActive,
    agentsAvailable,
    agentsTotal,
    systemRunning,
    isConnected,
    loading,
    launchSystem,
  } = useSystemStatus();
  const [actionLoading, setActionLoading] = useState(false);
  const onlineCount = agentsActive + agentsAvailable;

  const handleToggle = async () => {
    setActionLoading(true);
    try {
      await launchSystem();
    } finally {
      setActionLoading(false);
    }
  };

  // Status colors
  const getStatusColor = () => {
    if (isConnected === false) return "red";
    if (systemRunning) return "green";
    return "gray";
  };

  const getStatusLabel = () => {
    if (isConnected === false) return "Offline";
    if (systemRunning) return "Online";
    return "Stopped";
  };

  if (loading) {
    return (
      <Group gap="xs">
        <Loader size="xs" />
        <Text size="xs" c="dimmed">Loading...</Text>
      </Group>
    );
  }

  if (compact) {
    return (
      <Group gap="xs">
        <Tooltip label={getStatusLabel()}>
          <Badge
            size="sm"
            variant="dot"
            color={getStatusColor()}
          >
            {systemRunning ? "ON" : "OFF"}
          </Badge>
        </Tooltip>
        <Tooltip
          label={
            agentsTotal > 0
              ? `${onlineCount} / ${agentsTotal} agents online`
              : "No agents enabled"
          }
        >
          <Badge
            size="sm"
            variant="light"
            color="blue"
          >
            {onlineCount}/{agentsTotal}
          </Badge>
        </Tooltip>
      </Group>
    );
  }

  return (
    <Box>
      <Group gap="md" wrap="nowrap">
        {/* Connection Status */}
        <Tooltip label="Backend connection status">
          <Badge
            size="lg"
            variant="dot"
            color={isConnected ? "blue" : "red"}
          >
            {isConnected ? "Connected" : "Offline"}
          </Badge>
        </Tooltip>

        {/* System Status */}
        <Tooltip label={`System is ${getStatusLabel().toLowerCase()}`}>
          <Badge
            size="lg"
            variant="dot"
            color={getStatusColor()}
          >
            {getStatusLabel()}
          </Badge>
        </Tooltip>

        {/* Agent Count */}
        {isConnected && agentsTotal > 0 && (
          <Tooltip label={`${onlineCount} / ${agentsTotal} agents online`}>
            <Badge size="lg" variant="light" color="indigo">
              {onlineCount}/{agentsTotal}
            </Badge>
          </Tooltip>
        )}

        {/* Actions */}
        {showActions && (
          <Group gap="xs">
            <Menu shadow="md" width={200}>
              <Menu.Target>
                <Tooltip label={systemRunning ? "System running" : "Launch system"}>
                  <ActionIcon
                    variant={systemRunning ? "light" : "gradient"}
                    gradient={systemRunning ? undefined : { from: "indigo", to: "violet" }}
                    color={systemRunning ? "green" : undefined}
                    loading={actionLoading}
                    disabled={isConnected === false}
                    onClick={systemRunning ? undefined : handleToggle}
                  >
                    <IconPower size={16} />
                  </ActionIcon>
                </Tooltip>
              </Menu.Target>
              {systemRunning && (
                <Menu.Dropdown>
                  <Menu.Label>System Controls</Menu.Label>
                  <Link href="/system" style={{ textDecoration: "none" }}>
                    <Menu.Item leftSection={<IconSettings size={14} />}>
                      System Settings
                    </Menu.Item>
                  </Link>
                </Menu.Dropdown>
              )}
            </Menu>
          </Group>
        )}
      </Group>
    </Box>
  );
}
