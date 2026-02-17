'use client';

import { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { getApiBaseUrl } from '@/lib/api';
import {
  AppShell,
  Text,
  Burger,
  Group,
  Avatar,
  Menu,
  NavLink,
  Stack,
  Divider,
  Badge,
  ActionIcon,
  Tooltip,
  Box,
  Collapse,
  Indicator,
  ThemeIcon,
  Transition,
  useMantineColorScheme,
  UnstyledButton,
  rem,
  TextInput,
  Kbd,
  Paper,
  ScrollArea,
  Tabs,
  Card,
  Center,
  Skeleton,
  Alert,
} from '@mantine/core';
import { useMediaQuery, useDisclosure, useHotkeys } from '@mantine/hooks';
import {
  IconUser,
  IconSettings,
  IconLogout,
  IconLayoutDashboard,
  IconInbox,
  IconWallet,
  IconTool,
  IconUsers,
  IconBuildingEstate,
  IconShieldLock,
  IconChecklist,
  IconBell,
  IconSun,
  IconMoon,
  IconSearch,
  IconChevronRight,
  IconChevronDown,
  IconStar,
  IconStarFilled,
  IconHome,
  IconActivity,
  IconCircleCheck,
  IconAlertCircle,
  IconBolt,
  IconMenu2,
  IconLayoutSidebarLeftCollapse,
  IconLayoutSidebarRightCollapse,
  IconCommand,
  IconServer,
} from '@tabler/icons-react';
import { tokens } from '@/theme/tokens';
import { GlobalChat } from '@/components/GlobalChat';
import { useAuditEvents, useTasks, useUnreadCount, useSystemStatus } from '@/lib/hooks';

// Navigation section type
interface NavSection {
  title: string;
  items: NavItem[];
}

interface NavItem {
  label: string;
  href: string;
  icon: React.ElementType;
  badge?: string | number;
  badgeColor?: string;
}

// System status indicator
function SystemStatus({ status }: { status: 'healthy' | 'warning' | 'error' }) {
  const colors = {
    healthy: tokens.colors.success[500],
    warning: tokens.colors.warn[500],
    error: tokens.colors.error[500],
  };

  const labels = {
    healthy: 'All systems operational',
    warning: 'Some issues detected',
    error: 'System error',
  };

  return (
    <Tooltip label={labels[status]} position="bottom">
      <Box
        style={{
          width: 8,
          height: 8,
          borderRadius: '50%',
          backgroundColor: colors[status],
          boxShadow: `0 0 0 3px ${colors[status]}33`,
        }}
        className={status !== 'healthy' ? 'animate-pulse' : ''}
      />
    </Tooltip>
  );
}

// Theme toggle button
function ThemeToggle() {
  const { setColorScheme, colorScheme } = useMantineColorScheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Prevent hydration mismatch by showing consistent icon until mounted
  const isDark = mounted && colorScheme === 'dark';

  return (
    <Tooltip label={`Switch to ${isDark ? 'light' : 'dark'} mode`}>
      <ActionIcon
        variant="subtle"
        color="gray"
        radius="lg"
        size="lg"
        onClick={() => setColorScheme(isDark ? 'light' : 'dark')}
        aria-label="Toggle color scheme"
      >
        {isDark ? <IconSun size={20} /> : <IconMoon size={20} />}
      </ActionIcon>
    </Tooltip>
  );
}

// Notification dropdown
function NotificationBell() {
  const { data, loading, error, refetch } = useAuditEvents(25);
  const [lastSeen, setLastSeen] = useState<string | null>(null);
  const events = data?.events || [];

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const stored = window.localStorage.getItem('mycasa:last_seen_audit');
    if (stored) setLastSeen(stored);
  }, []);

  const newestTimestamp = events[0]?.created_at || null;
  const unseenCount = useMemo(() => {
    if (error || !events.length) return 0;
    if (!lastSeen) return events.length;
    const last = new Date(lastSeen).getTime();
    return events.filter((e) => {
      const ts = e.created_at ? new Date(e.created_at).getTime() : 0;
      return ts > last;
    }).length;
  }, [events, lastSeen, error]);

  const markSeen = () => {
    if (!newestTimestamp || typeof window === 'undefined') return;
    window.localStorage.setItem('mycasa:last_seen_audit', newestTimestamp);
    setLastSeen(newestTimestamp);
  };

  return (
    <Menu
      shadow="lg"
      width={360}
      position="bottom-end"
      onOpen={() => {
        refetch();
        markSeen();
      }}
    >
      <Menu.Target>
        <Indicator
          color="red"
          size={16}
          label={unseenCount}
          disabled={unseenCount === 0}
          offset={4}
        >
          <ActionIcon variant="subtle" color="gray" radius="lg" size="lg">
            <IconBell size={20} />
          </ActionIcon>
        </Indicator>
      </Menu.Target>

      <Menu.Dropdown>
        <Menu.Label>
          <Group justify="space-between">
            <Text fw={600}>Notifications</Text>
            {unseenCount > 0 && (
              <Text
                size="xs"
                c="dimmed"
                style={{ cursor: 'pointer' }}
                onClick={markSeen}
              >
                Mark seen
              </Text>
            )}
          </Group>
        </Menu.Label>
        <Divider />
        <ScrollArea h={240}>
          {loading && (
            <Menu.Item>
              <Text size="sm" c="dimmed">Loading activity…</Text>
            </Menu.Item>
          )}
          {error && (
            <Menu.Item>
              <Text size="sm" c="red">Unable to load activity.</Text>
            </Menu.Item>
          )}
          {!loading && !error && events.length === 0 && (
            <Menu.Item>
              <Text size="sm" c="dimmed">No notifications yet.</Text>
            </Menu.Item>
          )}
          {!loading && !error && events.map((event) => {
            const title = event.event_type.replace(/_/g, " ");
            const time = event.created_at
              ? new Date(event.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
              : "—";
            return (
              <Menu.Item key={event.id}>
                <Stack gap={4}>
                  <Text size="sm" fw={500}>
                    {title}
                  </Text>
                  <Text size="xs" c="dimmed">
                    {event.source || "system"} • {time}
                  </Text>
                  {event.status && event.status !== "success" && (
                    <Text size="xs" c="red">
                      {event.status}
                    </Text>
                  )}
                </Stack>
              </Menu.Item>
            );
          })}
        </ScrollArea>
        <Divider />
        <Menu.Item ta="center" c="primary" component={Link} href="/logs">
          <Text size="sm" fw={500}>View all notifications</Text>
        </Menu.Item>
      </Menu.Dropdown>
    </Menu>
  );
}

