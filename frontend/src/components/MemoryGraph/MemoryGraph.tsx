"use client";

import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { getApiBaseUrl } from "@/lib/api";
import dynamic from "next/dynamic";
import {
  Card,
  Group,
  Stack,
  Text,
  Badge,
  ActionIcon,
  Tooltip,
  Paper,
  Title,
  Loader,
  Alert,
  Select,
  TextInput,
  Box,
  ScrollArea,
  Divider,
  ThemeIcon,
  SimpleGrid,
  Center,
  SegmentedControl,
  Modal,
  Button,
  Code,
} from "@mantine/core";
import {
  IconRefresh,
  IconSearch,
  IconBrain,
  IconFile,
  IconFolder,
  IconRobot,
  IconFilter,
  IconZoomIn,
  IconZoomOut,
  IconMaximize,
  IconList,
  IconTopologyRing,
  IconX,
} from "@tabler/icons-react";

// Dynamic import for force graph (SSR disabled)
const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
  loading: () => (
    <Center h={500}>
      <Loader size="lg" />
    </Center>
  ),
});

const API_URL = getApiBaseUrl();

interface GraphNode {
  id: string;
  title: string;
  type: string;
  folder: string;
  agent: string;
  modified: string;
  body_preview?: string;
  is_center?: boolean;
}

interface GraphEdge {
  source: string;
  target: string;
  type: string;
}

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  stats: {
    total_notes: number;
    total_edges: number;
    by_type: Record<string, number>;
    by_folder: Record<string, number>;
    by_agent: Record<string, number>;
  };
}

interface NoteDetail {
  id: string;
  path: string;
  folder: string;
  frontmatter: Record<string, any>;
  body: string;
  body_preview: string;
  modified: string;
}

// Color mapping for node types
const TYPE_COLORS: Record<string, string> = {
  decision: "#228be6",
  event: "#40c057",
  entity: "#fab005",
  policy: "#7950f2",
  task: "#fd7e14",
  message: "#20c997",
  telemetry: "#868e96",
  document: "#e64980",
  note: "#339af0",
  unknown: "#adb5bd",
};

// Color mapping for folders
const FOLDER_COLORS: Record<string, string> = {
  decisions: "#228be6",
  memory: "#40c057",
  entities: "#fab005",
  logs: "#868e96",
  finance: "#12b886",
  maintenance: "#fd7e14",
  contractors: "#e64980",
  projects: "#7950f2",
  documents: "#339af0",
  inbox: "#495057",
};

function NodeCard({ node, onClick }: { node: GraphNode; onClick: () => void }) {
  const color = TYPE_COLORS[node.type] || TYPE_COLORS.unknown;
  
  return (
    <Paper 
      p="xs" 
      withBorder 
      style={{ cursor: "pointer", borderLeft: `3px solid ${color}` }}
      onClick={onClick}
    >
      <Group justify="space-between" wrap="nowrap">
        <div style={{ minWidth: 0 }}>
          <Text size="sm" fw={500} truncate>{node.title}</Text>
          <Group gap={4}>
            <Badge size="xs" color={color.replace("#", "")} variant="light">
              {node.type}
            </Badge>
            <Text size="xs" c="dimmed">{node.folder}/</Text>
          </Group>
        </div>
        <Badge size="xs" variant="outline">{node.agent}</Badge>
      </Group>
    </Paper>
  );
}

function StatCard({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <Paper p="xs" withBorder>
      <Text size="xs" c="dimmed">{label}</Text>
      <Text size="lg" fw={700} c={color}>{value}</Text>
    </Paper>
  );
}

