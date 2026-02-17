"use client";
import { Shell } from "@/components/layout/Shell";
import { useEffect, useState } from "react";
import { Page } from "@/components/layout/Page";
import { apiFetch } from "@/lib/api";

import { Stack, Text, Card, Badge, Container, Title } from "@mantine/core";

// Mock Approval Queue Component
function ApprovalQueue() {
  return (
    <Card withBorder p="lg" radius="md">
      <Text c="dimmed" ta="center" py="xl">
        No pending approvals at this time
      </Text>
    </Card>
  );
}

export default function ApprovalsPage() {
  return (
    <Shell>
      <Page title="Approvals" subtitle="Pending approvals">
      <Container size="lg">
        <Title order={2} mb="xs">
          Approval Center
        </Title>
        <Text c="dimmed" mb="lg">
          Review and approve agent requests for costs and actions
        </Text>
        <ApprovalQueue />
      </Container>
          </Page>
    </Shell>
  );
}