function RightRail() {
  const activity = useAuditEvents(15);
  const tasks = useTasks({ status: "pending", limit: 6 });
  const system = useSystemStatus(30000);
  const systemIndicator: "healthy" | "warning" | "error" = system.error
    ? "error"
    : system.data
      ? "healthy"
      : "warning";

  const activityEvents = activity.data?.events || [];
  const pendingTasks = tasks.data || [];

  return (
    <Tabs defaultValue="activity" variant="pills">
      <Tabs.List>
        <Tabs.Tab value="activity" leftSection={<IconActivity size={14} />}>
          Activity
        </Tabs.Tab>
        <Tabs.Tab value="alerts" leftSection={<IconAlertCircle size={14} />}>
          Alerts
        </Tabs.Tab>
        <Tabs.Tab value="system" leftSection={<IconServer size={14} />}>
          System
        </Tabs.Tab>
      </Tabs.List>

      <Tabs.Panel value="activity" pt="sm">
        <Card radius="md" p="sm">
          {activity.loading && (
            <Stack gap="xs">
              <Skeleton height={16} />
              <Skeleton height={16} />
              <Skeleton height={16} />
            </Stack>
          )}
          {activity.error && (
            <Alert color="red" title="Activity unavailable">
              Unable to load recent activity.
            </Alert>
          )}
          {!activity.loading && !activity.error && activityEvents.length === 0 && (
            <Center py="md">
              <Text size="sm" c="dimmed">
                No recent activity.
              </Text>
            </Center>
          )}
          {!activity.loading && !activity.error && activityEvents.length > 0 && (
            <Stack gap="sm">
              {activityEvents.slice(0, 8).map((event: any) => (
                <Group key={event.id} gap="xs" align="flex-start">
                  <Badge size="xs" variant="light">
                    {event.action?.split(".")[0] || "event"}
                  </Badge>
                  <Stack gap={2}>
                    <Text size="sm" fw={500}>
                      {event.action || "Activity"}
                    </Text>
                    <Text size="xs" c="dimmed">
                      {event.created_at
                        ? new Date(event.created_at).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })
                        : "Just now"}
                    </Text>
                  </Stack>
                </Group>
              ))}
            </Stack>
          )}
        </Card>
      </Tabs.Panel>

      <Tabs.Panel value="alerts" pt="sm">
        <Card radius="md" p="sm">
          {tasks.loading && (
            <Stack gap="xs">
              <Skeleton height={16} />
              <Skeleton height={16} />
              <Skeleton height={16} />
            </Stack>
          )}
          {tasks.error && (
            <Alert color="red" title="Alerts unavailable">
              Unable to load pending tasks.
            </Alert>
          )}
          {!tasks.loading && !tasks.error && pendingTasks.length === 0 && (
            <Center py="md">
              <Text size="sm" c="dimmed">
                No pending tasks.
              </Text>
            </Center>
          )}
          {!tasks.loading && !tasks.error && pendingTasks.length > 0 && (
            <Stack gap="sm">
              {pendingTasks.slice(0, 6).map((task: any) => (
                <Group key={task.id} justify="space-between" align="center">
                  <Text size="sm" fw={500}>
                    {task.title}
                  </Text>
                  <Badge size="xs" color={task.priority === "high" ? "red" : "gray"}>
                    {task.priority || "pending"}
                  </Badge>
                </Group>
              ))}
            </Stack>
          )}
        </Card>
      </Tabs.Panel>

      <Tabs.Panel value="system" pt="sm">
        <Card radius="md" p="sm">
          {system.loading && (
            <Stack gap="xs">
              <Skeleton height={16} />
              <Skeleton height={16} />
              <Skeleton height={16} />
            </Stack>
          )}
          {system.error && (
            <Alert color="red" title="System unavailable">
              Unable to load system status.
            </Alert>
          )}
          {!system.loading && !system.error && system.data && (
            <Stack gap="xs">
              <Group justify="space-between">
                <Text size="sm" c="dimmed">
                  System
                </Text>
                <Badge size="sm" color={system.data.running ? "green" : "yellow"} variant="light">
                  {system.data.running ? "Running" : "Stopped"}
                </Badge>
              </Group>
              {system.data.last_startup && (
                <Group justify="space-between">
                  <Text size="sm" c="dimmed">
                    Last startup
                  </Text>
                  <Text size="sm" fw={500}>
                    {new Date(system.data.last_startup).toLocaleString()}
                  </Text>
                </Group>
              )}
              {system.data.last_backup && (
                <Group justify="space-between">
                  <Text size="sm" c="dimmed">
                    Last backup
                  </Text>
                  <Text size="sm" fw={500}>
                    {new Date(system.data.last_backup).toLocaleString()}
                  </Text>
                </Group>
              )}
              {system.data.last_shutdown && (
                <Group justify="space-between">
                  <Text size="sm" c="dimmed">
                    Last shutdown
                  </Text>
                  <Text size="sm" fw={500}>
                    {new Date(system.data.last_shutdown).toLocaleString()}
                  </Text>
                </Group>
              )}
              {!system.data.last_startup && !system.data.last_backup && !system.data.last_shutdown && (
                <Text size="sm" c="dimmed">
                  No lifecycle events recorded yet.
                </Text>
              )}
            </Stack>
          )}
          {!system.loading && !system.error && !system.data && (
            <Center py="md">
              <Text size="sm" c="dimmed">
                System status unavailable.
              </Text>
            </Center>
          )}
        </Card>
      </Tabs.Panel>
    </Tabs>
  );
}

