import { Alert, Button, Group, Text } from "@mantine/core";
import { IconAlertTriangle } from "@tabler/icons-react";

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <Alert icon={<IconAlertTriangle size={16} />} color="red" title="Error">
      <Group justify="space-between">
        <Text size="sm">{message}</Text>
        {onRetry && (
          <Button size="xs" variant="light" onClick={onRetry}>Retry</Button>
        )}
      </Group>
    </Alert>
  );
}
