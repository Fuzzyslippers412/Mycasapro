"use client";

import { useEffect, useState, useMemo } from "react";
import { Shell } from "@/components/layout/Shell";
import { Page } from "@/components/layout/Page";
import { StatCard } from "@/components/widgets/WidgetCard";
import { WidgetTable } from "@/components/widgets/WidgetTable";
import { apiFetch } from "@/lib/api";
import {
  Stack,
  Group,
  Badge,
  Button,
  Text,
  SimpleGrid,
  Alert,
  Card,
  Box,
  ThemeIcon,
  Grid,
  Modal,
  TextInput,
  NumberInput,
  Select,
  Skeleton,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import {
  IconRefresh,
  IconAlertTriangle,
  IconWallet,
  IconCash,
  IconChartPie,
  IconPlus,
  IconCoins,
  IconChartBar,
} from "@tabler/icons-react";
import { tokens } from "@/theme/tokens";

interface Holding {
  ticker: string;
  shares: number;
  asset_type?: string;
  type?: string;
  price?: number;
  value?: number;
  change_pct?: number;
  changePercent?: number;
}

interface PortfolioData {
  holdings: Holding[];
  total_value: number;
  cash: number;
  last_updated?: string;
  source?: string;
}

// Simple pie chart component
function AllocationChart({ holdings }: { holdings: Holding[] }) {
  // Group by asset type
  const allocation = useMemo(() => {
    const grouped: Record<string, number> = {};
    let total = 0;

    holdings.forEach((h) => {
      const type = h.asset_type || h.type || "Uncategorized";
      const value = typeof h.value === "number" ? h.value : 0;
      if (!Number.isFinite(value)) return;
      grouped[type] = (grouped[type] || 0) + value;
      total += value;
    });

    const colors = [
      tokens.colors.primary[500],
      tokens.colors.success[500],
      tokens.colors.warn[500],
      tokens.colors.info[500],
      tokens.colors.accent[500],
      tokens.colors.error[500],
    ];

    return Object.entries(grouped).map(([type, value], index) => ({
      type,
      value,
      percentage: total > 0 ? (value / total) * 100 : 0,
      color: colors[index % colors.length],
    }));
  }, [holdings]);

  // Create SVG pie chart
  const createPieSlices = () => {
    let currentAngle = 0;
    const slices = allocation.map((item) => {
      const startAngle = currentAngle;
      const angle = (item.percentage / 100) * 360;
      currentAngle += angle;

      const startRad = ((startAngle - 90) * Math.PI) / 180;
      const endRad = ((startAngle + angle - 90) * Math.PI) / 180;

      const x1 = 50 + 40 * Math.cos(startRad);
      const y1 = 50 + 40 * Math.sin(startRad);
      const x2 = 50 + 40 * Math.cos(endRad);
      const y2 = 50 + 40 * Math.sin(endRad);

      const largeArcFlag = angle > 180 ? 1 : 0;

      return {
        ...item,
        path: `M 50 50 L ${x1} ${y1} A 40 40 0 ${largeArcFlag} 1 ${x2} ${y2} Z`,
      };
    });

    return slices;
  };

  const slices = createPieSlices();

  if (holdings.length === 0) {
    return (
      <Stack align="center" py="xl">
        <IconChartPie
          size={48}
          style={{
            color: "var(--mantine-color-dimmed)",
          }}
        />
        <Text size="sm" c="dimmed">
          No holdings to display
        </Text>
      </Stack>
    );
  }

  return (
    <Stack gap="md">
      <Group justify="center">
        <svg width="160" height="160" viewBox="0 0 100 100">
          {slices.map((slice, index) => (
            <path key={index} d={slice.path} fill={slice.color} stroke="white" strokeWidth="1" />
          ))}
          {/* Center circle for donut effect */}
          <circle
            cx="50"
            cy="50"
            r="25"
            fill="var(--mantine-color-body)"
          />
        </svg>
      </Group>

      <Stack gap="xs">
        {allocation.map((item) => (
          <Group key={item.type} justify="space-between">
            <Group gap="xs">
              <Box
                style={{
                  width: 12,
                  height: 12,
                  borderRadius: 3,
                  backgroundColor: item.color,
                }}
              />
              <Text size="sm">{item.type}</Text>
            </Group>
            <Group gap="xs">
              <Text size="sm" fw={500}>
                {item.percentage.toFixed(1)}%
              </Text>
              <Text size="xs" c="dimmed">
                ${item.value.toLocaleString()}
              </Text>
            </Group>
          </Group>
        ))}
      </Stack>
    </Stack>
  );
}

// Performance panel (real data only)
interface PerformancePoint {
  timestamp: string;
  value: number;
}

function PerformancePanel({
  loading,
  error,
  message,
  points,
}: {
  loading: boolean;
  error: string | null;
  message: string | null;
  points: PerformancePoint[];
}) {
  if (loading) {
    return (
      <Stack gap="sm">
        <Skeleton height={18} width={180} />
        <Skeleton height={160} />
      </Stack>
    );
  }

  if (error) {
    return (
      <Alert color="red" title="Performance unavailable">
        {error}
      </Alert>
    );
  }

  if (!points.length) {
    return (
      <Stack align="center" py="xl">
        <IconChartBar size={48} style={{ color: "var(--mantine-color-dimmed)" }} />
        <Text size="sm" c="dimmed" ta="center">
          {message || "No performance data available yet."}
        </Text>
      </Stack>
    );
  }

  const max = Math.max(...points.map((p) => p.value));
  const min = Math.min(...points.map((p) => p.value));
  const range = max - min || 1;

  const linePoints = points
    .map((p, i) => {
      const x = (i / (points.length - 1)) * 280 + 30;
      const y = 150 - ((p.value - min) / range) * 120 + 10;
      return `${x},${y}`;
    })
    .join(" ");

  const areaPoints = `30,160 ${linePoints} 310,160`;

  return (
    <Stack gap="sm">
      <Group justify="space-between">
        <Text size="sm" fw={500}>
          Portfolio Performance
        </Text>
        <Badge variant="light" color="blue">
          {points.length} points
        </Badge>
      </Group>

      <svg width="100%" height="180" viewBox="0 0 340 180" preserveAspectRatio="xMidYMid meet">
        {[0, 1, 2, 3, 4].map((i) => (
          <line
            key={i}
            x1="30"
            y1={10 + i * 30}
            x2="310"
            y2={10 + i * 30}
            stroke="var(--mantine-color-default-border)"
            strokeDasharray="4"
          />
        ))}

        <defs>
          <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={tokens.colors.primary[500]} stopOpacity="0.3" />
            <stop offset="100%" stopColor={tokens.colors.primary[500]} stopOpacity="0" />
          </linearGradient>
        </defs>
        <polygon points={areaPoints} fill="url(#areaGradient)" />

        <polyline
          points={linePoints}
          fill="none"
          stroke={tokens.colors.primary[500]}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {points.map((p, i) => {
          const x = (i / (points.length - 1)) * 280 + 30;
          const y = 150 - ((p.value - min) / range) * 120 + 10;
          return <circle key={i} cx={x} cy={y} r="4" fill={tokens.colors.primary[500]} />;
        })}
      </svg>
    </Stack>
  );
}

// Holdings table with sparklines
function HoldingsTable({ holdings, onEdit }: { holdings: Holding[]; onEdit?: (holding: Holding) => void }) {
  const columns = [
    {
      key: "ticker",
      label: "Ticker",
      sortable: true,
      render: (value: unknown) => (
        <Text fw={600} size="sm">
          {String(value)}
        </Text>
      ),
    },
    {
      key: "asset_type",
      label: "Type",
      sortable: true,
      render: (value: unknown) => (
        <Badge variant="light" size="sm">
          {value ? String(value) : "—"}
        </Badge>
      ),
    },
    {
      key: "shares",
      label: "Shares",
      sortable: true,
      align: "right" as const,
      render: (value: unknown) => <Text size="sm">{Number(value).toLocaleString()}</Text>,
    },
    {
      key: "price",
      label: "Price",
      sortable: true,
      align: "right" as const,
      render: (value: unknown) => {
        const price = typeof value === "number" ? value : null;
        return price === null ? (
          <Text size="sm" c="dimmed">—</Text>
        ) : (
          <Text size="sm">${price.toFixed(2)}</Text>
        );
      },
    },
    {
      key: "value",
      label: "Value",
      sortable: true,
      align: "right" as const,
      render: (value: unknown) => {
        const val = typeof value === "number" ? value : null;
        return val === null ? (
          <Text size="sm" c="dimmed">—</Text>
        ) : (
          <Text size="sm" fw={500}>
            ${val.toLocaleString()}
          </Text>
        );
      },
    },
    {
      key: "changePercent",
      label: "Change",
      sortable: true,
      align: "right" as const,
      render: (value: unknown, row: Record<string, unknown>) => {
        const raw =
          typeof value === "number"
            ? value
            : typeof row.change_pct === "number"
              ? row.change_pct
              : typeof row.changePercent === "number"
                ? row.changePercent
                : null;
        if (raw === null || Number.isNaN(raw)) {
          return <Text size="sm" c="dimmed">—</Text>;
        }
        const change = Number(raw);
        const isPositive = change >= 0;
        return (
          <Group gap={4} justify="flex-end">
            <Text size="sm" c={isPositive ? "success" : "error"}>
              {isPositive ? "+" : ""}
              {change.toFixed(2)}%
            </Text>
          </Group>
        );
      },
    },
  ];

  return <WidgetTable columns={columns} data={holdings} stickyHeader maxHeight={400} emptyMessage="No holdings in portfolio" />;
}

// Add/Edit holding modal
function AddHoldingModal({ opened, onClose, onSave }: { opened: boolean; onClose: () => void; onSave: (data: Partial<Holding>) => void }) {
  const [ticker, setTicker] = useState("");
  const [shares, setShares] = useState<number | string>("");
  const [assetType, setAssetType] = useState<string | null>("Stock");

  const handleSubmit = () => {
    if (!ticker || !shares) return;
    onSave({
      ticker: ticker.toUpperCase(),
      shares: Number(shares),
      asset_type: assetType || "Stock",
    });
    setTicker("");
    setShares("");
    setAssetType("Stock");
    onClose();
  };

  return (
    <Modal opened={opened} onClose={onClose} title="Add Holding" radius="lg">
      <Stack gap="md">
        <TextInput label="Ticker Symbol" placeholder="e.g., AAPL" value={ticker} onChange={(e) => setTicker(e.currentTarget.value)} required />
        <Select
          label="Asset Type"
          value={assetType}
          onChange={setAssetType}
          data={["Stock", "ETF", "Bond", "Crypto", "Real Estate", "Cash"]}
        />
        <NumberInput label="Shares" placeholder="Number of shares" value={shares} onChange={setShares} min={0} decimalScale={4} required />

        <Group justify="flex-end" mt="md">
          <Button variant="subtle" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={!ticker || !shares}>
            Add Holding
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

export default function FinancePage() {
  const [portfolio, setPortfolio] = useState<PortfolioData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modalOpened, { open: openModal, close: closeModal }] = useDisclosure(false);
  const [performancePoints, setPerformancePoints] = useState<PerformancePoint[]>([]);
  const [performanceLoading, setPerformanceLoading] = useState(true);
  const [performanceError, setPerformanceError] = useState<string | null>(null);
  const [performanceMessage, setPerformanceMessage] = useState<string | null>(null);

  const fetchPortfolio = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<PortfolioData>("/portfolio");
      setPortfolio(data);
    } catch {
      setError("Failed to load portfolio data");
      setPortfolio(null);
    } finally {
      setLoading(false);
    }
  };

  const fetchPerformance = async () => {
    setPerformanceLoading(true);
    setPerformanceError(null);
    setPerformanceMessage(null);
    try {
      const data = await apiFetch<any>("/api/finance/portfolio/performance?days=180");
      const rawPoints = Array.isArray(data?.points)
        ? data.points
        : Array.isArray(data?.series)
          ? data.series
          : Array.isArray(data?.data)
            ? data.data
            : [];
      const mapped: PerformancePoint[] = rawPoints
        .map((point: any) => ({
          timestamp: point.timestamp || point.date || point.time || "",
          value: typeof point.value === "number" ? point.value : Number(point.value),
        }))
        .filter((point: PerformancePoint) => point.timestamp && Number.isFinite(point.value));

      setPerformancePoints(mapped);
      if (!mapped.length && data?.message) {
        setPerformanceMessage(data.message);
      }
    } catch {
      setPerformanceError("Failed to load performance data");
      setPerformancePoints([]);
    } finally {
      setPerformanceLoading(false);
    }
  };

  useEffect(() => {
    fetchPortfolio();
    fetchPerformance();
  }, []);

  const handleAddHolding = async (data: Partial<Holding>) => {
    try {
      await apiFetch("/portfolio/holdings", {
        method: "POST",
        body: JSON.stringify({
          ticker: data.ticker,
          shares: data.shares,
          asset_type: data.asset_type || data.type,
        }),
      });
      fetchPortfolio();
    } catch {
      setError("Failed to add holding");
    }
  };

  const totalChange = useMemo(() => {
    if (!performancePoints.length) return null;
    const first = performancePoints[0]?.value;
    const last = performancePoints[performancePoints.length - 1]?.value;
    if (!first || !last) return null;
    return ((last - first) / first) * 100;
  }, [performancePoints]);

  const performanceSparkline = performancePoints.map((p) => p.value);
  const lastUpdatedLabel = portfolio?.last_updated
    ? new Date(portfolio.last_updated).toLocaleString()
    : "—";
  const normalizedHoldings = (portfolio?.holdings || []).map((holding) => ({
    ...holding,
    asset_type: holding.asset_type || holding.type,
  }));

  return (
    <Shell>
      <Page
        title="Finance"
        subtitle="Portfolio overview, holdings, and performance tracking"
        actions={
          <Group gap="sm">
            <Button leftSection={<IconPlus size={16} />} size="sm" onClick={openModal}>
              Add Holding
            </Button>
            <Button
              leftSection={<IconRefresh size={16} />}
              variant="light"
              size="sm"
              onClick={() => {
                fetchPortfolio();
                fetchPerformance();
              }}
              loading={loading}
            >
              Refresh
            </Button>
          </Group>
        }
      >
        <Stack gap="lg">
          {error && (
            <Alert
              icon={<IconAlertTriangle size={16} />}
              color="yellow"
              title="Portfolio unavailable"
              variant="light"
              withCloseButton={false}
            >
              <Group justify="space-between" align="center">
                <Text size="sm">{error}</Text>
                <Button
                  size="xs"
                  variant="light"
                  onClick={() => {
                    fetchPortfolio();
                    fetchPerformance();
                  }}
                >
                  Retry
                </Button>
              </Group>
            </Alert>
          )}

          {/* Stats Cards */}
          <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} spacing="md">
            <StatCard
              title="Total Value"
              value={`$${(portfolio?.total_value || 0).toLocaleString()}`}
              subtitle="All assets combined"
              trend={typeof totalChange === "number" ? { value: totalChange } : undefined}
              icon={<IconWallet size={22} />}
              color="primary"
              loading={loading}
              sparkline={performanceSparkline.length > 1 ? performanceSparkline : undefined}
            />
            <StatCard
              title="Cash Balance"
              value={`$${(portfolio?.cash || 0).toLocaleString()}`}
              subtitle="Available liquidity"
              icon={<IconCash size={22} />}
              color="success"
              loading={loading}
            />
            <StatCard
              title="Holdings"
              value={portfolio?.holdings?.length || 0}
              subtitle="Active positions"
              icon={<IconCoins size={22} />}
              color="info"
              loading={loading}
            />
            <StatCard
              title="Last Updated"
              value={lastUpdatedLabel}
              subtitle={portfolio?.source ? `Source: ${portfolio.source}` : "Source unavailable"}
              icon={<IconRefresh size={22} />}
              color="gray"
              loading={loading}
            />
          </SimpleGrid>

          {/* Charts Row */}
          <Grid gutter="lg">
            <Grid.Col span={{ base: 12, lg: 8 }}>
              <Card radius="lg" withBorder padding="lg">
                <PerformancePanel
                  loading={performanceLoading}
                  error={performanceError}
                  message={performanceMessage}
                  points={performancePoints}
                />
              </Card>
            </Grid.Col>
            <Grid.Col span={{ base: 12, lg: 4 }}>
              <Card radius="lg" withBorder padding="lg" h="100%">
                <Group justify="space-between" mb="md">
                  <Group gap="xs">
                    <ThemeIcon variant="light" color="primary" size="sm" radius="md">
                      <IconChartPie size={14} />
                    </ThemeIcon>
                    <Text fw={600} size="sm">
                      Allocation
                    </Text>
                  </Group>
                </Group>
                <AllocationChart holdings={normalizedHoldings} />
              </Card>
            </Grid.Col>
          </Grid>

          {/* Holdings Table */}
          <Card radius="lg" withBorder padding="lg">
            <Group justify="space-between" mb="md">
              <Group gap="xs">
                <ThemeIcon variant="light" color="primary" size="sm" radius="md">
                  <IconChartBar size={14} />
                </ThemeIcon>
                <Text fw={600} size="sm">
                  Holdings
                </Text>
              </Group>
              <Text size="xs" c="dimmed">
                {portfolio?.holdings?.length || 0} positions
              </Text>
            </Group>
            <HoldingsTable holdings={normalizedHoldings} />
          </Card>
        </Stack>
      </Page>

      <AddHoldingModal opened={modalOpened} onClose={closeModal} onSave={handleAddHolding} />
    </Shell>
  );
}
