'use client';

import { useState, useMemo } from 'react';
import {
  Table,
  Group,
  Text,
  Box,
  Stack,
  Skeleton,
  ActionIcon,
  Tooltip,
  ScrollArea,
  rem,
} from '@mantine/core';
import {
  IconArrowUp,
  IconArrowDown,
  IconArrowsSort,
  IconInbox,
} from '@tabler/icons-react';

interface Column<T> {
  key: string;
  label: string;
  sortable?: boolean;
  width?: number | string;
  align?: 'left' | 'center' | 'right';
  render?: (value: unknown, row: T) => React.ReactNode;
}

interface WidgetTableProps<T extends object> {
  columns: Column<T>[];
  data: T[];
  loading?: boolean;
  loadingRows?: number;
  emptyMessage?: string;
  emptyIcon?: React.ReactNode;
  stickyHeader?: boolean;
  maxHeight?: number | string;
  striped?: boolean;
  highlightOnHover?: boolean;
  onRowClick?: (row: T) => void;
}

type SortDirection = 'asc' | 'desc' | null;

export function WidgetTable<T extends object>({
  columns,
  data,
  loading = false,
  loadingRows = 5,
  emptyMessage = 'No data available',
  emptyIcon,
  stickyHeader = false,
  maxHeight,
  striped = true,
  highlightOnHover = true,
  onRowClick,
}: WidgetTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>(null);

  // Handle sorting
  const handleSort = (key: string) => {
    if (sortKey === key) {
      if (sortDirection === 'asc') {
        setSortDirection('desc');
      } else if (sortDirection === 'desc') {
        setSortKey(null);
        setSortDirection(null);
      }
    } else {
      setSortKey(key);
      setSortDirection('asc');
    }
  };

  // Sort data
  const sortedData = useMemo(() => {
    if (!sortKey || !sortDirection) return data;

    return [...data].sort((a, b) => {
      const aValue = (a as Record<string, unknown>)[sortKey];
      const bValue = (b as Record<string, unknown>)[sortKey];

      if (aValue === bValue) return 0;
      if (aValue === null || aValue === undefined) return 1;
      if (bValue === null || bValue === undefined) return -1;

      const comparison = aValue < bValue ? -1 : 1;
      return sortDirection === 'asc' ? comparison : -comparison;
    });
  }, [data, sortKey, sortDirection]);

  // Render sort icon
  const renderSortIcon = (key: string) => {
    if (sortKey !== key) {
      return <IconArrowsSort size={14} style={{ opacity: 0.4 }} />;
    }
    return sortDirection === 'asc' ? (
      <IconArrowUp size={14} />
    ) : (
      <IconArrowDown size={14} />
    );
  };

  // Loading skeleton
  if (loading) {
    return (
      <Table striped={striped}>
        <Table.Thead>
          <Table.Tr>
            {columns.map((col) => (
              <Table.Th key={col.key} style={{ width: col.width }}>
                <Skeleton height={16} width="60%" radius="sm" />
              </Table.Th>
            ))}
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {Array.from({ length: loadingRows }).map((_, i) => (
            <Table.Tr key={i}>
              {columns.map((col) => (
                <Table.Td key={col.key}>
                  <Skeleton height={14} radius="sm" />
                </Table.Td>
              ))}
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    );
  }

  // Empty state
  if (data.length === 0) {
    return (
      <Stack align="center" justify="center" py="xl" gap="sm">
        {emptyIcon || (
          <IconInbox
            size={48}
            style={{
              color: 'var(--mantine-color-dimmed)',
            }}
          />
        )}
        <Text size="sm" c="dimmed" ta="center">
          {emptyMessage}
        </Text>
      </Stack>
    );
  }

  const tableContent = (
    <Table
      striped={striped}
      highlightOnHover={highlightOnHover}
      withTableBorder={false}
      withColumnBorders={false}
      verticalSpacing="sm"
      horizontalSpacing="md"
    >
      <Table.Thead
        style={
          stickyHeader
            ? {
                position: 'sticky',
                top: 0,
                backgroundColor: 'var(--mantine-color-body)',
                zIndex: 1,
              }
            : undefined
        }
      >
        <Table.Tr>
          {columns.map((col) => (
            <Table.Th
              key={col.key}
              style={{
                width: col.width,
                textAlign: col.align || 'left',
                cursor: col.sortable ? 'pointer' : undefined,
                userSelect: col.sortable ? 'none' : undefined,
              }}
              onClick={col.sortable ? () => handleSort(col.key) : undefined}
              className={col.sortable ? 'table-sortable-header' : ''}
            >
              <Group gap={4} justify={col.align === 'right' ? 'flex-end' : 'flex-start'}>
                <Text
                  size="xs"
                  fw={600}
                  tt="uppercase"
                  style={{ letterSpacing: '0.05em' }}
                >
                  {col.label}
                </Text>
                {col.sortable && renderSortIcon(col.key)}
              </Group>
            </Table.Th>
          ))}
        </Table.Tr>
      </Table.Thead>
      <Table.Tbody>
        {sortedData.map((row, rowIndex) => (
          <Table.Tr
            key={rowIndex}
            style={{
              cursor: onRowClick ? 'pointer' : undefined,
            }}
            onClick={onRowClick ? () => onRowClick(row) : undefined}
          >
            {columns.map((col) => (
              <Table.Td
                key={col.key}
                style={{ textAlign: col.align || 'left' }}
              >
                {col.render
                  ? col.render((row as Record<string, unknown>)[col.key], row)
                  : String((row as Record<string, unknown>)[col.key] ?? '')}
              </Table.Td>
            ))}
          </Table.Tr>
        ))}
      </Table.Tbody>
    </Table>
  );

  if (maxHeight || stickyHeader) {
    return (
      <ScrollArea h={maxHeight} type="auto" scrollbarSize={6}>
        {tableContent}
      </ScrollArea>
    );
  }

  return tableContent;
}

// Simple table (backwards compatible)
interface SimpleTableProps {
  header: string[];
  rows: React.ReactNode[][];
  loading?: boolean;
  emptyMessage?: string;
}

export function SimpleTable({ header, rows, loading, emptyMessage }: SimpleTableProps) {
  if (loading) {
    return (
      <Table striped highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            {header.map((h, i) => (
              <Table.Th key={i}>
                <Skeleton height={14} width="60%" radius="sm" />
              </Table.Th>
            ))}
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {Array.from({ length: 3 }).map((_, i) => (
            <Table.Tr key={i}>
              {header.map((_, j) => (
                <Table.Td key={j}>
                  <Skeleton height={14} radius="sm" />
                </Table.Td>
              ))}
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    );
  }

  if (rows.length === 0) {
    return (
      <Stack align="center" justify="center" py="xl" gap="sm">
        <IconInbox
          size={48}
          style={{
            color: 'var(--mantine-color-dimmed)',
          }}
        />
        <Text size="sm" c="dimmed" ta="center">
          {emptyMessage || 'No data available'}
        </Text>
      </Stack>
    );
  }

  return (
    <Table striped highlightOnHover>
      <Table.Thead>
        <Table.Tr>
          {header.map((h, i) => (
            <Table.Th key={i}>
              <Text size="xs" fw={600} tt="uppercase" style={{ letterSpacing: '0.05em' }}>
                {h}
              </Text>
            </Table.Th>
          ))}
        </Table.Tr>
      </Table.Thead>
      <Table.Tbody>
        {rows.map((r, i) => (
          <Table.Tr key={i}>
            {r.map((cell, j) => (
              <Table.Td key={j}>{cell}</Table.Td>
            ))}
          </Table.Tr>
        ))}
      </Table.Tbody>
    </Table>
  );
}

export default WidgetTable;
