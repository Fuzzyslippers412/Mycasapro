"use client";
import { Shell } from "@/components/layout/Shell";
import { apiFetch } from "@/lib/api";
import { WidgetCard } from "@/components/widgets/WidgetCard";
import { Page } from "@/components/layout/Page";
import { Card, Text, Stack, Box, Badge, Group, SimpleGrid, ThemeIcon } from "@mantine/core";
import { IconShield, IconLock, IconAlertTriangle, IconEye } from "@tabler/icons-react";

export default function SecurityPage() {
  return (
    <Shell>
      <Page title="Security" subtitle="Security posture & incidents">
      <Stack gap="md" className="security-page">
        <Group justify="space-between">
          <div>
            <Text fw={600}>Security status</Text>
            <Text size="xs" c="dimmed">Monitoring, alerts, and incident tracking</Text>
          </div>
          <Badge color="green" size="lg">Secure</Badge>
        </Group>
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} className="security-stats">
          <Card withBorder p="lg" radius="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed" tt="uppercase" fw={600}>Threats</Text>
                <Text size="xl" fw={700}>0</Text>
              </div>
              <ThemeIcon size="xl" variant="light" color="green">
                <IconShield size={24} />
              </ThemeIcon>
            </Group>
          </Card>
          <Card withBorder p="lg" radius="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed" tt="uppercase" fw={600}>Alerts</Text>
                <Text size="xl" fw={700}>0</Text>
              </div>
              <ThemeIcon size="xl" variant="light" color="gray">
                <IconAlertTriangle size={24} />
              </ThemeIcon>
            </Group>
          </Card>
          <Card withBorder p="lg" radius="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed" tt="uppercase" fw={600}>Scans Today</Text>
                <Text size="xl" fw={700}>0</Text>
              </div>
              <ThemeIcon size="xl" variant="light" color="blue">
                <IconEye size={24} />
              </ThemeIcon>
            </Group>
          </Card>
          <Card withBorder p="lg" radius="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed" tt="uppercase" fw={600}>Protected</Text>
                <Text size="xl" fw={700}>✓</Text>
              </div>
              <ThemeIcon size="xl" variant="light" color="green">
                <IconLock size={24} />
              </ThemeIcon>
            </Group>
          </Card>
        </SimpleGrid>
        <Card withBorder p="xl" radius="md">
          <Text fw={600} mb="md">Security Events</Text>
          <Box py="xl" style={{ textAlign: "center" }}>
            <Text c="dimmed">No security events to display</Text>
          </Box>
        </Card>
      </Stack>
          </Page>
    </Shell>
  );
}
