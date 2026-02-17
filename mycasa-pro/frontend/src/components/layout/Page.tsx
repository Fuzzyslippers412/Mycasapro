'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Box,
  Group,
  Stack,
  Text,
  Breadcrumbs,
  Anchor,
  Paper,
  Transition,
} from '@mantine/core';
import { IconChevronRight, IconHome } from '@tabler/icons-react';

interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface PageProps {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  breadcrumbs?: BreadcrumbItem[];
  children: React.ReactNode;
  fullWidth?: boolean;
  noPadding?: boolean;
}

// Route to label mapping for auto-generated breadcrumbs
const routeLabels: Record<string, string> = {
  '': 'Dashboard',
  'inbox': 'Inbox',
  'finance': 'Finance',
  'maintenance': 'Maintenance',
  'contractors': 'Contractors',
  'projects': 'Projects',
  'security': 'Security',
  'settings': 'Settings',
  'system': 'Tasks & Logs',
};

// Generate breadcrumbs from pathname
function generateBreadcrumbs(pathname: string): BreadcrumbItem[] {
  const segments = pathname.split('/').filter(Boolean);

  if (segments.length === 0) {
    return [{ label: 'Dashboard' }];
  }

  const breadcrumbs: BreadcrumbItem[] = [
    { label: 'Dashboard', href: '/' },
  ];

  let currentPath = '';
  segments.forEach((segment, index) => {
    currentPath += `/${segment}`;
    const isLast = index === segments.length - 1;
    const label = routeLabels[segment] || segment.charAt(0).toUpperCase() + segment.slice(1);

    breadcrumbs.push({
      label,
      href: isLast ? undefined : currentPath,
    });
  });

  return breadcrumbs;
}

export function Page({
  title,
  subtitle,
  actions,
  breadcrumbs: customBreadcrumbs,
  children,
  fullWidth = false,
  noPadding = false,
}: PageProps) {
  const pathname = usePathname();

  // Use custom breadcrumbs or auto-generate from pathname
  const breadcrumbs = customBreadcrumbs || generateBreadcrumbs(pathname);

  return (
    <Box
      style={{
        maxWidth: fullWidth ? '100%' : 1200,
        margin: '0 auto',
        padding: noPadding ? 0 : undefined,
      }}
    >
      <Transition mounted={true} transition="fade" duration={200}>
        {(styles) => (
          <Stack gap="md" style={styles}>
            {/* Breadcrumbs */}
            {breadcrumbs && breadcrumbs.length > 0 && (
              <Breadcrumbs
                separator={
                  <IconChevronRight
                    size={14}
                    style={{ color: 'var(--mantine-color-dimmed)' }}
                  />
                }
                styles={{
                  root: {
                    flexWrap: 'wrap',
                  },
                  separator: {
                    margin: '0 4px',
                  },
                }}
              >
                {breadcrumbs.map((item, index) => {
                  const isFirst = index === 0;
                  const isLast = index === breadcrumbs.length - 1;

                  if (isLast || !item.href) {
                    return (
                      <Text
                        key={index}
                        size="sm"
                        fw={500}
                        c={isLast ? 'dark' : 'dimmed'}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 4,
                        }}
                      >
                        {isFirst && <IconHome size={14} />}
                        {item.label}
                      </Text>
                    );
                  }

                  return (
                    <Anchor
                      key={index}
                      component={Link}
                      href={item.href}
                      size="sm"
                      c="dimmed"
                      underline="hover"
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 4,
                        transition: 'color 150ms ease',
                      }}
                    >
                      {isFirst && <IconHome size={14} />}
                      {item.label}
                    </Anchor>
                  );
                })}
              </Breadcrumbs>
            )}

            {/* Page header */}
            <Group justify="space-between" align="flex-start" className="page-header" wrap="wrap">
              <Stack gap={4}>
                <Text
                  fw={700}
                  size="lg"
                  style={{
                    fontSize: 'clamp(1.25rem, 2vw, 1.6rem)',
                    letterSpacing: '-0.02em',
                    color: 'var(--mantine-color-text)',
                  }}
                >
                  {title}
                </Text>
                {subtitle && (
                  <Text
                    size="sm"
                    c="dimmed"
                    style={{
                      maxWidth: 600,
                      lineHeight: 1.5,
                    }}
                  >
                    {subtitle}
                  </Text>
                )}
              </Stack>
              {actions && (
                <Group gap="sm" wrap="wrap">
                  {actions}
                </Group>
              )}
            </Group>

            {/* Page content */}
            <Box>{children}</Box>
          </Stack>
        )}
      </Transition>
    </Box>
  );
}

// Page section component for consistent spacing
interface PageSectionProps {
  title?: string;
  subtitle?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
  noPadding?: boolean;
}

export function PageSection({
  title,
  subtitle,
  actions,
  children,
  noPadding = false,
}: PageSectionProps) {
  return (
    <Stack gap="sm">
      {(title || actions) && (
        <Group justify="space-between" align="center">
          <Stack gap={2}>
            {title && (
              <Text fw={600} size="md">
                {title}
              </Text>
            )}
            {subtitle && (
              <Text size="xs" c="dimmed">
                {subtitle}
              </Text>
            )}
          </Stack>
          {actions}
        </Group>
      )}
      <Box>{children}</Box>
    </Stack>
  );
}

// Page card wrapper for consistent card styling
interface PageCardProps {
  children: React.ReactNode;
  accent?: 'primary' | 'success' | 'warning' | 'error' | 'info';
  clickable?: boolean;
  onClick?: () => void;
  className?: string;
}

export function PageCard({
  children,
  accent,
  clickable = false,
  onClick,
  className = '',
}: PageCardProps) {
  const accentClass = accent ? `card-accent-left ${accent}` : '';
  const clickableClass = clickable ? 'card-clickable' : '';

  return (
    <Paper
      p="lg"
      radius="lg"
      withBorder
      className={`${accentClass} ${clickableClass} ${className}`}
      onClick={onClick}
      style={{
        cursor: clickable ? 'pointer' : undefined,
      }}
    >
      {children}
    </Paper>
  );
}
