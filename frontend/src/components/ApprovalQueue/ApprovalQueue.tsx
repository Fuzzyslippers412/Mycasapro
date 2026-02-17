"use client";

import { useState, useEffect } from "react";
import { getApiBaseUrl } from "@/lib/api";
import {
  Box,
  Stack,
  Paper,
  Title,
  Text,
  Group,
  Badge,
  Button,
  Progress,
  Divider,
  ActionIcon,
  Collapse,
  Alert,
} from "@mantine/core";
import {
  IconAlertCircle,
  IconCheck,
  IconX,
  IconChevronDown,
  IconChevronUp,
  IconCoin,
} from "@tabler/icons-react";

interface ApprovalRequest {
  id: string;
  requester_agent: string;
  approver_agent: string;
  approval_type: string;
  amount_usd: number | null;
  description: string;
  details: Record<string, any>;
  created_at: string;
  status: string;
}

interface BudgetInfo {
  spent: number;
  limit: number;
  percentage: number;
  remaining: number;
}

export function ApprovalQueue() {
  const API_URL = getApiBaseUrl();
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [budget, setBudget] = useState<BudgetInfo>({
    spent: 0,
    limit: 10000,
    percentage: 0,
    remaining: 10000,
  });
  const [loading, setLoading] = useState(false);

  const fetchApprovals = async () => {
    try {
      const res = await fetch(`${API_URL}/approvals/pending`);
      if (res.ok) {
        const data = await res.json();
        setApprovals(data.approvals || []);
      }
    } catch (error) {
      console.error("Failed to fetch approvals:", error);
    }
  };

  const fetchBudget = async () => {
    try {
      const res = await fetch(`${API_URL}/cost/budget`);
      if (res.ok) {
        const data = await res.json();
        const monthlyBudget = data.budgets?.find((b: any) => b.name === "Monthly Spend");
        if (monthlyBudget) {
          setBudget({
            spent: monthlyBudget.current || 0,
            limit: monthlyBudget.limit || 10000,
            percentage: monthlyBudget.pct || 0,
            remaining: (monthlyBudget.limit || 10000) - (monthlyBudget.current || 0),
          });
        }
      }
    } catch (error) {
      console.error("Failed to fetch budget:", error);
    }
  };

  useEffect(() => {
    fetchApprovals();
    fetchBudget();
    const interval = setInterval(() => {
      fetchApprovals();
      fetchBudget();
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleApprove = async (approvalId: string) => {
    setLoading(true);
    try {
      await fetch(`${API_URL}/approvals/${approvalId}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason: "Approved by user" }),
      });
      fetchApprovals();
      fetchBudget();
    } catch (error) {
      console.error("Failed to approve:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleDeny = async (approvalId: string) => {
    setLoading(true);
    try {
      await fetch(`${API_URL}/approvals/${approvalId}/deny`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason: "Denied by user" }),
      });
      fetchApprovals();
    } catch (error) {
      console.error("Failed to deny:", error);
    } finally {
      setLoading(false);
    }
  };

  const toggleExpanded = (id: string) => {
    const newExpanded = new Set(expandedIds);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }
    setExpandedIds(newExpanded);
  };

  const getAgentColor = (agent: string) => {
    const colors: Record<string, string> = {
      finance: "green",
      maintenance: "blue",
      contractors: "orange",
      projects: "violet",
      manager: "cyan",
    };
    return colors[agent] || "gray";
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case "cost":
        return <IconCoin size={18} />;
      default:
        return <IconAlertCircle size={18} />;
    }
  };

  const calculateImpact = (amount: number) => {
    const newSpent = budget.spent + amount;
    const newPercentage = (newSpent / budget.limit) * 100;
    const newRemaining = budget.limit - newSpent;

    return {
      newSpent,
      newPercentage,
      newRemaining,
      exceedsBudget: newSpent > budget.limit,
    };
  };

  return (
    <Stack gap="md">
      {/* Budget Overview */}
      <Paper p="md" withBorder>
        <Title order={4} mb="md">
          Monthly Budget Status
        </Title>
        <Group justify="space-between" mb="xs">
          <Text size="sm">
            ${budget.spent.toFixed(2)} / ${budget.limit.toFixed(2)}
          </Text>
          <Text size="sm" c="dimmed">
            {budget.percentage.toFixed(1)}%
          </Text>
        </Group>
        <Progress
          value={budget.percentage}
          color={budget.percentage > 85 ? "red" : budget.percentage > 70 ? "orange" : "green"}
          size="lg"
        />
        <Text size="xs" c="dimmed" mt="xs">
          ${budget.remaining.toFixed(2)} remaining
        </Text>
      </Paper>

      {/* Approval Queue */}
      <Paper p="md" withBorder>
        <Group justify="space-between" mb="md">
          <Group>
            <Title order={4}>Pending Approvals</Title>
            {approvals.length > 0 && (
              <Badge size="lg" color="red" variant="filled">
                {approvals.length}
              </Badge>
            )}
          </Group>
        </Group>

        {approvals.length === 0 ? (
          <Box ta="center" py="xl">
            <IconCheck size={48} style={{ opacity: 0.3 }} />
            <Text c="dimmed" size="sm" mt="sm">
              No pending approvals. All clear!
            </Text>
          </Box>
        ) : (
          <Stack gap="md">
            {approvals.map((approval) => {
              const isExpanded = expandedIds.has(approval.id);
              const impact = approval.amount_usd ? calculateImpact(approval.amount_usd) : null;

              return (
                <Paper key={approval.id} p="md" withBorder>
                  <Group justify="space-between" mb="sm">
                    <Group gap="xs">
                      <Badge color={getAgentColor(approval.requester_agent)} size="sm">
                        {approval.requester_agent}
                      </Badge>
                      <Badge variant="light" leftSection={getTypeIcon(approval.approval_type)}>
                        {approval.approval_type}
                      </Badge>
                      {approval.amount_usd && (
                        <Badge color="orange" size="lg" leftSection={<IconCoin size={14} />}>
                          ${approval.amount_usd.toFixed(2)}
                        </Badge>
                      )}
                    </Group>
                    <ActionIcon
                      variant="subtle"
                      size="sm"
                      onClick={() => toggleExpanded(approval.id)}
                    >
                      {isExpanded ? <IconChevronUp size={16} /> : <IconChevronDown size={16} />}
                    </ActionIcon>
                  </Group>

                  <Text size="sm" fw={600} mb="xs">
                    {approval.description}
                  </Text>

                  {/* Budget Impact Warning */}
                  {impact && impact.exceedsBudget && (
                    <Alert
                      icon={<IconAlertCircle size={16} />}
                      title="Budget Exceeded"
                      color="red"
                      variant="light"
                      mb="sm"
                    >
                      This approval would exceed your monthly budget by $
                      {Math.abs(impact.newRemaining).toFixed(2)}
                    </Alert>
                  )}

                  {/* Budget Impact Preview */}
                  {impact && !impact.exceedsBudget && (
                    <Box mb="sm">
                      <Text size="xs" c="dimmed" mb={4}>
                        Impact: ${impact.newSpent.toFixed(2)} ({impact.newPercentage.toFixed(1)}%)
                      </Text>
                      <Progress
                        value={impact.newPercentage}
                        color={
                          impact.newPercentage > 85
                            ? "red"
                            : impact.newPercentage > 70
                            ? "orange"
                            : "green"
                        }
                        size="sm"
                      />
                    </Box>
                  )}

                  {/* Expanded Details */}
                  <Collapse in={isExpanded}>
                    <Divider my="sm" />
                    <Stack gap="xs">
                      <Group>
                        <Text size="xs" c="dimmed">
                          Requested:
                        </Text>
                        <Text size="xs">
                          {new Date(approval.created_at).toLocaleString()}
                        </Text>
                      </Group>
                      {approval.details && Object.keys(approval.details).length > 0 && (
                        <>
                          <Text size="xs" c="dimmed" mt="xs">
                            Details:
                          </Text>
                          <Box
                            p="xs"
                            style={{
                              background: "var(--mantine-color-dark-6)",
                              borderRadius: 4,
                              fontFamily: "monospace",
                              fontSize: "11px",
                            }}
                          >
                            <pre style={{ margin: 0 }}>
                              {JSON.stringify(approval.details, null, 2)}
                            </pre>
                          </Box>
                        </>
                      )}
                    </Stack>
                    <Divider my="sm" />
                  </Collapse>

                  {/* Actions */}
                  <Group mt="md" justify="flex-end">
                    <Button
                      leftSection={<IconCheck size={16} />}
                      color="green"
                      onClick={() => handleApprove(approval.id)}
                      loading={loading}
                    >
                      Approve
                    </Button>
                    <Button
                      leftSection={<IconX size={16} />}
                      color="red"
                      variant="light"
                      onClick={() => handleDeny(approval.id)}
                      loading={loading}
                    >
                      Deny
                    </Button>
                  </Group>
                </Paper>
              );
            })}
          </Stack>
        )}
      </Paper>
    </Stack>
  );
}
