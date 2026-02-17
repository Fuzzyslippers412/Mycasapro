"use client";

import { useState, useEffect, useCallback } from "react";
import { getApiBaseUrl } from "@/lib/api";
import {
  Card,
  Group,
  Stack,
  Text,
  Badge,
  SimpleGrid,
  ThemeIcon,
  Paper,
  Title,
  ActionIcon,
  Tooltip,
  Box,
  Loader,
  Alert,
  Button,
  Modal,
  TextInput,
  Divider,
  Center,
  Tabs,
} from "@mantine/core";
import {
  IconRefresh,
  IconPlugConnected,
  IconPlugConnectedX,
  IconSettings,
  IconCheck,
  IconX,
  IconExternalLink,
  IconTestPipe,
} from "@tabler/icons-react";

const API_URL = getApiBaseUrl();

interface Connector {
  id: string;
  name: string;
  description: string;
  category: string;
  icon: string;
  status: string;
  config_required: string[];
  config_values: Record<string, any>;
  health: string | null;
  stats: Record<string, any>;
}

interface MarketplaceData {
  connectors: Connector[];
  by_category: Record<string, Connector[]>;
  stats: {
    total: number;
    connected: number;
    installed: number;
  };
}

const STATUS_COLORS: Record<string, string> = {
  connected: "green",
  configured: "blue",
  installed: "yellow",
  not_installed: "gray",
  error: "red",
};

const CATEGORY_ICONS: Record<string, string> = {
  messaging: "💬",
  email: "📧",
  calendar: "📅",
  finance: "💰",
  smart_home: "🏠",
  security: "🔒",
};

function ConnectorCard({ 
  connector, 
  onConfigure,
  onTest,
}: { 
  connector: Connector;
  onConfigure: () => void;
  onTest: () => void;
}) {
  const isConnected = connector.status === "connected";
  const statusColor = STATUS_COLORS[connector.status] || "gray";
  
  return (
    <Card withBorder p="md" radius="md">
      <Group justify="space-between" mb="sm">
        <Group gap="sm">
          <Text size="xl">{connector.icon}</Text>
          <div>
            <Text fw={600}>{connector.name}</Text>
            <Badge size="xs" color={statusColor} variant="light">
              {connector.status.replace("_", " ")}
            </Badge>
          </div>
        </Group>
        <Group gap="xs">
          {connector.config_required.length > 0 && (
            <Tooltip label="Configure">
              <ActionIcon variant="light" onClick={onConfigure}>
                <IconSettings size={16} />
              </ActionIcon>
            </Tooltip>
          )}
          <Tooltip label="Test Connection">
            <ActionIcon 
              variant="light" 
              color={isConnected ? "green" : "gray"}
              onClick={onTest}
            >
              <IconTestPipe size={16} />
            </ActionIcon>
          </Tooltip>
        </Group>
      </Group>
      
      <Text size="sm" c="dimmed" mb="sm">
        {connector.description}
      </Text>
      
      {connector.health && connector.status !== "not_installed" && (
        <Group gap="xs">
          <ThemeIcon size="xs" color={isConnected ? "green" : "red"} variant="light">
            {isConnected ? <IconCheck size={10} /> : <IconX size={10} />}
          </ThemeIcon>
          <Text size="xs" c="dimmed">
            {connector.health}
          </Text>
        </Group>
      )}
      
      {Object.keys(connector.stats).length > 0 && (
        <Group gap="xs" mt="xs">
          {Object.entries(connector.stats).map(([key, value]) => (
            <Badge key={key} size="xs" variant="outline">
              {key}: {value}
            </Badge>
          ))}
        </Group>
      )}
    </Card>
  );
}