export function MemoryGraph() {
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [noteDetail, setNoteDetail] = useState<NoteDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [filterType, setFilterType] = useState<string | null>(null);
  const [filterFolder, setFilterFolder] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [viewMode, setViewMode] = useState<"list" | "graph">("graph");
  const graphRef = useRef<any>(null);
  const graphContainerRef = useRef<HTMLDivElement | null>(null);
  const [graphSize, setGraphSize] = useState({ width: 800, height: 500 });
  
  const fetchGraph = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/secondbrain/graph?include_body=true`);
      if (res.ok) {
        const data = await res.json();
        setGraphData(data);
        setError(null);
      } else {
        setError("Failed to fetch knowledge graph");
      }
    } catch (e) {
      setError("Backend offline");
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchNoteDetail = useCallback(async (noteId: string) => {
    setDetailLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/secondbrain/notes/${noteId}`);
      if (res.ok) {
        const data = await res.json();
        setNoteDetail(data);
      }
    } catch (e) {
      console.error("Failed to fetch note detail:", e);
    } finally {
      setDetailLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchGraph();
  }, [fetchGraph]);

  useEffect(() => {
    const node = graphContainerRef.current;
    if (!node) return;
    const updateSize = () => {
      const width = node.clientWidth || 800;
      const height = Math.max(420, Math.min(560, Math.round(width * 0.6)));
      setGraphSize({ width, height });
    };
    updateSize();
    if (typeof ResizeObserver !== "undefined") {
      const observer = new ResizeObserver(updateSize);
      observer.observe(node);
      return () => observer.disconnect();
    }
    window.addEventListener("resize", updateSize);
    return () => window.removeEventListener("resize", updateSize);
  }, []);

  // Transform data for force graph
  const forceGraphData = useMemo(() => {
    if (!graphData) return { nodes: [], links: [] };
    
    let nodes = graphData.nodes;
    
    // Apply filters
    if (filterType) {
      nodes = nodes.filter(n => n.type === filterType);
    }
    if (filterFolder) {
      nodes = nodes.filter(n => n.folder === filterFolder);
    }
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      nodes = nodes.filter(n => 
        n.title.toLowerCase().includes(q) || 
        n.id.toLowerCase().includes(q)
      );
    }
    
    const nodeIds = new Set(nodes.map(n => n.id));
    
    // Add color to nodes
    const coloredNodes = nodes.map(n => ({
      ...n,
      color: TYPE_COLORS[n.type] || TYPE_COLORS.unknown,
      val: n.type === "entity" ? 3 : 2, // Entities are bigger
    }));
    
    // Filter edges to only include visible nodes
    const links = graphData.edges
      .filter(e => nodeIds.has(e.source as string) && nodeIds.has(e.target as string))
      .map(e => ({
        ...e,
        color: "#ccc",
      }));
    
    return { nodes: coloredNodes, links };
  }, [graphData, filterType, filterFolder, searchQuery]);

  // Filter nodes for list view
  const filteredNodes = useMemo(() => {
    if (!graphData) return [];
    
    let nodes = graphData.nodes;
    
    if (filterType) {
      nodes = nodes.filter(n => n.type === filterType);
    }
    if (filterFolder) {
      nodes = nodes.filter(n => n.folder === filterFolder);
    }
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      nodes = nodes.filter(n => 
        n.title.toLowerCase().includes(q) || 
        n.id.toLowerCase().includes(q)
      );
    }
    
    return nodes;
  }, [graphData, filterType, filterFolder, searchQuery]);

  const handleNodeClick = useCallback((node: any) => {
    setSelectedNode(node);
    fetchNoteDetail(node.id);
    
    // Center on clicked node
    if (graphRef.current) {
      graphRef.current.centerAt(node.x, node.y, 500);
      graphRef.current.zoom(2, 500);
    }
  }, [fetchNoteDetail]);

  const handleZoomIn = useCallback(() => {
    if (graphRef.current) {
      graphRef.current.zoom(graphRef.current.zoom() * 1.5, 300);
    }
  }, []);

  const handleZoomOut = useCallback(() => {
    if (graphRef.current) {
      graphRef.current.zoom(graphRef.current.zoom() / 1.5, 300);
    }
  }, []);

  const handleResetView = useCallback(() => {
    if (graphRef.current) {
      graphRef.current.zoomToFit(500, 50);
    }
  }, []);

  if (loading && !graphData) {
    return (
      <Center py="xl">
        <Stack align="center" gap="md">
          <Loader size="lg" />
          <Text c="dimmed">Loading knowledge graph...</Text>
        </Stack>
      </Center>
    );
  }

  if (error && !graphData) {
    return (
      <Alert color="red" icon={<IconBrain />} title="Error">
        {error}
      </Alert>
    );
  }

  if (!graphData) return null;

  const stats = graphData.stats ?? {
    total_notes: 0,
    total_edges: 0,
    by_type: {} as Record<string, number>,
    by_folder: {} as Record<string, number>,
    by_agent: {} as Record<string, number>,
  };
  const types = Object.keys(stats.by_type || {});
  const folders = Object.keys(stats.by_folder || {});

  return (
    <Stack gap="md" className="memory-page">
      {/* Header */}
      <Group justify="space-between">
        <Group gap="xs">
          <ThemeIcon size="lg" variant="light" color="violet">
            <IconBrain size={20} />
          </ThemeIcon>
          <div>
            <Text fw={600}>SecondBrain Knowledge Graph</Text>
            <Text size="xs" c="dimmed">
              {stats.total_notes} notes, {stats.total_edges} connections
            </Text>
          </div>
        </Group>
        <Group gap="xs">
          <SegmentedControl
            size="xs"
            value={viewMode}
            onChange={(v) => setViewMode(v as "list" | "graph")}
            data={[
              { value: "graph", label: <IconTopologyRing size={16} /> },
              { value: "list", label: <IconList size={16} /> },
            ]}
          />
          <Tooltip label="Refresh">
            <ActionIcon variant="light" onClick={fetchGraph} loading={loading}>
              <IconRefresh size={18} />
            </ActionIcon>
          </Tooltip>
        </Group>
      </Group>

      {/* Stats */}
      <SimpleGrid cols={{ base: 2, sm: 4 }} className="memory-stats">
        <StatCard label="Total Notes" value={stats.total_notes} color="violet" />
        <StatCard label="Connections" value={stats.total_edges} color="blue" />
        <StatCard label="Types" value={types.length} color="green" />
        <StatCard label="Folders" value={folders.length} color="orange" />
      </SimpleGrid>

      {/* Filters */}
      <Card withBorder p="sm" className="memory-filters">
        <Group gap="sm">
          <TextInput
            placeholder="Search notes..."
            leftSection={<IconSearch size={16} />}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.currentTarget.value)}
            style={{ flex: 1 }}
          />
          <Select
            placeholder="Type"
            data={[
              { value: "", label: "All types" },
              ...types.map(t => ({ value: t, label: `${t} (${stats.by_type[t]})` }))
            ]}
            value={filterType || ""}
            onChange={(v) => setFilterType(v || null)}
            clearable
            leftSection={<IconFilter size={16} />}
            w={160}
          />
          <Select
            placeholder="Folder"
            data={[
              { value: "", label: "All folders" },
              ...folders.map(f => ({ value: f, label: `${f}/ (${stats.by_folder[f]})` }))
            ]}
            value={filterFolder || ""}
            onChange={(v) => setFilterFolder(v || null)}
            clearable
            leftSection={<IconFolder size={16} />}
            w={160}
          />
        </Group>
      </Card>

      {/* Main content */}
      {viewMode === "graph" ? (
        <Card withBorder p={0} style={{ position: "relative", overflow: "hidden" }} className="memory-graph-card">
          {/* Graph controls */}
          <Group
            gap="xs"
            className="memory-graph-controls"
            style={{
              position: "absolute",
              top: 10,
              right: 10,
              zIndex: 10,
              padding: 4,
            }}
          >
            <Tooltip label="Zoom In">
              <ActionIcon variant="light" size="sm" onClick={handleZoomIn}>
                <IconZoomIn size={16} />
              </ActionIcon>
            </Tooltip>
            <Tooltip label="Zoom Out">
              <ActionIcon variant="light" size="sm" onClick={handleZoomOut}>
                <IconZoomOut size={16} />
              </ActionIcon>
            </Tooltip>
            <Tooltip label="Fit View">
              <ActionIcon variant="light" size="sm" onClick={handleResetView}>
                <IconMaximize size={16} />
              </ActionIcon>
            </Tooltip>
          </Group>
          
          <Box ref={graphContainerRef} className="memory-graph-canvas">
            <ForceGraph2D
              ref={graphRef}
              graphData={forceGraphData}
              width={graphSize.width}
              height={graphSize.height}
              nodeLabel={(node: any) => `${node.title}\n(${node.type})`}
              nodeColor={(node: any) => node.color}
              nodeRelSize={6}
              nodeVal={(node: any) => node.val || 2}
              linkColor={() => "#e0e0e0"}
              linkWidth={1}
              linkDirectionalParticles={1}
              linkDirectionalParticleWidth={2}
              onNodeClick={handleNodeClick}
              onBackgroundClick={() => {
                setSelectedNode(null);
                setNoteDetail(null);
              }}
              cooldownTicks={100}
              onEngineStop={() => {
                if (graphRef.current) {
                  graphRef.current.zoomToFit(400, 50);
                }
              }}
              nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
                const label = node.title.length > 20 ? node.title.slice(0, 20) + "..." : node.title;
                const fontSize = 12 / globalScale;
                ctx.font = `${fontSize}px Sans-Serif`;
                
                // Draw node circle
                const isSelected = selectedNode?.id === node.id;
                ctx.beginPath();
                ctx.arc(node.x, node.y, node.val * 2, 0, 2 * Math.PI);
                ctx.fillStyle = node.color;
                ctx.fill();
                
                if (isSelected) {
                  ctx.strokeStyle = "#000";
                  ctx.lineWidth = 2 / globalScale;
                  ctx.stroke();
                }
                
                // Draw label if zoomed in enough
                if (globalScale > 0.7) {
                  ctx.textAlign = "center";
                  ctx.textBaseline = "middle";
                  ctx.fillStyle = "#333";
                  ctx.fillText(label, node.x, node.y + node.val * 2 + fontSize);
                }
              }}
            />
          </Box>
          
          {/* Legend */}
          <Group
            gap="xs"
            className="memory-graph-legend"
            style={{
              position: "absolute",
              bottom: 10,
              left: 10,
              padding: 8,
            }}
          >
            {Object.entries(TYPE_COLORS).slice(0, 6).map(([type, color]) => (
              <Group key={type} gap={4}>
                <Box w={10} h={10} style={{ backgroundColor: color, borderRadius: "50%" }} />
                <Text size="xs">{type}</Text>
              </Group>
            ))}
          </Group>
        </Card>
      ) : (
        <SimpleGrid cols={{ base: 1, md: 2 }}>
          {/* Notes list */}
          <Card withBorder p="sm">
            <Title order={6} mb="sm">
              Notes ({filteredNodes.length})
            </Title>
            <ScrollArea h={400}>
              <Stack gap="xs">
                {filteredNodes.length === 0 ? (
                  <Text c="dimmed" ta="center" py="md">No notes match filters</Text>
                ) : (
                  filteredNodes.map(node => (
                    <NodeCard 
                      key={node.id} 
                      node={node} 
                      onClick={() => {
                        setSelectedNode(node);
                        fetchNoteDetail(node.id);
                      }}
                    />
                  ))
                )}
              </Stack>
            </ScrollArea>
          </Card>

          {/* Distribution charts */}
          <Card withBorder p="sm">
            <Title order={6} mb="sm">Distribution</Title>
            
            <Text size="xs" fw={600} mb="xs">By Type</Text>
            <Stack gap={4} mb="md">
              {Object.entries(stats.by_type).map(([type, count]) => (
                <Group key={type} justify="space-between">
                  <Group gap="xs">
                    <Box 
                      w={12} 
                      h={12} 
                      style={{ 
                        backgroundColor: TYPE_COLORS[type] || TYPE_COLORS.unknown,
                        borderRadius: 2,
                      }} 
                    />
                    <Text size="sm">{type}</Text>
                  </Group>
                  <Badge size="sm" variant="light">{count}</Badge>
                </Group>
              ))}
            </Stack>

            <Divider my="sm" />

            <Text size="xs" fw={600} mb="xs">By Folder</Text>
            <Stack gap={4} mb="md">
              {Object.entries(stats.by_folder).map(([folder, count]) => (
                <Group key={folder} justify="space-between">
                  <Group gap="xs">
                    <IconFolder size={14} color={FOLDER_COLORS[folder] || "#868e96"} />
                    <Text size="sm">{folder}/</Text>
                  </Group>
                  <Badge size="sm" variant="light">{count}</Badge>
                </Group>
              ))}
            </Stack>

            <Divider my="sm" />

            <Text size="xs" fw={600} mb="xs">By Agent</Text>
            <Stack gap={4}>
              {Object.entries(stats.by_agent).map(([agent, count]) => (
                <Group key={agent} justify="space-between">
                  <Group gap="xs">
                    <IconRobot size={14} />
                    <Text size="sm">{agent}</Text>
                  </Group>
                  <Badge size="sm" variant="light">{count}</Badge>
                </Group>
              ))}
            </Stack>
          </Card>
        </SimpleGrid>
      )}

      {/* Note detail modal */}
      <Modal
        opened={!!selectedNode}
        onClose={() => {
          setSelectedNode(null);
          setNoteDetail(null);
        }}
        title={
          <Group gap="xs">
            <Badge color={TYPE_COLORS[selectedNode?.type || "unknown"]?.replace("#", "") || "gray"}>
              {selectedNode?.type}
            </Badge>
            <Text fw={600}>{selectedNode?.title}</Text>
          </Group>
        }
        size="lg"
      >
        {detailLoading ? (
          <Center py="xl">
            <Loader />
          </Center>
        ) : noteDetail ? (
          <Stack gap="md">
            <SimpleGrid cols={2}>
              <div>
                <Text size="xs" c="dimmed">ID</Text>
                <Code>{noteDetail.id}</Code>
              </div>
              <div>
                <Text size="xs" c="dimmed">Folder</Text>
                <Text size="sm">{noteDetail.folder}/</Text>
              </div>
              <div>
                <Text size="xs" c="dimmed">Agent</Text>
                <Badge size="sm" variant="light">
                  {noteDetail.frontmatter?.agent || "unknown"}
                </Badge>
              </div>
              <div>
                <Text size="xs" c="dimmed">Modified</Text>
                <Text size="sm">{new Date(noteDetail.modified).toLocaleString()}</Text>
              </div>
            </SimpleGrid>
            
            {noteDetail.frontmatter?.tags && (
              <div>
                <Text size="xs" c="dimmed" mb={4}>Tags</Text>
                <Group gap={4}>
                  {(Array.isArray(noteDetail.frontmatter.tags) 
                    ? noteDetail.frontmatter.tags 
                    : [noteDetail.frontmatter.tags]
                  ).map((tag: string) => (
                    <Badge key={tag} size="xs" variant="outline">{tag}</Badge>
                  ))}
                </Group>
              </div>
            )}
            
            <Divider />
            
            <div>
              <Text size="xs" c="dimmed" mb={4}>Content</Text>
              <Paper p="sm" bg="gray.0" style={{ maxHeight: 300, overflow: "auto" }}>
                <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                  {noteDetail.body}
                </Text>
              </Paper>
            </div>
          </Stack>
        ) : (
          <Text c="dimmed">Failed to load note details</Text>
        )}
      </Modal>
    </Stack>
  );
}
