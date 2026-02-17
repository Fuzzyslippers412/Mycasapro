import { Table, Group, Text, Badge } from "@mantine/core";

export function FinanceHoldingsTable({ holdings }: { holdings: any[] }) {
  return (
    <Table striped highlightOnHover>
      <Table.Thead>
        <Table.Tr>
          <Table.Th>Ticker</Table.Th>
          <Table.Th>Type</Table.Th>
          <Table.Th ta="right">Shares</Table.Th>
          <Table.Th ta="right">Price</Table.Th>
          <Table.Th ta="right">Value</Table.Th>
        </Table.Tr>
      </Table.Thead>
      <Table.Tbody>
        {holdings.map((h, i) => (
          <Table.Tr key={i}>
            <Table.Td><Badge variant="light">{h.ticker}</Badge></Table.Td>
            <Table.Td><Text size="sm" c="dimmed">{h.asset_type}</Text></Table.Td>
            <Table.Td ta="right">{h.shares}</Table.Td>
            <Table.Td ta="right">${h.price?.toLocaleString?.() || h.price}</Table.Td>
            <Table.Td ta="right">${h.value?.toLocaleString?.() || h.value}</Table.Td>
          </Table.Tr>
        ))}
      </Table.Tbody>
    </Table>
  );
}