// Search spotlight button
function SearchButton({ onClick }: { onClick: () => void }) {
  return (
    <Tooltip label="Search (⌘K)">
      <UnstyledButton
        onClick={onClick}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '6px 12px',
          borderRadius: 8,
          backgroundColor: 'var(--mantine-color-gray-1)',
          border: '1px solid var(--mantine-color-gray-3)',
          color: 'var(--mantine-color-gray-6)',
          transition: 'all 150ms ease',
        }}
        className="search-button"
      >
        <IconSearch size={16} />
        <Text size="sm" c="dimmed" visibleFrom="md">
          Search...
        </Text>
        <Kbd size="xs" ml="auto" visibleFrom="md">
          ⌘K
        </Kbd>
      </UnstyledButton>
    </Tooltip>
  );
}

// Quick actions dropdown
function QuickActions() {
  const router = useRouter();

  const actions = [
    { label: 'Add Task', icon: IconChecklist, href: '/maintenance' },
    { label: 'Send Message', icon: IconInbox, href: '/inbox' },
    { label: 'View Finance', icon: IconWallet, href: '/finance' },
    { label: 'Check Security', icon: IconShieldLock, href: '/security' },
  ];

  return (
    <Menu shadow="md" width={200} position="bottom-end">
      <Menu.Target>
        <Tooltip label="Quick Actions">
          <ActionIcon variant="subtle" color="gray" radius="lg" size="lg">
            <IconBolt size={20} />
          </ActionIcon>
        </Tooltip>
      </Menu.Target>

      <Menu.Dropdown>
        <Menu.Label>Quick Actions</Menu.Label>
        {actions.map((action) => (
          <Menu.Item
            key={action.label}
            leftSection={<action.icon size={16} />}
            onClick={() => router.push(action.href)}
          >
            {action.label}
          </Menu.Item>
        ))}
      </Menu.Dropdown>
    </Menu>
  );
}

