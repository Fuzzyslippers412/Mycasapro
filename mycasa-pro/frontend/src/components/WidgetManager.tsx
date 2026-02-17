"use client";
import {
  Card,
  Group,
  Text,
  Switch,
  Stack,
  Badge,
  Button,
  SimpleGrid,
  ThemeIcon,
  Paper,
} from "@mantine/core";
import {
  IconActivity,
  IconCpu,
  IconTool,
  IconAlertTriangle,
  IconChartLine,
  IconWallet,
  IconClock,
  IconBolt,
  IconTrash,
  IconReceipt,
  IconMessage,
  IconRefresh,
} from "@tabler/icons-react";
import { useState, useEffect } from "react";
import {
  AVAILABLE_WIDGETS,
  Widget,
  getDashboardConfig,
  toggleWidget,
  resetDashboardConfig,
  DashboardConfig,
} from "@/lib/widgets";

// Icon mapping
const ICONS: Record<string, React.ElementType> = {
  IconActivity,
  IconCpu,
  IconTool,
  IconAlertTriangle,
  IconChartLine,
  IconWallet,
  IconClock,
  IconBolt,
  IconTrash,
  IconReceipt,
  IconMessage,
};

const CATEGORY_COLORS: Record<string, string> = {
  status: "blue",
  finance: "green",
  tasks: "orange",
  agents: "violet",
  tools: "gray",
};

interface WidgetCardProps {
  widget: Widget;
  enabled: boolean;
  onToggle: () => void;
}

function WidgetCard({ widget, enabled, onToggle }: WidgetCardProps) {
  const Icon = ICONS[widget.icon] || IconActivity;
  
  return (
    <Paper withBorder p="md" radius="md">
      <Group justify="space-between" wrap="nowrap">
        <Group gap="sm" wrap="nowrap">
          <ThemeIcon
            size="lg"
            radius="md"
            variant={enabled ? "filled" : "light"}
            color={CATEGORY_COLORS[widget.category]}
          >
            <Icon size={18} />
          </ThemeIcon>
          <div>
            <Text size="sm" fw={500}>
              {widget.name}
            </Text>
            <Text size="xs" c="dimmed">
              {widget.description}
            </Text>
          </div>
        </Group>
        <Switch
          checked={enabled}
          onChange={onToggle}
          size="md"
        />
      </Group>
    </Paper>
  );
}

export function WidgetManager() {
  const [config, setConfig] = useState<DashboardConfig | null>(null);
  
  useEffect(() => {
    setConfig(getDashboardConfig());
  }, []);
  
  const handleToggle = (widgetId: string) => {
    const newConfig = toggleWidget(widgetId);
    setConfig(newConfig);
  };
  
  const handleReset = () => {
    const newConfig = resetDashboardConfig();
    setConfig(newConfig);
  };
  
  if (!config) {
    return null;
  }
  
  // Group widgets by category
  const widgetsByCategory: Record<string, Widget[]> = {};
  AVAILABLE_WIDGETS.forEach(widget => {
    if (!widgetsByCategory[widget.category]) {
      widgetsByCategory[widget.category] = [];
    }
    widgetsByCategory[widget.category].push(widget);
  });
  
  return (
    <Stack gap="lg">
      <Group justify="space-between">
        <div>
          <Text size="lg" fw={600}>Dashboard Widgets</Text>
          <Text size="sm" c="dimmed">
            Choose which widgets appear on your dashboard
          </Text>
        </div>
        <Button
          variant="subtle"
          leftSection={<IconRefresh size={16} />}
          onClick={handleReset}
        >
          Reset to Default
        </Button>
      </Group>
      
      <Group gap="xs">
        <Badge color="blue" variant="light">Status</Badge>
        <Badge color="green" variant="light">Finance</Badge>
        <Badge color="orange" variant="light">Tasks</Badge>
        <Badge color="violet" variant="light">Agents</Badge>
        <Badge color="gray" variant="light">Tools</Badge>
      </Group>
      
      {Object.entries(widgetsByCategory).map(([category, widgets]) => (
        <Card key={category} withBorder padding="md" radius="md">
          <Text size="sm" fw={600} mb="md" tt="capitalize">
            {category} Widgets
          </Text>
          <SimpleGrid cols={{ base: 1, sm: 2 }}>
            {widgets.map(widget => (
              <WidgetCard
                key={widget.id}
                widget={widget}
                enabled={config.enabledWidgets.includes(widget.id)}
                onToggle={() => handleToggle(widget.id)}
              />
            ))}
          </SimpleGrid>
        </Card>
      ))}
      
      <Text size="xs" c="dimmed">
        Changes are saved automatically. Refresh the dashboard to see updates.
      </Text>
    </Stack>
  );
}
