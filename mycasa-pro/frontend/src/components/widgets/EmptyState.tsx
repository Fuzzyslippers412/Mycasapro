import { Group, Text, Button } from "@mantine/core";
import { IconInbox } from "@tabler/icons-react";

export function EmptyState({ message, ctaLabel, onClick }: { message: string; ctaLabel?: string; onClick?: () => void; }) {
  return (
    <Group gap="sm">
      <IconInbox size={18} />
      <Text size="sm" c="dimmed">{message}</Text>
      {ctaLabel && onClick && (
        <Button size="xs" variant="light" onClick={onClick}>{ctaLabel}</Button>
      )}
    </Group>
  );
}