// Collapsible nav section
function NavSection({
  title,
  items,
  pathname,
  collapsed,
  defaultExpanded = true,
}: {
  title: string;
  items: NavItem[];
  pathname: string;
  collapsed: boolean;
  defaultExpanded?: boolean;
}) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  if (collapsed) {
    return (
      <Stack gap={4}>
        {items.map((item) => (
          <Tooltip key={item.href} label={item.label} position="right" withArrow>
            <NavLink
              component={Link}
              href={item.href}
              leftSection={
                <Indicator
                  color={item.badgeColor || 'primary'}
                  size={8}
                  disabled={!item.badge}
                  offset={-2}
                >
                  <item.icon size={20} />
                </Indicator>
              }
              active={pathname === item.href}
              variant="light"
              color="primary"
              style={{ padding: '12px 16px', justifyContent: 'center' }}
            />
          </Tooltip>
        ))}
      </Stack>
    );
  }

  return (
    <Stack gap={4}>
      <UnstyledButton
        onClick={() => setExpanded(!expanded)}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '4px 8px',
          borderRadius: 6,
        }}
      >
        <Text size="xs" c="dimmed" tt="uppercase" fw={700} style={{ letterSpacing: 0.8 }}>
          {title}
        </Text>
        {expanded ? <IconChevronDown size={14} /> : <IconChevronRight size={14} />}
      </UnstyledButton>

      <Collapse in={expanded}>
        <Stack gap={2}>
          {items.map((item) => (
            <NavLink
              key={item.href}
              component={Link}
              href={item.href}
              label={item.label}
              leftSection={<item.icon size={18} />}
              rightSection={
                item.badge && (
                  <Badge size="xs" variant="light" color={item.badgeColor || 'primary'}>
                    {item.badge}
                  </Badge>
                )
              }
              active={pathname === item.href}
              variant="light"
              color="primary"
            />
          ))}
        </Stack>
      </Collapse>
    </Stack>
  );
}

