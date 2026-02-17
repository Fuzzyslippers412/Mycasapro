"use client";

import { Group, Progress, Stack, Text, Badge } from "@mantine/core";

const COLORS: Record<string, string> = {
  system: "indigo",
  developer: "cyan",
  memory: "teal",
  history: "blue",
  retrieval: "violet",
  tool_results: "orange",
  other: "grape",
  reserved_output: "gray",
};

interface ContextStackedBarProps {
  contextWindow: number;
  reservedOutput: number;
  tokens: {
    system?: number;
    developer?: number;
    memory?: number;
    history?: number;
    retrieval?: number;
    tool_results?: number;
    other?: number;
  };
}

function pct(value: number, total: number) {
  if (total <= 0) return 0;
  return Math.max(0, Math.min(100, (value / total) * 100));
}

export function ContextStackedBar({ contextWindow, reservedOutput, tokens }: ContextStackedBarProps) {
  const sections = [
    { key: "system", value: tokens.system || 0 },
    { key: "developer", value: tokens.developer || 0 },
    { key: "memory", value: tokens.memory || 0 },
    { key: "history", value: tokens.history || 0 },
    { key: "retrieval", value: tokens.retrieval || 0 },
    { key: "tool_results", value: tokens.tool_results || 0 },
    { key: "other", value: tokens.other || 0 },
    { key: "reserved_output", value: reservedOutput || 0 },
  ];

  const progressSections = sections
    .filter((section) => section.value > 0)
    .map((section) => ({
      value: pct(section.value, contextWindow),
      color: COLORS[section.key] || "gray",
    }));

  return (
    <Stack gap="xs">
      <Progress data-testid="context-progress" sections={progressSections} radius="lg" size="lg" />
      <Group gap="xs">
        {sections.map((section) => (
          <Badge
            key={section.key}
            size="xs"
            variant="light"
            color={COLORS[section.key] || "gray"}
          >
            {section.key.replace("_", " ")} · {section.value}
          </Badge>
        ))}
      </Group>
      <Text size="xs" c="dimmed">
        Context window: {contextWindow} tokens
      </Text>
    </Stack>
  );
}
