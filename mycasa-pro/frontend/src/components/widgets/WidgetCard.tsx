'use client';

import {
  Card,
  Group,
  Stack,
  Text,
  Box,
  Skeleton,
  Badge,
  ThemeIcon,
  Tooltip,
  ActionIcon,
  Collapse,
  rem,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import {
  IconChevronDown,
  IconChevronUp,
  IconArrowUpRight,
  IconArrowDownRight,
  IconMinus,
  IconRefresh,
} from '@tabler/icons-react';
import { tokens } from '@/theme/tokens';

// Accent color types for left border
type AccentColor = 'primary' | 'success' | 'warning' | 'error' | 'info' | 'neutral';

interface WidgetCardProps {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  footer?: React.ReactNode;
  loading?: boolean;
  children: React.ReactNode;
  accent?: AccentColor;
  collapsible?: boolean;
  defaultCollapsed?: boolean;
  icon?: React.ReactNode;
  badge?: string | number;
  badgeColor?: string;
  onRefresh?: () => void;
  noPadding?: boolean;
  gradient?: boolean;
}

const accentColors: Record<AccentColor, string> = {
  primary: tokens.colors.primary[600],
  success: tokens.colors.success[500],
  warning: tokens.colors.warn[500],
  error: tokens.colors.error[500],
  info: tokens.colors.info[500],
  neutral: tokens.colors.neutral[400],
};

export function WidgetCard({
  title,
  description,
  actions,
  footer,
  loading,
  children,
  accent,
  collapsible = false,
  defaultCollapsed = false,
  icon,
  badge,
  badgeColor = 'primary',
  onRefresh,
  noPadding = false,
  gradient = false,
}: WidgetCardProps) {
  const [collapsed, { toggle }] = useDisclosure(defaultCollapsed);

  const cardStyles: React.CSSProperties = {
    borderLeft: accent ? `4px solid ${accentColors[accent]}` : undefined,
    background: gradient ? 'var(--widget-card-gradient)' : undefined,
  };

  return (
    <Card
      radius="lg"
      withBorder
      padding={noPadding ? 0 : 'lg'}
      style={cardStyles}
      data-no-hover={noPadding ? true : undefined}
    >
      {/* Header */}
      <Group
        justify="space-between"
        mb={collapsed ? 0 : 12}
        style={{ cursor: collapsible ? 'pointer' : undefined }}
        onClick={collapsible ? toggle : undefined}
        px={noPadding ? 'lg' : 0}
        pt={noPadding ? 'lg' : 0}
      >
        <Group gap="sm">
          {icon && (
            <ThemeIcon
              variant="light"
              color={accent || 'primary'}
              size="md"
              radius="md"
            >
              {icon}
            </ThemeIcon>
          )}
          <Stack gap={2}>
            <Group gap="xs">
              <Text size="sm" fw={600}>
                {title}
              </Text>
              {badge && (
                <Badge size="xs" variant="light" color={badgeColor}>
                  {badge}
                </Badge>
              )}
            </Group>
            {description && (
              <Text size="xs" c="dimmed">
                {description}
              </Text>
            )}
          </Stack>
        </Group>

        <Group gap="xs">
          {onRefresh && (
            <Tooltip label="Refresh">
              <ActionIcon
                variant="subtle"
                color="gray"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  onRefresh();
                }}
              >
                <IconRefresh size={14} />
              </ActionIcon>
            </Tooltip>
          )}
          {actions}
          {collapsible && (
            <ActionIcon variant="subtle" color="gray" size="sm">
              {collapsed ? <IconChevronDown size={14} /> : <IconChevronUp size={14} />}
            </ActionIcon>
          )}
        </Group>
      </Group>

      {/* Content */}
      <Collapse in={!collapsed}>
        <Box px={noPadding ? 'lg' : 0}>
          {loading ? (
            <Stack gap="sm">
              <Skeleton height={20} radius="md" />
              <Skeleton height={20} width="80%" radius="md" />
              <Skeleton height={20} width="60%" radius="md" />
            </Stack>
          ) : (
            children
          )}
        </Box>
      </Collapse>

      {/* Footer */}
      {footer && !collapsed && (
        <Box
          mt={12}
          pt={12}
          px={noPadding ? 'lg' : 0}
          pb={noPadding ? 'lg' : 0}
          style={{
            borderTop: '1px solid var(--mantine-color-default-border)',
          }}
        >
          {footer}
        </Box>
      )}
    </Card>
  );
}