// Favorites section
function FavoritesSection({
  favorites,
  pathname,
  collapsed,
  onToggleFavorite,
}: {
  favorites: NavItem[];
  pathname: string;
  collapsed: boolean;
  onToggleFavorite: (href: string) => void;
}) {
  if (favorites.length === 0) return null;

  if (collapsed) {
    return (
      <Stack gap={4}>
        <Divider />
        {favorites.map((item) => (
          <Tooltip key={item.href} label={item.label} position="right" withArrow>
            <NavLink
              component={Link}
              href={item.href}
              leftSection={<item.icon size={20} />}
              active={pathname === item.href}
              variant="light"
              color="warning"
              style={{ padding: '12px 16px', justifyContent: 'center' }}
            />
          </Tooltip>
        ))}
      </Stack>
    );
  }

  return (
    <Stack gap={4}>
      <Divider />
      <Text size="xs" c="dimmed" tt="uppercase" fw={700} px={8} style={{ letterSpacing: 0.8 }}>
        Favorites
      </Text>
      {favorites.map((item) => (
        <NavLink
          key={item.href}
          component={Link}
          href={item.href}
          label={item.label}
          leftSection={<item.icon size={18} />}
          rightSection={
            <ActionIcon
              size="xs"
              variant="subtle"
              color="yellow"
              onClick={(e) => {
                e.preventDefault();
                onToggleFavorite(item.href);
              }}
            >
              <IconStarFilled size={14} />
            </ActionIcon>
          }
          active={pathname === item.href}
          variant="light"
          color="primary"
        />
      ))}
    </Stack>
  );
}

