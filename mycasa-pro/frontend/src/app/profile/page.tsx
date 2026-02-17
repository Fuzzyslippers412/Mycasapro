"use client";

import Link from "next/link";
import { Shell } from "@/components/layout/Shell";
import { Page } from "@/components/layout/Page";
import { Button, Card, Stack, Text } from "@mantine/core";

export default function ProfilePage() {
  return (
    <Shell>
      <Page title="Profile" subtitle="Manage your account details and preferences.">
        <Card withBorder radius="md" padding="lg">
          <Stack gap="sm">
            <Text size="sm" c="dimmed">
              Update your profile photo, name, and security preferences from Settings.
            </Text>
            <Button component={Link} href="/settings?tab=profile" variant="light" size="sm">
              Open Profile Settings
            </Button>
          </Stack>
        </Card>
      </Page>
    </Shell>
  );
}
