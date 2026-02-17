"use client";
import { Shell } from "@/components/layout/Shell";
import { Page } from "@/components/layout/Page";
import { tokens } from "@/theme/tokens";

import {
  Card, Text, Title, Stack, Tabs, Badge, Group, Box, Avatar, Paper,
  ActionIcon, Tooltip, Button, TextInput, Divider, Textarea,
  Menu, Checkbox, Loader, Alert, ScrollArea, ThemeIcon, CloseButton,
  Transition, Collapse, rem, SimpleGrid, Skeleton,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import {
  IconMail, IconCheck, IconBell, IconBrandWhatsapp, IconRefresh,
  IconSearch, IconArchive, IconArrowBackUp, IconFilter,
  IconInbox, IconStar, IconTrash, IconTag, IconPlugConnectedX,
  IconExternalLink, IconChevronDown, IconChevronUp,
  IconCircle, IconSend, IconX, IconMailOpened,
} from "@tabler/icons-react";
import { useState, useEffect } from "react";
import { apiFetch, getApiBaseUrl, isNetworkError } from "@/lib/api";
import { notifications } from "@mantine/notifications";
import { useInboxMessages, useUnreadCount } from "@/lib/hooks";

interface Message {
  id: number;
  source: "whatsapp" | "gmail";
  sender: string;
  sender_id?: string;
  subject?: string;
  body: string;
  timestamp: string;
  is_read: boolean;
  domain?: string;
}

const API_URL = getApiBaseUrl();

// Filter pill component
function FilterPill({
  label,
  active,
  count,
  color,
  icon,
  onClick,
}: {
  label: string;
  active: boolean;
  count?: number;
  color?: string;
  icon?: React.ReactNode;
  onClick: () => void;
}) {
  return (
    <Button
      variant={active ? "filled" : "light"}
      color={active ? (color || "primary") : "gray"}
      size="xs"
      radius="xl"
      leftSection={icon}
      onClick={onClick}
      styles={{
        root: {
          fontWeight: active ? 600 : 500,
          transition: "all 150ms ease",
        },
      }}
    >
      {label}
      {count !== undefined && count > 0 && (
        <Badge
          size="xs"
          variant={active ? "white" : "filled"}
          color={active ? undefined : color || "primary"}
          ml={6}
          style={{ minWidth: 18 }}
        >
          {count}
        </Badge>
      )}
    </Button>
  );
}

// Quick reply component
function QuickReply({
  onSend,
  onCancel,
  recipientName,
  sending = false,
  error,
}: {
  onSend: (message: string) => void;
  onCancel: () => void;
  recipientName: string;
  sending?: boolean;
  error?: string | null;
}) {
  const [message, setMessage] = useState("");

  return (
    <Paper
      p="md"
      radius="md"
      withBorder
      style={{
        backgroundColor: "var(--quick-reply-bg)",
      }}
    >
      <Stack gap="sm">
        <Group justify="space-between">
          <Text size="sm" fw={500}>
            Reply to {recipientName}
          </Text>
          <ActionIcon variant="subtle" color="gray" size="sm" onClick={onCancel}>
            <IconX size={14} />
          </ActionIcon>
        </Group>
        <Textarea
          placeholder="Type your reply..."
          value={message}
          onChange={(e) => setMessage(e.currentTarget.value)}
          minRows={2}
          maxRows={4}
          autoFocus
        />
        {error && (
          <Text size="xs" c="red">
            {error}
          </Text>
        )}
        <Group justify="flex-end" gap="xs">
          <Button variant="subtle" size="xs" onClick={onCancel}>
            Cancel
          </Button>
          <Button
            size="xs"
            leftSection={<IconSend size={14} />}
            loading={sending}
            disabled={!message.trim() || sending}
            onClick={() => {
              onSend(message);
              setMessage("");
            }}
          >
            Send
          </Button>
        </Group>
      </Stack>
    </Paper>
  );
}

// Message Detail Panel
function MessageDetail({
  message,
  onClose,
  onMarkRead,
}: {
  message: Message | null;
  onClose: () => void;
  onMarkRead: (id: number) => void;
}) {
  const [showReply, setShowReply] = useState(false);
  const [replySending, setReplySending] = useState(false);
  const [replyError, setReplyError] = useState<string | null>(null);

  if (!message) return null;

  const date = new Date(message.timestamp);
  const formattedDate = date.toLocaleDateString([], {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });
  const formattedTime = date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  const handleReply = () => {
    if (message.source === "gmail") {
      window.open(`https://mail.google.com/mail/u/0/?compose=new&to=${message.sender_id}`, "_blank");
    } else {
      const phone = message.sender_id?.split("@")[0];
      if (phone) {
        window.open(`https://wa.me/${phone}`, "_blank");
      }
    }
  };

  const handleQuickReply = async (text: string) => {
    setReplySending(true);
    setReplyError(null);
    try {
      if (message.source === "whatsapp") {
        const to = message.sender_id || message.sender;
        await apiFetch("/api/messaging/send", {
          method: "POST",
          body: JSON.stringify({
            to,
            message: text,
            channel: "whatsapp",
            record_in_secondbrain: true,
          }),
        }, 15000);
        notifications.show({
          title: "Message sent",
          message: `WhatsApp sent to ${message.sender}`,
          color: "green",
        });
      } else {
        const subject = encodeURIComponent(message.subject || "Re:");
        const body = encodeURIComponent(text);
        const mailto = `mailto:${message.sender_id || ""}?subject=${subject}&body=${body}`;
        window.open(mailto, "_blank");
        notifications.show({
          title: "Draft opened",
          message: "Your email draft opened in the mail app.",
          color: "blue",
        });
      }
      setShowReply(false);
    } catch (e) {
      const detail = isNetworkError(e)
        ? `Unable to reach backend at ${API_URL}. Start the server and try again.`
        : (e as any)?.detail || (e as Error)?.message || "Failed to send reply";
      setReplyError(detail);
    } finally {
      setReplySending(false);
    }
  };

  return (
    <Card withBorder radius="lg" p={0} h="100%" style={{ display: "flex", flexDirection: "column" }}>
      {/* Header */}
      <Box
        p="md"
        style={{
          borderBottom: "1px solid var(--mantine-color-default-border)",
        }}
      >
        <Group justify="space-between" mb="sm">
          <Group gap="sm">
            <Avatar
              size="lg"
              radius="xl"
              color={message.source === "whatsapp" ? "green" : "red"}
            >
              {message.sender.charAt(0).toUpperCase()}
            </Avatar>
            <div>
              <Group gap="xs">
                <Text fw={600} size="md">{message.sender}</Text>
                <ThemeIcon
                  size="sm"
                  radius="xl"
                  color={message.source === "whatsapp" ? "green" : "red"}
                  variant="light"
                >
                  {message.source === "whatsapp" ? <IconBrandWhatsapp size={12} /> : <IconMail size={12} />}
                </ThemeIcon>
              </Group>
              <Text size="xs" c="dimmed">{message.sender_id || message.source}</Text>
            </div>
          </Group>
          <CloseButton onClick={onClose} />
        </Group>

        <Text fw={600} size="lg" mb="xs">
          {message.subject || `Message from ${message.sender}`}
        </Text>

        <Group gap="xs">
          <Text size="xs" c="dimmed">{formattedDate} at {formattedTime}</Text>
          {message.domain && message.domain !== "unknown" && (
            <Badge size="xs" variant="light">{message.domain}</Badge>
          )}
          {!message.is_read && (
            <Badge size="xs" color="blue" variant="filled">Unread</Badge>
          )}
        </Group>
      </Box>

      {/* Body */}
      <ScrollArea style={{ flex: 1 }} p="md">
        <Text style={{ whiteSpace: "pre-wrap", lineHeight: 1.7 }}>
          {message.body || "(No message content available - click Sync to fetch full message)"}
        </Text>
      </ScrollArea>

      {/* Quick Reply */}
      <Collapse in={showReply}>
        <Box p="md" pt={0}>
          <QuickReply
            recipientName={message.sender}
            onSend={handleQuickReply}
            onCancel={() => setShowReply(false)}
            sending={replySending}
            error={replyError}
          />
        </Box>
      </Collapse>

      {/* Actions */}
      <Box
        p="md"
        style={{
          borderTop: "1px solid var(--mantine-color-default-border)",
        }}
      >
        <Group gap="xs">
          <Button
            variant="light"
            leftSection={<IconArrowBackUp size={16} />}
            size="sm"
            onClick={() => setShowReply(!showReply)}
          >
            {showReply ? "Cancel Reply" : "Quick Reply"}
          </Button>
          <Button
            variant="subtle"
            leftSection={<IconExternalLink size={16} />}
            size="sm"
            onClick={handleReply}
          >
            Reply in {message.source === "gmail" ? "Gmail" : "WhatsApp"}
          </Button>
          <Button
            variant="subtle"
            leftSection={<IconArchive size={16} />}
            size="sm"
            onClick={() => {
              onMarkRead(message.id);
              onClose();
            }}
          >
            Archive
          </Button>
          {!message.is_read && (
            <Button
              variant="subtle"
              leftSection={<IconMailOpened size={16} />}
              size="sm"
              onClick={() => onMarkRead(message.id)}
            >
              Mark Read
            </Button>
          )}
        </Group>
      </Box>
    </Card>
  );
}

// Message List Item
function MessageItem({
  message,
  isSelected,
  onSelect,
  onMarkRead,
}: {
  message: Message;
  isSelected: boolean;
  onSelect: () => void;
  onMarkRead: (id: number) => void;
}) {
  const [isStarred, setIsStarred] = useState(false);
  const time = new Date(message.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const date = new Date(message.timestamp).toLocaleDateString([], { month: "short", day: "numeric" });
  const preview = message.body ? (message.body.length > 80 ? message.body.substring(0, 80) + "..." : message.body) : "(No preview)";

  // Styling based on state
  const getBgColor = () => {
    if (isSelected) {
      return "var(--message-selected-bg)";
    }
    if (!message.is_read) {
      return "var(--message-unread-bg)";
    }
    return "transparent";
  };

  return (
    <Paper
      p="sm"
      radius={0}
      style={{
        background: getBgColor(),
        cursor: "pointer",
        transition: "background 150ms ease",
        borderLeft: isSelected ? `3px solid ${tokens.colors.primary[500]}` : "3px solid transparent",
      }}
      onClick={onSelect}
      className="message-item"
    >
      <Group gap="sm" wrap="nowrap" align="flex-start">
        <Stack gap={4} align="center">
          <Checkbox
            size="xs"
            onClick={(e) => e.stopPropagation()}
          />
          <ActionIcon
            variant="subtle"
            size="xs"
            color={isStarred ? "yellow" : "gray"}
            onClick={(e) => { e.stopPropagation(); setIsStarred(!isStarred); }}
          >
            <IconStar size={14} fill={isStarred ? "currentColor" : "none"} />
          </ActionIcon>
        </Stack>

        <Avatar
          size="md"
          color={message.source === "whatsapp" ? "green" : "red"}
          radius="xl"
        >
          {message.sender.charAt(0).toUpperCase()}
        </Avatar>

        <Box style={{ flex: 1, minWidth: 0 }}>
          <Group gap="xs" justify="space-between" wrap="nowrap" mb={2}>
            <Group gap="xs" wrap="nowrap" style={{ minWidth: 0 }}>
              {!message.is_read && (
                <IconCircle size={8} fill={tokens.colors.primary[500]} color={tokens.colors.primary[500]} />
              )}
              <Text size="sm" fw={!message.is_read ? 700 : 500} truncate style={{ maxWidth: 140 }}>
                {message.sender}
              </Text>
              {message.source === "whatsapp" ? (
                <IconBrandWhatsapp size={14} color={tokens.colors.success[500]} style={{ flexShrink: 0 }} />
              ) : (
                <IconMail size={14} color={tokens.colors.error[500]} style={{ flexShrink: 0 }} />
              )}
            </Group>
            <Text size="xs" c="dimmed" style={{ flexShrink: 0 }}>{date}</Text>
          </Group>

          {message.subject && (
            <Text size="sm" fw={!message.is_read ? 600 : 400} truncate mb={2}>
              {message.subject}
            </Text>
          )}

          <Text size="xs" c="dimmed" truncate>
            {preview}
          </Text>
        </Box>
      </Group>
    </Paper>
  );
}

// Empty State Component
function EmptyState({ icon: Icon, title, description }: {
  icon: React.ElementType;
  title: string;
  description: string;
}) {
  return (
    <Box py="xl" style={{ textAlign: "center" }}>
      <Icon
        size={48}
        stroke={1.5}
        style={{
          color: "var(--mantine-color-dimmed)",
        }}
      />
      <Text size="lg" fw={500} mt="md">{title}</Text>
      <Text c="dimmed" size="sm">{description}</Text>
    </Box>
  );
}

export default function InboxPage() {
  const [filter, setFilter] = useState("all");
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncError, setSyncError] = useState<string | null>(null);
  const [backendConnected, setBackendConnected] = useState<boolean | null>(null);
  const [selectedMessage, setSelectedMessage] = useState<Message | null>(null);
  const [syncEnabled, setSyncEnabled] = useState<boolean | null>(null);
  const [launching, setLaunching] = useState(false);
  const [managerReport, setManagerReport] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const sourceFilter = filter === "all" ? undefined : filter === "whatsapp" ? "whatsapp" : "gmail";
  const { data: messages, loading, error, refetch } = useInboxMessages({ source: sourceFilter, limit: 50 });
  const { data: unreadCount, refetch: refetchUnread } = useUnreadCount();

  // Check backend connection AND sync status
  useEffect(() => {
    const check = async () => {
      try {
        const res = await fetch(`${API_URL}/status`);
        setBackendConnected(res.ok);

        // Check if sync is enabled
        const syncRes = await fetch(`${API_URL}/inbox/sync-status`);
        if (syncRes.ok) {
          const syncData = await syncRes.json();
          setSyncEnabled(syncData.enabled);
        }
      } catch {
        setBackendConnected(false);
      }
    };
    check();
  }, []);

  // Filter messages - handle both API format and local format
  const filteredMessages = messages?.filter((msg) => {
    // Handle both API response (content/read) and local Message format (body/is_read)
    const apiMsg = msg as { read?: boolean; content?: string };
    const localMsg = msg as { is_read?: boolean; body?: string };
    const isRead = localMsg.is_read !== undefined ? localMsg.is_read : (apiMsg.read ?? false);
    const body: string = localMsg.body ?? apiMsg.content ?? "";

    if (unreadOnly && isRead) return false;
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      return (
        msg.sender.toLowerCase().includes(query) ||
        (msg.subject?.toLowerCase().includes(query)) ||
        body.toLowerCase().includes(query)
      );
    }
    return true;
  });

  // Handle launching inbox from this page
  const handleLaunchInbox = async () => {
    setLaunching(true);
    setManagerReport(null);
    try {
      const res = await fetch(`${API_URL}/api/inbox/launch`, { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        setSyncEnabled(true);

        if (data.manager_report?.text) {
          setManagerReport(data.manager_report.text);
        }

        setTimeout(() => {
          refetch();
          refetchUnread();
        }, 500);
        notifications.show({
          title: "Inbox synced",
          message: `Synced ${data?.gmail || 0} email(s) and ${data?.whatsapp || 0} WhatsApp message(s)`,
          color: "green",
        });
      }
    } catch (e) {
      console.error("Failed to launch inbox:", e);
      setManagerReport("Failed to launch inbox sync. Check backend connection.");
    } finally {
      setLaunching(false);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    setSyncError(null);
    try {
      const data = await apiFetch<any>("/inbox/ingest", { method: "POST" });
      refetch();
      refetchUnread();
      notifications.show({
        title: "Sync complete",
        message: `Pulled ${data?.new_messages || 0} new message(s)`,
        color: "green",
      });
    } catch (e) {
      let detail = "Sync failed. Please try again.";
      if (isNetworkError(e)) {
        detail = `Unable to reach backend at ${API_URL}. Start the server and try again.`;
      } else if (e instanceof Error && e.message) {
        detail = e.message;
      } else if (e && typeof e === "object" && "detail" in e) {
        const maybeDetail = (e as { detail?: string }).detail;
        if (maybeDetail) detail = maybeDetail;
      }
      setSyncError(detail);
      console.error("Sync failed:", e);
    } finally {
      setSyncing(false);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await apiFetch("/inbox/messages/mark-read", {
        method: "POST",
        body: JSON.stringify({}),
      });
      refetch();
      refetchUnread();
      setSelectedMessage(null);
    } catch (e) {
      console.error("Failed to mark all as read:", e);
    }
  };

  const handleClearInbox = async (source?: string) => {
    const confirmMsg = source
      ? `Clear all ${source} messages? This cannot be undone.`
      : "Clear ALL inbox messages? This cannot be undone.";

    if (!confirm(confirmMsg)) return;

    try {
      const sourceParam = source ? `?source=${encodeURIComponent(source)}` : "";
      await apiFetch(`/inbox/clear${sourceParam}`, { method: "POST" });
      refetch();
      refetchUnread();
      setSelectedMessage(null);
    } catch (e) {
      console.error("Failed to clear inbox:", e);
    }
  };

  const handleMarkRead = async (id: number) => {
    try {
      await apiFetch(`/inbox/messages/${id}/read`, { method: "PATCH" });
      refetch();
      refetchUnread();
      if (selectedMessage?.id === id) {
        setSelectedMessage({ ...selectedMessage, is_read: true });
      }
    } catch (e) {
      console.error("Failed to mark read:", e);
    }
  };

  const handleSelectMessage = (msg: Message) => {
    setSelectedMessage(msg);
    if (!msg.is_read) {
      handleMarkRead(msg.id);
    }
  };

  const totalMessages = filteredMessages?.length || 0;
  const unreadTotal = unreadCount?.total || 0;
  const whatsappUnread = unreadCount?.whatsapp || 0;
  const gmailUnread = unreadCount?.gmail || 0;

  // Show launch screen if sync not enabled
  if (syncEnabled === false) {
    return (
      <Shell>
        <Page title="Inbox" subtitle="Messages and approvals">
          <Stack gap="md" align="center" justify="center" h="calc(100vh - 200px)">
            {managerReport ? (
              <Card withBorder radius="lg" p="xl" maw={500} w="100%">
                <Group mb="md">
                  <ThemeIcon size={40} radius="xl" variant="gradient" gradient={{ from: tokens.colors.primary[700], to: tokens.colors.primary[500] }}>
                    <IconInbox size={24} />
                  </ThemeIcon>
                  <Text fw={600} size="lg">Manager Report</Text>
                </Group>
                <Box
                  p="md"
                  style={{
                    background: "var(--manager-report-bg)",
                    borderRadius: 8,
                    whiteSpace: "pre-wrap",
                    fontFamily: "monospace",
                    fontSize: rem(14),
                  }}
                >
                  {managerReport}
                </Box>
                <Button
                  mt="md"
                  fullWidth
                  onClick={() => {
                    setSyncEnabled(true);
                    refetch();
                  }}
                >
                  View Inbox
                </Button>
              </Card>
            ) : (
              <>
                <ThemeIcon size={80} radius="xl" variant="light" color="gray">
                  <IconInbox size={40} />
                </ThemeIcon>
                <Title order={2}>Inbox Not Launched</Title>
                <Text c="dimmed" ta="center" maw={400}>
                  Email and WhatsApp sync is disabled. Launch it to start receiving messages.
                </Text>
                <Button
                  size="lg"
                  leftSection={<IconRefresh size={20} />}
                  loading={launching}
                  onClick={handleLaunchInbox}
                >
                  Launch Inbox Sync
                </Button>
                <Text size="xs" c="dimmed">
                  Or go to Settings &rarr; Connectors to configure
                </Text>
              </>
            )}
          </Stack>
        </Page>
      </Shell>
    );
  }

  return (
    <Shell>
      <Page
        title="Inbox"
        subtitle={`${totalMessages} messages${unreadTotal > 0 ? ` - ${unreadTotal} unread` : ""}`}
        actions={
          <Group gap="xs">
            {unreadTotal > 0 && (
              <Button
                leftSection={<IconCheck size={16} />}
                variant="light"
                color="success"
                size="sm"
                onClick={handleMarkAllRead}
              >
                Mark All Read
              </Button>
            )}
            <Menu shadow="md" width={200}>
              <Menu.Target>
                <Button variant="subtle" color="gray" size="sm">
                  <IconTrash size={16} />
                </Button>
              </Menu.Target>
              <Menu.Dropdown>
                <Menu.Label>Clear Messages</Menu.Label>
                <Menu.Item
                  color="red"
                  leftSection={<IconTrash size={14} />}
                  onClick={() => handleClearInbox()}
                >
                  Clear All Messages
                </Menu.Item>
                <Menu.Item
                  leftSection={<IconBrandWhatsapp size={14} />}
                  onClick={() => handleClearInbox("whatsapp")}
                >
                  Clear WhatsApp Only
                </Menu.Item>
                <Menu.Item
                  leftSection={<IconMail size={14} />}
                  onClick={() => handleClearInbox("gmail")}
                >
                  Clear Email Only
                </Menu.Item>
              </Menu.Dropdown>
            </Menu>
            <Button
              leftSection={syncing ? <Loader size={14} /> : <IconRefresh size={16} />}
              variant="light"
              size="sm"
              onClick={handleSync}
              disabled={syncing}
            >
              {syncing ? "Syncing..." : "Sync"}
            </Button>
          </Group>
        }
      >
        <Stack gap="md" h="calc(100vh - 180px)">
          {/* Backend Warning */}
          {backendConnected === false && (
            <Alert icon={<IconPlugConnectedX size={18} />} color="orange" title="Backend not connected" variant="light">
              Start the API to see real messages
            </Alert>
          )}
          {syncError && (
            <Alert color="red" title="Sync failed" variant="light">
              {syncError}
            </Alert>
          )}

          <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} spacing="md">
            <Card withBorder radius="lg">
              <Text size="xs" c="dimmed" tt="uppercase" fw={600}>Messages in view</Text>
              {loading ? (
                <Skeleton height={22} width="40%" mt={6} />
              ) : (
                <Text size="xl" fw={700} mt={4}>{totalMessages}</Text>
              )}
              <Text size="xs" c="dimmed">Matches filters</Text>
            </Card>
            <Card withBorder radius="lg">
              <Text size="xs" c="dimmed" tt="uppercase" fw={600}>Unread total</Text>
              {loading ? (
                <Skeleton height={22} width="40%" mt={6} />
              ) : (
                <Text size="xl" fw={700} mt={4}>{unreadTotal}</Text>
              )}
              <Text size="xs" c="dimmed">Across all sources</Text>
            </Card>
            <Card withBorder radius="lg">
              <Text size="xs" c="dimmed" tt="uppercase" fw={600}>WhatsApp unread</Text>
              {loading ? (
                <Skeleton height={22} width="40%" mt={6} />
              ) : (
                <Text size="xl" fw={700} mt={4}>{whatsappUnread}</Text>
              )}
              <Text size="xs" c="dimmed">Messaging queue</Text>
            </Card>
            <Card withBorder radius="lg">
              <Text size="xs" c="dimmed" tt="uppercase" fw={600}>Gmail unread</Text>
              {loading ? (
                <Skeleton height={22} width="40%" mt={6} />
              ) : (
                <Text size="xl" fw={700} mt={4}>{gmailUnread}</Text>
              )}
              <Text size="xs" c="dimmed">Email queue</Text>
            </Card>
          </SimpleGrid>

          {/* Filter Pills */}
          <Group gap="xs">
            <FilterPill
              label="All"
              active={filter === "all" && !unreadOnly}
              count={messages?.length}
              onClick={() => { setFilter("all"); setUnreadOnly(false); }}
            />
            <FilterPill
              label="Unread"
              active={unreadOnly}
              count={unreadTotal}
              color="blue"
              icon={<IconCircle size={8} fill="currentColor" />}
              onClick={() => setUnreadOnly(!unreadOnly)}
            />
            <Divider orientation="vertical" />
            <FilterPill
              label="WhatsApp"
              active={filter === "whatsapp"}
              count={unreadCount?.whatsapp}
              color="green"
              icon={<IconBrandWhatsapp size={14} />}
              onClick={() => setFilter(filter === "whatsapp" ? "all" : "whatsapp")}
            />
            <FilterPill
              label="Gmail"
              active={filter === "email"}
              count={unreadCount?.gmail}
              color="red"
              icon={<IconMail size={14} />}
              onClick={() => setFilter(filter === "email" ? "all" : "email")}
            />
            <Box style={{ flex: 1 }} />
            <TextInput
              placeholder="Search messages..."
              leftSection={<IconSearch size={16} />}
              size="xs"
              style={{ width: 200 }}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.currentTarget.value)}
            />
          </Group>

          {/* Split View */}
          <Group gap="md" align="stretch" style={{ flex: 1, minHeight: 0 }}>
            {/* Message List */}
            <Card withBorder radius="lg" p={0} style={{ width: 380, flexShrink: 0 }}>
              <ScrollArea h="100%" offsetScrollbars scrollbarSize={6}>
                {loading ? (
                  <Box p="xl" style={{ textAlign: "center" }}>
                    <Loader />
                    <Text c="dimmed" size="sm" mt="md">Loading messages...</Text>
                  </Box>
                ) : filteredMessages && filteredMessages.length > 0 ? (
                  <Stack gap={0}>
                    {filteredMessages.map((msg, i) => (
                      <Box key={msg.id}>
                        <MessageItem
                          message={{
                            ...msg,
                            body: ("body" in msg ? msg.body : ("content" in msg ? (msg as unknown as { content: string }).content : "")) as string,
                            is_read: ("is_read" in msg ? msg.is_read : ("read" in msg ? (msg as unknown as { read: boolean }).read : false)) as boolean,
                            source: (msg.source === "gmail" || msg.source === "whatsapp") ? msg.source : "whatsapp",
                          } as Message}
                          isSelected={selectedMessage?.id === msg.id}
                          onSelect={() => handleSelectMessage({
                            ...msg,
                            body: ("body" in msg ? msg.body : ("content" in msg ? (msg as unknown as { content: string }).content : "")) as string,
                            is_read: ("is_read" in msg ? msg.is_read : ("read" in msg ? (msg as unknown as { read: boolean }).read : false)) as boolean,
                            source: (msg.source === "gmail" || msg.source === "whatsapp") ? msg.source : "whatsapp",
                          } as Message)}
                          onMarkRead={handleMarkRead}
                        />
                        {i < filteredMessages.length - 1 && <Divider />}
                      </Box>
                    ))}
                  </Stack>
                ) : (
                  <EmptyState
                    icon={IconInbox}
                    title={searchQuery ? "No results" : "No messages"}
                    description={searchQuery ? "Try a different search term" : "Click Sync to fetch messages"}
                  />
                )}
              </ScrollArea>
            </Card>

            {/* Message Detail */}
            <Box style={{ flex: 1, minWidth: 0 }}>
              {selectedMessage ? (
                <MessageDetail
                  message={selectedMessage}
                  onClose={() => setSelectedMessage(null)}
                  onMarkRead={handleMarkRead}
                />
              ) : (
                <Card withBorder radius="lg" h="100%">
                  <Box h="100%" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <EmptyState
                      icon={IconMail}
                      title="Select a message"
                      description="Click on a message to view its contents"
                    />
                  </Box>
                </Card>
              )}
            </Box>
          </Group>
        </Stack>
      </Page>
    </Shell>
  );
}
