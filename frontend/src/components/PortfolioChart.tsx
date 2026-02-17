"use client";

import { useState, useEffect } from "react";
import { getApiBaseUrl } from "@/lib/api";
import {
  Card,
  Text,
  Group,
  Badge,
  Stack,
  SimpleGrid,
  Progress,
  Skeleton,
  Box,
  ThemeIcon,
} from "@mantine/core";
import { IconTrendingUp, IconTrendingDown, IconMinus } from "@tabler/icons-react";

interface Holding {
  ticker: string;
  shares: number;
  type: string;
  price?: number;
  value?: number;
  change_pct?: number;
}

interface PortfolioData {
  holdings: Holding[];
  total_value: number;
  day_change: number;
  day_change_pct: number;
  by_type: Record<string, number>;
}

const API_URL = getApiBaseUrl();

function HoldingRow({ holding }: { holding: Holding }) {
  const changePct = holding.change_pct || 0;
  const isPositive = changePct > 0;
  const isNegative = changePct < 0;

  return (
    <Group
      justify="space-between"
      py="xs"
      style={{
        borderBottom: "1px solid var(--mantine-color-default-border)"
      }}
    >
      <Group gap="sm">
        <Text fw={600} size="sm" w={60}>{holding.ticker}</Text>
        <Text size="xs" c="dimmed">{holding.shares.toLocaleString()} shares</Text>
      </Group>
      <Group gap="sm">
        <Text size="sm" fw={500}>
          ${(holding.value || 0).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
        </Text>
        {changePct !== 0 && (
          <Badge 
            size="sm" 
            variant="light" 
            color={isPositive ? "green" : isNegative ? "red" : "gray"}
            leftSection={
              isPositive ? <IconTrendingUp size={12} /> : 
              isNegative ? <IconTrendingDown size={12} /> : 
              <IconMinus size={12} />
            }
          >
            {isPositive ? "+" : ""}{changePct.toFixed(2)}%
          </Badge>
        )}
      </Group>
    </Group>
  );
}

function AllocationBar({ allocations }: { allocations: Record<string, number> }) {
  const colors: Record<string, string> = {
    "Tech": "blue",
    "Tech/AI": "violet",
    "Gold": "yellow",
    "BTC ETF": "orange",
    "Dividend ETF": "green",
    "Payments": "cyan",
    "China Tech": "red",
    "Cash": "gray",
  };
  
  const total = Object.values(allocations).reduce((a, b) => a + b, 0);
  const sections = Object.entries(allocations)
    .filter(([_, value]) => value > 0)
    .map(([type, value]) => ({
      value: (value / total) * 100,
      color: colors[type] || "gray",
      tooltip: `${type}: ${((value / total) * 100).toFixed(1)}%`,
    }));
  
  return (
    <Box>
      <Progress.Root size="xl" radius="md">
        {sections.map((section, idx) => (
          <Progress.Section key={idx} value={section.value} color={section.color} />
        ))}
      </Progress.Root>
      <Group mt="xs" gap="xs" wrap="wrap">
        {Object.entries(allocations)
          .filter(([_, value]) => value > 0)
          .slice(0, 6)
          .map(([type, value]) => (
            <Badge key={type} size="xs" variant="light" color={colors[type] || "gray"}>
              {type}: {((value / total) * 100).toFixed(0)}%
            </Badge>
          ))}
      </Group>
    </Box>
  );
}

export function PortfolioChart() {
  const [data, setData] = useState<PortfolioData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  useEffect(() => {
    const fetchPortfolio = async () => {
      try {
        const res = await fetch(`${API_URL}/portfolio`);
        if (!res.ok) throw new Error("Failed to fetch portfolio");
        const portfolio = await res.json();
        setData(portfolio);
      } catch (e) {
        setError((e as Error).message);
      } finally {
        setLoading(false);
      }
    };
    
    fetchPortfolio();
    const interval = setInterval(fetchPortfolio, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, []);
  
  if (loading) {
    return (
      <Card withBorder padding="lg" radius="md">
        <Skeleton height={20} width={150} mb="md" />
        <Skeleton height={40} mb="md" />
        <Stack gap="xs">
          {[1, 2, 3].map((i) => <Skeleton key={i} height={36} />)}
        </Stack>
      </Card>
    );
  }
  
  if (error || !data) {
    return (
      <Card withBorder padding="lg" radius="md">
        <Text fw={600} mb="md">Portfolio</Text>
        <Text size="sm" c="dimmed">{error || "No data available"}</Text>
      </Card>
    );
  }
  
  const dayChange = data.day_change || 0;
  const dayChangePct = data.day_change_pct || 0;
  const isPositive = dayChange > 0;
  
  return (
    <Card withBorder padding="lg" radius="md">
      <Group justify="space-between" mb="md">
        <Text fw={600}>Portfolio</Text>
        <Badge 
          variant="light" 
          color={isPositive ? "green" : dayChange < 0 ? "red" : "gray"}
          leftSection={
            isPositive ? <IconTrendingUp size={12} /> : 
            dayChange < 0 ? <IconTrendingDown size={12} /> : 
            <IconMinus size={12} />
          }
        >
          {isPositive ? "+" : ""}{dayChangePct.toFixed(2)}% today
        </Badge>
      </Group>
      
      {/* Total Value */}
      <Box mb="md">
        <Text size="xl" fw={700}>
          ${data.total_value.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
        </Text>
        <Text size="sm" c={isPositive ? "green" : dayChange < 0 ? "red" : "dimmed"}>
          {isPositive ? "+" : ""}${Math.abs(dayChange).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })} today
        </Text>
      </Box>
      
      {/* Allocation */}
      {data.by_type && Object.keys(data.by_type).length > 0 && (
        <Box mb="md">
          <Text size="xs" c="dimmed" mb="xs">ALLOCATION</Text>
          <AllocationBar allocations={data.by_type} />
        </Box>
      )}
      
      {/* Top Holdings */}
      <Box>
        <Text size="xs" c="dimmed" mb="xs">TOP HOLDINGS</Text>
        <Stack gap={0}>
          {data.holdings
            .sort((a, b) => (b.value || 0) - (a.value || 0))
            .slice(0, 5)
            .map((holding) => (
              <HoldingRow key={holding.ticker} holding={holding} />
            ))}
        </Stack>
      </Box>
    </Card>
  );
}
