"use client";

import { useState, useEffect } from "react";
import { Shell } from "@/components/layout/Shell";
import { Page } from "@/components/layout/Page";
import { LiveSystemDashboard } from "@/components/LiveSystemDashboard";
import { MemoryGraph } from "@/components/MemoryGraph";
import { SchedulerManager } from "@/components/SchedulerManager";
import { AgentManager } from "@/components/AgentManager";
import { AgentTimeline } from "@/components/AgentTimeline";
import { apiFetch, getJanitorWizardHistory, JanitorWizardRun } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";
import {
  Text,
  Tabs,
  Card,
  Stack,
  Group,
  Button,
  TextInput,
  NumberInput,
  Select,
  Badge,
  Alert,
  Paper,
  ThemeIcon,
  Divider,
  Modal,
  SimpleGrid,
  ActionIcon,
  Table,
  Progress,
  Skeleton,
  Grid,
  Loader
} from "@mantine/core";
import { 
  IconBrain, 
  IconChartLine, 
  IconWallet, 
  IconDatabase, 
  IconActivity, 
  IconClock, 
  IconRefresh,
  IconPlus,
  IconTrash,
  IconPencil,
  IconX,
  IconCheck,
  IconSparkles
} from "@tabler/icons-react";

// Define TypeScript interfaces
interface Holding {
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

interface PortfolioData {
  holdings: Holding[];
  total_value: number;
  cash: number;
  day_change?: number;
  day_change_pct?: number;
  last_updated?: string;
  source?: string;
}

export default function SystemPage() {
  // Portfolio state
  const [portfolio, setPortfolio] = useState<PortfolioData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // System monitor state
  const [systemMonitor, setSystemMonitor] = useState<any | null>(null);
  const [monitorLoading, setMonitorLoading] = useState(false);
  const [monitorError, setMonitorError] = useState<string | null>(null);

  // Janitor wizard summary
  const [janitorRun, setJanitorRun] = useState<JanitorWizardRun | null>(null);
  const [janitorLoading, setJanitorLoading] = useState(false);
  const [janitorError, setJanitorError] = useState<string | null>(null);
  
  // Add holding modal state
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [newTicker, setNewTicker] = useState("");
  const [newShares, setNewShares] = useState<number | "">(0);
  const [newAssetType, setNewAssetType] = useState("Tech");
  
  // Edit holding state
  const [editingHolding, setEditingHolding] = useState<Holding | null>(null);
  const [editTicker, setEditTicker] = useState("");
  const [editShares, setEditShares] = useState<number | "">("");
  const [editAssetType, setEditAssetType] = useState("");

  const fetchPortfolio = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<any>("/portfolio");
      setPortfolio(data);
      setNewCash(data.cash || 0);
    } catch (e) {
      setError("Failed to fetch portfolio");
    } finally {
      setLoading(false);
    }
  };

  const fetchSystemMonitor = async () => {
    setMonitorLoading(true);
    setMonitorError(null);
    try {
      const data = await apiFetch<any>("/api/system/monitor");
      setSystemMonitor(data);
    } catch (e) {
      setMonitorError("Failed to fetch system monitor");
    } finally {
      setMonitorLoading(false);
    }
  };

  const fetchJanitorWizard = async () => {
    setJanitorLoading(true);
    setJanitorError(null);
    try {
      const data = await getJanitorWizardHistory(1);
      setJanitorRun(data.runs?.[0] || null);
    } catch (e) {
      setJanitorError("Failed to fetch Janitor wizard");
    } finally {
      setJanitorLoading(false);
    }
  };

  useEffect(() => {
    fetchPortfolio();
    fetchSystemMonitor();
    fetchJanitorWizard();
  }, []);

  // Calculate total value
  const totalValue = portfolio?.holdings.reduce((sum, holding) => sum + holding.value, 0) || 0;
  const dayChangeValue =
    typeof portfolio?.day_change === "number"
      ? portfolio.day_change
      : portfolio?.holdings.reduce((sum, holding) => {
          const pct =
            typeof (holding as any).change_pct === "number"
              ? (holding as any).change_pct
              : typeof (holding as any).changePercent === "number"
                ? (holding as any).changePercent
                : null;
          if (pct === null || typeof holding.value !== "number") return sum;
          return sum + (holding.value * pct) / 100;
        }, 0) || 0;

  const dbInfo = systemMonitor?.database;
  const dbStatus = dbInfo?.status;
  const dbStatusLabel = dbStatus === "ok" ? "Connected" : dbStatus === "error" ? "Error" : "Unknown";
  const dbStatusColor = dbStatus === "ok" ? "green" : dbStatus === "error" ? "red" : "gray";

  // Asset type options for dropdowns
  const assetTypeOptions = [
    { value: "Tech", label: "Technology" },
    { value: "Healthcare", label: "Healthcare" },
    { value: "Finance", label: "Financial Services" },
    { value: "Energy", label: "Energy" },
    { value: "Consumer", label: "Consumer Goods" },
    { value: "Industrial", label: "Industrial" },
    { value: "Utilities", label: "Utilities" },
    { value: "Real Estate", label: "Real Estate" },
    { value: "Materials", label: "Materials" },
    { value: "Communication", label: "Communication Services" },
    { value: "Other", label: "Other" },
  ];

  const handleAddHolding = async () => {
    if (!newTicker || !newShares) return;
    
    try {
      await apiFetch("/portfolio/holdings", {
        method: "POST",
        body: JSON.stringify({
          ticker: newTicker,
          shares: parseFloat(newShares.toString()),
          asset_type: newAssetType
        })
      });
      
      setAddModalOpen(false);
      setNewTicker("");
      setNewShares(0);
      fetchPortfolio(); // Refresh portfolio
    } catch (e) {
      console.error("Failed to add holding:", e);
    }
  };

  const handleUpdateHolding = async () => {
    if (!editingHolding || !editTicker || editShares === "") return;
    
    try {
      await apiFetch(`/portfolio/holdings/${editingHolding.id}`, {
        method: "PUT",
        body: JSON.stringify({
          ticker: editTicker,
          shares: parseFloat(editShares.toString()),
          asset_type: editAssetType
        })
      });
      
      setEditingHolding(null);
      fetchPortfolio(); // Refresh portfolio
    } catch (e) {
      console.error("Failed to update holding:", e);
    }
  };

  const handleDeleteHolding = async (holdingId: number) => {
    try {
      await apiFetch(`/portfolio/holdings/${holdingId}`, {
        method: "DELETE"
      });
      
      fetchPortfolio(); // Refresh portfolio
    } catch (e) {
      console.error("Failed to delete holding:", e);
    }
  };

  // State for cash balance
  const [newCash, setNewCash] = useState(0);

  const handleUpdateCash = async () => {
    try {
      await apiFetch("/portfolio/cash", {
        method: "PUT",
        body: JSON.stringify({ cash: newCash })
      });
      
      fetchPortfolio(); // Refresh portfolio
    } catch (e) {
      console.error("Failed to update cash balance:", e);
    }
  };

  return (
    <Shell>
      {/* Add Holding Modal */}
      <Modal
        opened={addModalOpen}
        onClose={() => setAddModalOpen(false)}
        title={
          <Group gap="xs">
            <ThemeIcon size="sm" variant="light" color="green">
              <IconPlus size={14} />
            </ThemeIcon>
            <Text fw={600}>Add New Holding</Text>
          </Group>
        }
        centered
        size="md"
      >
        <Stack gap="md">
          <TextInput
            label="Ticker Symbol"
            placeholder="e.g., AAPL, MSFT, GOOGL"
            value={newTicker}
            onChange={(e) => setNewTicker(e.target.value.toUpperCase())}
            required
            description="Enter the stock ticker symbol"
          />
          <NumberInput
            label="Number of Shares"
            placeholder="0"
            value={newShares}
            onChange={(value) => setNewShares(value === '' ? '' : typeof value === 'string' ? parseFloat(value) || 0 : value)}
            min={0.0001}
            decimalScale={4}
            required
            description="Fractional shares are supported"
          />
          <Select
            label="Asset Type"
            value={newAssetType}
            onChange={(v) => setNewAssetType(v || "Tech")}
            data={assetTypeOptions}
            description="Category for allocation tracking"
          />
          <Divider my="xs" />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setAddModalOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleAddHolding}
              leftSection={<IconPlus size={14} />}
            >
              Add Holding
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Edit Holding Modal */}
      {editingHolding && (
        <Modal
          opened={!!editingHolding}
          onClose={() => setEditingHolding(null)}
          title={
            <Group gap="xs">
              <ThemeIcon size="sm" variant="light" color="blue">
                <IconPencil size={14} />
              </ThemeIcon>
              <Text fw={600}>Edit Holding: {editingHolding.ticker}</Text>
            </Group>
          }
          centered
          size="md"
        >
          <Stack gap="md">
            <TextInput
              label="Ticker Symbol"
              value={editTicker}
              onChange={(e) => setEditTicker(e.target.value.toUpperCase())}
              required
            />
            <NumberInput
              label="Number of Shares"
              value={editShares}
              onChange={(value) => setEditShares(value === '' ? '' : typeof value === 'string' ? parseFloat(value) || 0 : value)}
              min={0.0001}
              decimalScale={4}
              required
            />
            <Select
              label="Asset Type"
              value={editAssetType}
              onChange={(v) => setEditAssetType(v || "Tech")}
              data={assetTypeOptions}
            />
            <Divider my="xs" />
            <Group justify="flex-end">
              <Button 
                variant="default" 
                onClick={() => setEditingHolding(null)}
                leftSection={<IconX size={14} />}
              >
                Cancel
              </Button>
              <Button
                onClick={handleUpdateHolding}
                leftSection={<IconCheck size={14} />}
              >
                Update
              </Button>
            </Group>
          </Stack>
        </Modal>
      )}

      <Page
        title="Tasks & Logs"
        subtitle="Operational view of tasks, logs, agents, and system health"
        actions={
          <Button
            leftSection={<IconRefresh size={16} />}
            variant="light"
            onClick={() => {
              fetchPortfolio();
              fetchSystemMonitor();
              fetchJanitorWizard();
            }}
          >
            Refresh
          </Button>
        }
      >
        {monitorError && (
          <Alert color="red" title="System monitor unavailable" mb="md">
            {monitorError}
          </Alert>
        )}

        <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} mb="md">
          <Paper withBorder p="md" radius="lg">
            <Text size="xs" c="dimmed" tt="uppercase" fw={600}>System status</Text>
            <Group gap="xs" mt={6}>
              <Badge color={systemMonitor?.running ? "green" : "yellow"} variant="light">
                {systemMonitor?.running ? "Running" : "Stopped"}
              </Badge>
              <Text size="sm" fw={600}>
                {systemMonitor?.running ? "Healthy" : "Needs attention"}
              </Text>
            </Group>
            <Text size="xs" c="dimmed" mt={4}>
              Last activity: {systemMonitor?.last_activity ? new Date(systemMonitor.last_activity).toLocaleString() : "—"}
            </Text>
          </Paper>
          <Paper withBorder p="md" radius="lg">
            <Text size="xs" c="dimmed" tt="uppercase" fw={600}>Agents active</Text>
            <Text size="xl" fw={700} mt={6}>
              {systemMonitor?.resources?.agents_active ?? 0}
            </Text>
            <Text size="xs" c="dimmed">
              of {systemMonitor?.resources?.agents_total ?? 0} enabled
            </Text>
          </Paper>
          <Paper withBorder p="md" radius="lg">
            <Text size="xs" c="dimmed" tt="uppercase" fw={600}>Database</Text>
            <Group gap="xs" mt={6}>
              <Badge color={dbStatusColor} variant="light">{dbStatusLabel}</Badge>
              <Text size="sm" fw={600}>{dbInfo?.type || "unknown"}</Text>
            </Group>
            <Text size="xs" c="dimmed">
              Size: {dbInfo?.size_formatted || "—"}
            </Text>
          </Paper>
          <Paper withBorder p="md" radius="lg">
            <Text size="xs" c="dimmed" tt="uppercase" fw={600}>Last backup</Text>
            <Text size="xl" fw={700} mt={6}>
              {dbInfo?.last_backup ? dbInfo.last_backup : "—"}
            </Text>
            <Text size="xs" c="dimmed">
              {dbInfo?.last_backup ? "From local backups" : "No backups found"}
            </Text>
          </Paper>
        </SimpleGrid>

        <Card withBorder p="md" radius="lg" mb="md">
          <Group justify="space-between" align="center" wrap="wrap">
            <Group gap="sm">
              <ThemeIcon size="lg" variant="light" color="violet">
                <IconSparkles size={18} />
              </ThemeIcon>
              <div>
                <Text fw={600}>Janitor Audit Wizard</Text>
                <Text size="xs" c="dimmed">
                  {janitorLoading
                    ? "Loading last run..."
                    : janitorRun
                      ? `Last run: ${new Date(janitorRun.timestamp).toLocaleString()}`
                      : janitorError || "No wizard runs recorded"}
                </Text>
              </div>
            </Group>
            <Group gap="sm">
              {janitorLoading ? (
                <Loader size="sm" />
              ) : (
                <Badge color={janitorRun ? (janitorRun.health_score >= 80 ? "green" : janitorRun.health_score >= 50 ? "yellow" : "red") : "gray"}>
                  {janitorRun ? `${janitorRun.health_score}% health` : "Not run"}
                </Badge>
              )}
              <Button variant="light" onClick={() => window.location.assign("/janitor")}>
                Open Janitor
              </Button>
            </Group>
          </Group>
        </Card>

        <Tabs defaultValue="live">
          <Tabs.List mb="md">
            <Tabs.Tab value="live" leftSection={<IconChartLine size={16} />}>
              Live Overview
            </Tabs.Tab>
            <Tabs.Tab value="agents" leftSection={<IconBrain size={16} />}>
              Agent Fleet
            </Tabs.Tab>
            <Tabs.Tab value="portfolio" leftSection={<IconWallet size={16} />}>
              Portfolio Data
            </Tabs.Tab>
            <Tabs.Tab value="database" leftSection={<IconDatabase size={16} />}>
              Database
            </Tabs.Tab>
            <Tabs.Tab value="memory" leftSection={<IconBrain size={16} />}>
              Memory Graph
            </Tabs.Tab>
            <Tabs.Tab value="scheduler" leftSection={<IconClock size={16} />}>
              Scheduler
            </Tabs.Tab>
            <Tabs.Tab value="activity" leftSection={<IconActivity size={16} />}>
              Activity Map
            </Tabs.Tab>
          </Tabs.List>

          {/* Live Overview Tab - Real-time status of everything */}
          <Tabs.Panel value="live">
            <LiveSystemDashboard />
          </Tabs.Panel>

          {/* Agent Fleet Tab */}
          <Tabs.Panel value="agents">
            <Card withBorder p="lg" radius="md">
              <AgentManager />
            </Card>
          </Tabs.Panel>

          {/* Portfolio Data Tab */}
          <Tabs.Panel value="portfolio">
            <Stack gap="md">
              {error && (
                <Alert color="red">
                  {error}
                </Alert>
              )}
              {/* Summary Cards */}
              <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }}>
                <Paper withBorder p="md" radius="md">
                  <Text size="sm" c="dimmed">Total Portfolio Value</Text>
                  <div style={{ marginTop: '4px' }}>
                    <Text component="div" size="xl" fw={700}>
                      {loading ? <Skeleton height={24} width="60%" /> : formatCurrency(totalValue)}
                    </Text>
                  </div>
                </Paper>
                <Paper withBorder p="md" radius="md">
                  <Text size="sm" c="dimmed">Holdings Count</Text>
                  <div style={{ marginTop: '4px' }}>
                    <Text component="div" size="xl" fw={700}>
                      {loading ? <Skeleton height={24} width="60%" /> : portfolio?.holdings.length || 0}
                    </Text>
                  </div>
                </Paper>
                <Paper withBorder p="md" radius="md">
                  <Text size="sm" c="dimmed">Cash Balance</Text>
                  <div style={{ marginTop: '4px' }}>
                    <Text component="div" size="xl" fw={700}>
                      {loading ? <Skeleton height={24} width="60%" /> : formatCurrency(portfolio?.cash || 0)}
                    </Text>
                  </div>
                </Paper>
                <Paper withBorder p="md" radius="md">
                  <Text size="sm" c="dimmed">Today's Change</Text>
                  <div style={{ marginTop: '4px' }}>
                    <Text component="div" size="xl" fw={700} c={dayChangeValue >= 0 ? "green" : "red"}>
                      {loading ? (
                        <Skeleton height={24} width="60%" />
                      ) : portfolio ? (
                        `${dayChangeValue >= 0 ? "+" : ""}${formatCurrency(dayChangeValue)}`
                      ) : (
                        "—"
                      )}
                    </Text>
                  </div>
                </Paper>
              </SimpleGrid>

              {/* Cash Management */}
              <Card withBorder p="lg" radius="md">
                <Group justify="space-between">
                  <div>
                    <Text fw={600}>Cash Management</Text>
                    <Text size="sm" c="dimmed">Update your cash balance</Text>
                  </div>
                  <NumberInput
                    value={newCash}
                    onChange={(val) => setNewCash(typeof val === 'string' ? parseFloat(val) || 0 : val)}
                    placeholder="Enter cash amount"
                    w={200}
                  />
                  <Button onClick={handleUpdateCash}>Update</Button>
                </Group>
              </Card>

              {/* Holdings Table */}
              <Card withBorder p="lg" radius="md">
                <Group justify="space-between" mb="md">
                  <Text fw={600}>Portfolio Holdings</Text>
                  <Button 
                    leftSection={<IconPlus size={16} />} 
                    onClick={() => setAddModalOpen(true)}
                  >
                    Add Holding
                  </Button>
                </Group>
                
                {loading ? (
                  <Stack>
                    <Skeleton height={40} />
                    <Skeleton height={40} />
                    <Skeleton height={40} />
                  </Stack>
                ) : error ? (
                  <Alert color="red" title="Error">
                    {error}
                  </Alert>
                ) : (
                  <div style={{ overflowX: 'auto' }}>
                    <Table highlightOnHover>
                      <Table.Thead>
                        <Table.Tr>
                          <Table.Th>Ticker</Table.Th>
                          <Table.Th>Shares</Table.Th>
                          <Table.Th>Current Price</Table.Th>
                          <Table.Th>Total Value</Table.Th>
                          <Table.Th>Allocation</Table.Th>
                          <Table.Th>Actions</Table.Th>
                        </Table.Tr>
                      </Table.Thead>
                      <Table.Tbody>
                        {portfolio?.holdings.map((holding) => (
                          <Table.Tr key={holding.id}>
                            <Table.Td><Text fw={600}>{holding.ticker}</Text></Table.Td>
                            <Table.Td>{holding.shares.toFixed(4)}</Table.Td>
                            <Table.Td>{formatCurrency(holding.current_price)}</Table.Td>
                            <Table.Td fw={600}>{formatCurrency(holding.value)}</Table.Td>
                            <Table.Td>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <Progress 
                                  value={(holding.value / totalValue) * 100} 
                                  size="sm" 
                                  style={{ flex: 1 }}
                                />
                                <Text size="sm">{`${((holding.value / totalValue) * 100).toFixed(1)}%`}</Text>
                              </div>
                            </Table.Td>
                            <Table.Td>
                              <Group gap="xs">
                                <ActionIcon
                                  variant="subtle"
                                  color="blue"
                                  onClick={() => {
                                    setEditingHolding(holding);
                                    setEditTicker(holding.ticker);
                                    setEditShares(holding.shares);
                                    setEditAssetType(holding.asset_type);
                                  }}
                                >
                                  <IconPencil size={16} />
                                </ActionIcon>
                                <ActionIcon
                                  variant="subtle"
                                  color="red"
                                  onClick={() => handleDeleteHolding(holding.id)}
                                >
                                  <IconTrash size={16} />
                                </ActionIcon>
                              </Group>
                            </Table.Td>
                          </Table.Tr>
                        ))}
                      </Table.Tbody>
                    </Table>
                  </div>
                )}
              </Card>
            </Stack>
          </Tabs.Panel>

          {/* Database Tab */}
          <Tabs.Panel value="database">
            <Card withBorder p="lg" radius="md">
              <Text fw={600} mb="md">Database Status</Text>
              
              {monitorError && (
                <Alert color="red" mb="md">
                  {monitorError}
                </Alert>
              )}

              <Grid gutter="md">
                <Grid.Col span={{ base: 12, md: 6 }}>
                  <Paper withBorder p="md" radius="md">
                    <Group justify="space-between">
                      <Text size="sm">Database Connection</Text>
                      <Badge color={dbStatusColor} variant="light">
                        {monitorLoading ? "Checking..." : dbStatusLabel}
                      </Badge>
                    </Group>
                    <Text size="xs" c="dimmed" mt="xs">
                      {dbInfo?.type ? `${dbInfo.type} • ${dbInfo.url}` : "Connection details unavailable"}
                    </Text>
                  </Paper>
                </Grid.Col>
                
                <Grid.Col span={{ base: 12, md: 6 }}>
                  <Paper withBorder p="md" radius="md">
                    <Group justify="space-between">
                      <Text size="sm">Storage</Text>
                      <Badge color="blue" variant="light">
                        {dbInfo?.size_formatted || "—"}
                      </Badge>
                    </Group>
                    <Text size="xs" c="dimmed" mt="xs">
                      {dbInfo?.size_formatted ? "Database size" : "Size unavailable"}
                    </Text>
                  </Paper>
                </Grid.Col>
                
                <Grid.Col span={{ base: 12, md: 6 }}>
                  <Paper withBorder p="md" radius="md">
                    <Group justify="space-between">
                      <Text size="sm">Backups</Text>
                      <Badge color={dbInfo?.last_backup ? "green" : "gray"} variant="light">
                        {dbInfo?.last_backup ? "Available" : "None"}
                      </Badge>
                    </Group>
                    <Text size="xs" c="dimmed" mt="xs">
                      {dbInfo?.last_backup ? `Last backup: ${dbInfo.last_backup}` : "No backups recorded"}
                    </Text>
                  </Paper>
                </Grid.Col>
                
                <Grid.Col span={{ base: 12, md: 6 }}>
                  <Paper withBorder p="md" radius="md">
                    <Group justify="space-between">
                      <Text size="sm">Performance</Text>
                      <Badge color="gray" variant="light">Unknown</Badge>
                    </Group>
                    <Text size="xs" c="dimmed" mt="xs">Performance telemetry not configured</Text>
                  </Paper>
                </Grid.Col>
              </Grid>
              
              <Alert color="blue" icon={<IconDatabase size={16} />} mt="md">
                Data persists across sessions and server restarts. The database shown here is the configured source of truth.
              </Alert>
            </Card>
          </Tabs.Panel>

          {/* Memory Graph Tab - SecondBrain Knowledge Graph */}
          <Tabs.Panel value="memory">
            <MemoryGraph />
          </Tabs.Panel>

          {/* Scheduler Tab - Scheduled Agent Runs */}
          <Tabs.Panel value="scheduler">
            <SchedulerManager />
          </Tabs.Panel>

          {/* Activity Map Tab - HYPERCONTEXT-style activity dashboard */}
          <Tabs.Panel value="activity">
            <Stack gap="md">
              <Text size="sm" c="dimmed" mb="xs">
                Real-time activity tracking for all agents - files touched, tools used, decisions made, and context usage
              </Text>
              <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
                <AgentTimeline />
              </SimpleGrid>
            </Stack>
          </Tabs.Panel>
        </Tabs>
      </Page>
    </Shell>
  );
}