export function Shell({ children }: { children: React.ReactNode }) {
  const [mobileOpened, { toggle: toggleMobile, close: closeMobile }] = useDisclosure();
  const [desktopCollapsed, setDesktopCollapsed] = useState(false);
  const [searchOpened, { open: openSearch, close: closeSearch }] = useDisclosure();
  const [favorites, setFavorites] = useState<string[]>(['/finance']);
  const pathname = usePathname();
  const router = useRouter();
  const { logout, user, avatarVersion } = useAuth();
  const apiBase = getApiBaseUrl();
  const avatarSrc = user?.avatar_url
    ? `${user.avatar_url.startsWith('http') ? '' : apiBase}${user.avatar_url}?v=${avatarVersion}`
    : undefined;

  const isMobile = useMediaQuery('(max-width: 768px)');
  const unreadCount = useUnreadCount();
  const pendingTasks = useTasks({ status: 'pending', limit: 200 });
  const headerSystem = useSystemStatus(30000);
  const headerSystemIndicator: "healthy" | "warning" | "error" = headerSystem.error
    ? "error"
    : headerSystem.data
      ? "healthy"
      : "warning";
  const systemIndicator = headerSystemIndicator;

  // Hot keys
  useHotkeys([
    ['mod+K', () => openSearch()],
    ['mod+B', () => setDesktopCollapsed((c) => !c)],
  ]);

  // Close mobile nav on route change
  useEffect(() => {
    closeMobile();
  }, [pathname, closeMobile]);

  // Navigation structure (badges are real data when available)
  const workspaceItems: NavItem[] = useMemo(() => {
    const unreadTotal = unreadCount.data?.total;
    const pendingCount = pendingTasks.data?.length;
    return [
      { label: 'Dashboard', href: '/', icon: IconLayoutDashboard },
      {
        label: 'Inbox',
        href: '/inbox',
        icon: IconInbox,
        badge: typeof unreadTotal === 'number' ? unreadTotal : undefined,
        badgeColor: 'red',
      },
      { label: 'Finance', href: '/finance', icon: IconWallet },
      {
        label: 'Maintenance',
        href: '/maintenance',
        icon: IconTool,
        badge: typeof pendingCount === 'number' ? pendingCount : undefined,
        badgeColor: 'orange',
      },
      { label: 'Contractors', href: '/contractors', icon: IconUsers },
      { label: 'Projects', href: '/projects', icon: IconBuildingEstate },
      { label: 'Security', href: '/security', icon: IconShieldLock },
    ];
  }, [pendingTasks.data, unreadCount.data]);

  const systemItems: NavItem[] = [
    { label: 'Settings', href: '/settings', icon: IconSettings },
    { label: 'Tasks & Logs', href: '/system', icon: IconChecklist },
  ];

  // Get favorite items
  const favoriteItems = workspaceItems.filter((item) => favorites.includes(item.href));

  const toggleFavorite = (href: string) => {
    setFavorites((prev) =>
      prev.includes(href) ? prev.filter((f) => f !== href) : [...prev, href]
    );
  };

  // Search items for spotlight
  const searchItems = [...workspaceItems, ...systemItems].map((item) => ({
    id: item.href,
    label: item.label,
    description: `Navigate to ${item.label}`,
    onClick: () => router.push(item.href),
    leftSection: <item.icon size={18} />,
  }));

  return (
    <>
      <AppShell
        header={{ height: 64 }}
        navbar={{
          width: desktopCollapsed ? 72 : 280,
          breakpoint: 'sm',
          collapsed: { mobile: !mobileOpened, desktop: false },
        }}
        aside={{
          width: 320,
          breakpoint: 'lg',
          collapsed: { mobile: true, desktop: false },
        }}
        padding="md"
        transitionDuration={200}
        transitionTimingFunction="ease"
      >
        {/* Header */}
        <AppShell.Header
          className="app-shell-header"
          style={{
            backgroundColor: 'var(--surface-1)',
            borderBottom: '1px solid var(--border-1)',
          }}
        >
          <Group h="100%" px="md" justify="space-between">
            {/* Left side */}
            <Group h="100%" gap="md">
              {isMobile && (
                <Burger opened={mobileOpened} onClick={toggleMobile} size="sm" />
              )}

              {!isMobile && (
                <Tooltip label={desktopCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}>
                  <ActionIcon
                    variant="subtle"
                    color="gray"
                    radius="lg"
                    size="lg"
                    onClick={() => setDesktopCollapsed((c) => !c)}
                  >
                    {desktopCollapsed ? (
                      <IconLayoutSidebarRightCollapse size={20} />
                    ) : (
                      <IconLayoutSidebarLeftCollapse size={20} />
                    )}
                  </ActionIcon>
                </Tooltip>
              )}

              <Group gap="xs">
                <ThemeIcon
                  size="lg"
                  radius="md"
                  variant="gradient"
                  gradient={{ from: tokens.colors.primary[700], to: tokens.colors.primary[500], deg: 135 }}
                >
                  <IconHome size={18} color="white" />
                </ThemeIcon>
                <Text fw={700} size="lg" visibleFrom="sm">
                  MyCasa Pro
                </Text>
              </Group>

              <Divider orientation="vertical" visibleFrom="md" />

              <Box visibleFrom="sm">
                <SearchButton onClick={openSearch} />
              </Box>
            </Group>

            {/* Right side */}
            <Group gap="xs">
              <SystemStatus status={headerSystemIndicator} />
              <Divider orientation="vertical" h={24} my="auto" />
              <QuickActions />
              <NotificationBell />
              <ThemeToggle />

              <Menu shadow="md" width={200} position="bottom-end">
                <Menu.Target>
                  <Avatar
                    src={avatarSrc}
                    alt="User"
                    radius="xl"
                    size="md"
                    style={{ cursor: 'pointer' }}
                  />
                </Menu.Target>

                <Menu.Dropdown>
                  <Menu.Label>Account</Menu.Label>
                  <Menu.Item
                    leftSection={<IconUser size={16} />}
                    component={Link}
                    href="/settings?tab=profile"
                  >
                    Profile
                  </Menu.Item>
                  <Menu.Item
                    leftSection={<IconSettings size={16} />}
                    component={Link}
                    href="/settings"
                  >
                    Settings
                  </Menu.Item>
                  <Menu.Divider />
                  <Menu.Item leftSection={<IconLogout size={16} />} color="red" onClick={logout}>
                    Logout
                  </Menu.Item>
                </Menu.Dropdown>
              </Menu>
            </Group>
          </Group>
        </AppShell.Header>

        {/* Sidebar */}
        <AppShell.Navbar
          p={desktopCollapsed ? 'xs' : 'md'}
          className="app-shell-navbar"
          style={{
            backgroundColor: 'var(--surface-1)',
            borderRight: '1px solid var(--border-1)',
            transition: 'width 200ms ease, padding 200ms ease',
          }}
        >
          <ScrollArea h="100%" scrollbarSize={6}>
            <Stack gap="md">
              {/* Favorites */}
              <FavoritesSection
                favorites={favoriteItems}
                pathname={pathname}
                collapsed={desktopCollapsed && !isMobile}
                onToggleFavorite={toggleFavorite}
              />

              {/* Workspace section */}
              <NavSection
                title="Workspace"
                items={workspaceItems}
                pathname={pathname}
                collapsed={desktopCollapsed && !isMobile}
                defaultExpanded={true}
              />

              {/* System section */}
              <NavSection
                title="System"
                items={systemItems}
                pathname={pathname}
                collapsed={desktopCollapsed && !isMobile}
                defaultExpanded={true}
              />
            </Stack>
          </ScrollArea>
        </AppShell.Navbar>

        {/* Right rail */}
        <AppShell.Aside
          p="md"
          className="app-shell-aside"
          style={{
            backgroundColor: 'var(--surface-1)',
            borderLeft: '1px solid var(--border-1)',
          }}
        >
          <Stack gap="md">
            <Group justify="space-between">
              <Text size="sm" fw={600}>
                Activity & Status
              </Text>
            </Group>
            <RightRail />
          </Stack>
        </AppShell.Aside>

        {/* Main content */}
        <AppShell.Main
          style={{
            backgroundColor: 'var(--bg)',
            transition: 'background-color 200ms ease',
          }}
        >
          {children}
        </AppShell.Main>
      </AppShell>

      {/* Search Spotlight */}
      {searchOpened && (
        <Paper
          shadow="xl"
          radius="lg"
          style={{
            position: 'fixed',
            top: '20%',
            left: '50%',
            transform: 'translateX(-50%)',
            width: '100%',
            maxWidth: 600,
            zIndex: 1000,
          }}
        >
          <TextInput
            placeholder="Search pages, actions..."
            leftSection={<IconSearch size={18} />}
            rightSection={
              <Kbd size="xs" onClick={closeSearch} style={{ cursor: 'pointer' }}>
                Esc
              </Kbd>
            }
            size="lg"
            autoFocus
            styles={{
              input: {
                border: 'none',
                borderRadius: rem(16),
              },
            }}
            onKeyDown={(e) => {
              if (e.key === 'Escape') closeSearch();
            }}
          />
          <Divider />
          <Stack gap={0} p="xs">
            {searchItems.map((item) => (
              <UnstyledButton
                key={item.id}
                onClick={() => {
                  item.onClick();
                  closeSearch();
                }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                  padding: '10px 12px',
                  borderRadius: 8,
                }}
                className="message-item"
              >
                {item.leftSection}
                <div>
                  <Text size="sm" fw={500}>
                    {item.label}
                  </Text>
                  <Text size="xs" c="dimmed">
                    {item.description}
                  </Text>
                </div>
              </UnstyledButton>
            ))}
          </Stack>
        </Paper>
      )}

      {/* Backdrop for search */}
      {searchOpened && (
        <Box
          onClick={closeSearch}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            backdropFilter: 'blur(4px)',
            zIndex: 999,
          }}
        />
      )}

      {/* Global Chat - persistent on all pages */}
      <GlobalChat />
    </>
  );
}