export function ConnectorMarketplace() {
  const [data, setData] = useState<MarketplaceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [configModal, setConfigModal] = useState<Connector | null>(null);
  const [testResult, setTestResult] = useState<{ id: string; passed: boolean } | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/connectors/marketplace`);
      if (res.ok) {
        const result = await res.json();
        setData(result);
        setError(null);
      } else {
        setError("Failed to fetch connectors");
      }
    } catch (e) {
      setError("Backend offline");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleTest = async (connectorId: string) => {
    try {
      const res = await fetch(`${API_URL}/api/connectors/marketplace/${connectorId}/test`, {
        method: "POST",
      });
      if (res.ok) {
        const result = await res.json();
        setTestResult({ id: connectorId, passed: result.test_passed });
        // Refresh after test
        fetchData();
      }
    } catch (e) {
      setTestResult({ id: connectorId, passed: false });
    }
  };

  if (loading && !data) {
    return (
      <Center py="xl">
        <Stack align="center" gap="md">
          <Loader size="lg" />
          <Text c="dimmed">Loading connectors...</Text>
        </Stack>
      </Center>
    );
  }

  if (error && !data) {
    return (
      <Alert color="red" icon={<IconPlugConnectedX />} title="Error">
        {error}
      </Alert>
    );
  }

  if (!data) return null;

  const categories = Object.keys(data.by_category);

  return (
    <Stack gap="md">
      {/* Header */}
      <Group justify="space-between">
        <Group gap="xs">
          <ThemeIcon size="lg" variant="light" color="green">
            <IconPlugConnected size={20} />
          </ThemeIcon>
          <div>
            <Text fw={600}>Connector Marketplace</Text>
            <Text size="xs" c="dimmed">
              {data.stats.connected}/{data.stats.total} connected
            </Text>
          </div>
        </Group>
        <Tooltip label="Refresh">
          <ActionIcon variant="light" onClick={fetchData} loading={loading}>
            <IconRefresh size={18} />
          </ActionIcon>
        </Tooltip>
      </Group>

      {/* Stats */}
      <SimpleGrid cols={{ base: 3 }}>
        <Paper p="sm" withBorder radius="md">
          <Text size="xs" c="dimmed">Total</Text>
          <Text size="xl" fw={700}>{data.stats.total}</Text>
        </Paper>
        <Paper p="sm" withBorder radius="md">
          <Text size="xs" c="dimmed">Connected</Text>
          <Text size="xl" fw={700} c="green">{data.stats.connected}</Text>
        </Paper>
        <Paper p="sm" withBorder radius="md">
          <Text size="xs" c="dimmed">Available</Text>
          <Text size="xl" fw={700} c="gray">{data.stats.total - data.stats.connected}</Text>
        </Paper>
      </SimpleGrid>

      {/* Connectors by Category */}
      <Tabs defaultValue={categories[0]}>
        <Tabs.List mb="md">
          {categories.map(cat => (
            <Tabs.Tab 
              key={cat} 
              value={cat}
              leftSection={<Text size="sm">{CATEGORY_ICONS[cat] || "📦"}</Text>}
            >
              {cat.replace("_", " ")} ({data.by_category[cat].length})
            </Tabs.Tab>
          ))}
        </Tabs.List>

        {categories.map(cat => (
          <Tabs.Panel key={cat} value={cat}>
            <SimpleGrid cols={{ base: 1, sm: 2 }}>
              {data.by_category[cat].map(connector => (
                <ConnectorCard
                  key={connector.id}
                  connector={connector}
                  onConfigure={() => setConfigModal(connector)}
                  onTest={() => handleTest(connector.id)}
                />
              ))}
            </SimpleGrid>
          </Tabs.Panel>
        ))}
      </Tabs>

      {/* Test Result Notification */}
      {testResult && (
        <Alert 
          color={testResult.passed ? "green" : "red"} 
          title={testResult.passed ? "Connection Successful" : "Connection Failed"}
          withCloseButton
          onClose={() => setTestResult(null)}
        >
          {testResult.passed 
            ? `${testResult.id} is connected and working!`
            : `${testResult.id} connection test failed. Check configuration.`
          }
        </Alert>
      )}

      {/* Configuration Modal */}
      <Modal
        opened={!!configModal}
        onClose={() => setConfigModal(null)}
        title={configModal ? `Configure ${configModal.name}` : ""}
      >
        {configModal && (
          <Stack gap="md">
            <Text size="sm" c="dimmed">{configModal.description}</Text>
            
            {configModal.config_required.length > 0 ? (
              <>
                <Divider label="Required Configuration" />
                {configModal.config_required.map(field => (
                  <TextInput
                    key={field}
                    label={field.replace("_", " ").replace(/\b\w/g, l => l.toUpperCase())}
                    placeholder={`Enter ${field}`}
                  />
                ))}
                <Button leftSection={<IconCheck size={16} />}>
                  Save Configuration
                </Button>
              </>
            ) : (
              <Alert color="blue">
                This connector is managed automatically. No configuration needed.
              </Alert>
            )}
          </Stack>
        )}
      </Modal>
    </Stack>
  );
}