// Stat card variant with trend indicator
interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: {
    value: number;
    label?: string;
  };
  icon?: React.ReactNode;
  color?: AccentColor;
  loading?: boolean;
  onClick?: () => void;
  sparkline?: number[];
}

export function StatCard({
  title,
  value,
  subtitle,
  trend,
  icon,
  color = 'primary',
  loading = false,
  onClick,
  sparkline,
}: StatCardProps) {
  const getTrendIcon = () => {
    if (!trend) return null;
    if (trend.value > 0) return <IconArrowUpRight size={16} />;
    if (trend.value < 0) return <IconArrowDownRight size={16} />;
    return <IconMinus size={16} />;
  };

  const getTrendColor = () => {
    if (!trend) return 'dimmed';
    if (trend.value > 0) return 'success';
    if (trend.value < 0) return 'error';
    return 'dimmed';
  };

  if (loading) {
    return (
      <Card radius="lg" withBorder padding="lg">
        <Stack gap="sm">
          <Skeleton height={14} width="60%" radius="md" />
          <Skeleton height={32} width="80%" radius="md" />
          <Skeleton height={12} width="40%" radius="md" />
        </Stack>
      </Card>
    );
  }

  return (
    <Card
      radius="lg"
      withBorder
      padding="lg"
      style={{
        cursor: onClick ? 'pointer' : undefined,
        borderLeft: `4px solid ${accentColors[color]}`,
        backgroundImage: tokens.gradients.card,
      }}
      onClick={onClick}
      className={`stat-card ${onClick ? 'card-clickable' : ''}`}
    >
      <Group justify="space-between" align="flex-start">
        <Stack gap={4}>
          <Text size="xs" c="dimmed" tt="uppercase" fw={600} style={{ letterSpacing: '0.05em' }}>
            {title}
          </Text>
          <Text
            size="xl"
            fw={700}
            style={{
              fontSize: rem(28),
              lineHeight: 1.2,
              letterSpacing: '-0.02em',
            }}
          >
            {value}
          </Text>
          {(subtitle || trend) && (
            <Group gap="xs">
              {trend && (
                <Badge
                  variant="light"
                  color={getTrendColor()}
                  size="sm"
                  leftSection={getTrendIcon()}
                >
                  {Math.abs(trend.value)}%
                </Badge>
              )}
              {subtitle && (
                <Text size="xs" c="dimmed">
                  {subtitle}
                </Text>
              )}
            </Group>
          )}
        </Stack>

        {icon && (
          <ThemeIcon
            variant="light"
            color={color}
            size="xl"
            radius="md"
          >
            {icon}
          </ThemeIcon>
        )}
      </Group>

      {/* Mini sparkline */}
      {sparkline && sparkline.length > 0 && (
        <Box mt="sm">
          <Sparkline data={sparkline} color={accentColors[color]} />
        </Box>
      )}
    </Card>
  );
}

// Simple sparkline component
function Sparkline({ data, color, height = 32 }: { data: number[]; color: string; height?: number }) {
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;

  const points = data.map((value, i) => {
    const x = (i / (data.length - 1)) * 100;
    const y = 100 - ((value - min) / range) * 100;
    return `${x},${y}`;
  }).join(' ');

  return (
    <svg
      width="100%"
      height={height}
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
      style={{ overflow: 'visible' }}
    >
      <defs>
        <linearGradient id={`sparkline-gradient-${color.replace('#', '')}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.3" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      {/* Fill area */}
      <polygon
        points={`0,100 ${points} 100,100`}
        fill={`url(#sparkline-gradient-${color.replace('#', '')})`}
      />
      {/* Line */}
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

// Export sparkline for use elsewhere
export { Sparkline };
