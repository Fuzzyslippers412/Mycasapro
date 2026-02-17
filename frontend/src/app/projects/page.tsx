"use client";
import { Shell } from "@/components/layout/Shell";
import { apiFetch } from "@/lib/api";
import { Page } from "@/components/layout/Page";
import { useEffect, useMemo, useState } from "react";
import { 
  Card, Text, Stack, Box, Button, Group, Badge, 
  Modal, TextInput, Textarea, Progress, Paper, SimpleGrid, Alert, Skeleton
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { IconPlus, IconFolders, IconAlertTriangle, IconTimeline } from "@tabler/icons-react";

interface Project {
  id: number;
  name: string;
  description?: string;
  status: "planning" | "in_progress" | "on_hold" | "completed";
  budget?: number;
  spent?: number;
  target_end_date?: string | null;
}

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [opened, { open, close }] = useDisclosure(false);
  const [newProject, setNewProject] = useState({ name: "", description: "", budget: 0 });

  const fetchProjects = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<any>("/api/projects?limit=50");
      setProjects(data.projects || []);
    } catch (e) {
      setError("Unable to load projects right now.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const handleAddProject = async () => {
    if (!newProject.name.trim()) {
      notifications.show({ title: "Error", message: "Project name is required", color: "red" });
      return;
    }

    try {
      await apiFetch("/api/projects", {
        method: "POST",
        body: JSON.stringify({
          name: newProject.name,
          description: newProject.description || undefined,
          budget: newProject.budget || undefined,
          status: "planning",
        }),
      });

      notifications.show({
        title: "Project Created",
        message: `"${newProject.name}" added to your projects`,
        color: "green",
      });
      setNewProject({ name: "", description: "", budget: 0 });
      close();
      fetchProjects();
    } catch (e) {
      notifications.show({ title: "Error", message: "Unable to create project", color: "red" });
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed": return "green";
      case "in_progress": return "blue";
      case "on_hold": return "yellow";
      default: return "gray";
    }
  };

  const summary = useMemo(() => {
    const total = projects.length;
    const inProgress = projects.filter((p) => p.status === "in_progress").length;
    const completed = projects.filter((p) => p.status === "completed").length;
    const totalBudget = projects.reduce((sum, p) => sum + (p.budget || 0), 0);
    return { total, inProgress, completed, totalBudget };
  }, [projects]);

  const getProgress = (project: Project) => {
    if (project.status === "completed") return 100;
    if (project.budget && project.spent) {
      return Math.min(100, Math.round((project.spent / project.budget) * 100));
    }
    return project.status === "in_progress" ? 45 : 10;
  };

  return (
    <Shell>
      <Page
        title="Projects"
        subtitle="Track renovation, improvement, and maintenance projects."
        actions={<Button leftSection={<IconPlus size={16} />} onClick={open}>New Project</Button>}
      >
      <Stack gap="md">
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }}>
          <Card withBorder radius="lg">
            <Text size="xs" c="dimmed" tt="uppercase" fw={600}>Total projects</Text>
            <Text size="xl" fw={700} mt={4}>{summary.total}</Text>
            <Text size="xs" c="dimmed">All statuses</Text>
          </Card>
          <Card withBorder radius="lg">
            <Text size="xs" c="dimmed" tt="uppercase" fw={600}>In progress</Text>
            <Text size="xl" fw={700} mt={4}>{summary.inProgress}</Text>
            <Text size="xs" c="dimmed">Active workstreams</Text>
          </Card>
          <Card withBorder radius="lg">
            <Text size="xs" c="dimmed" tt="uppercase" fw={600}>Completed</Text>
            <Text size="xl" fw={700} mt={4}>{summary.completed}</Text>
            <Text size="xs" c="dimmed">Finished work</Text>
          </Card>
          <Card withBorder radius="lg">
            <Text size="xs" c="dimmed" tt="uppercase" fw={600}>Total budget</Text>
            <Text size="xl" fw={700} mt={4}>
              {summary.totalBudget > 0 ? `$${summary.totalBudget.toLocaleString()}` : "—"}
            </Text>
            <Text size="xs" c="dimmed">Across all projects</Text>
          </Card>
        </SimpleGrid>

        {loading && (
          <Stack gap="sm">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} height={90} radius="md" />
            ))}
          </Stack>
        )}

        {error && (
          <Alert color="red" icon={<IconAlertTriangle size={16} />} title="Projects unavailable">
            {error}
          </Alert>
        )}

        {!loading && !error && projects.length === 0 ? (
          <Card withBorder p="xl" radius="md">
            <Box py="xl" style={{ textAlign: "center" }}>
              <IconFolders size={48} stroke={1.5} style={{ color: "var(--mantine-color-dimmed)" }} />
              <Text size="lg" fw={500} mt="md">No projects</Text>
              <Text c="dimmed" size="sm">Create a project to track home improvements</Text>
              <Button mt="md" leftSection={<IconPlus size={16} />} onClick={open}>
                Create project
              </Button>
            </Box>
          </Card>
        ) : (
          <Stack gap="sm">
            {projects.map(project => (
              <Paper key={project.id} withBorder p="md" radius="md">
                <Group justify="space-between" mb="sm" wrap="nowrap">
                  <div>
                    <Group gap="xs">
                      <Text fw={600}>{project.name}</Text>
                      <Badge size="sm" color={getStatusColor(project.status)}>{project.status}</Badge>
                    </Group>
                    {project.description && <Text size="sm" c="dimmed">{project.description}</Text>}
                    {project.target_end_date && (
                      <Group gap={6} mt={4}>
                        <IconTimeline size={14} style={{ opacity: 0.6 }} />
                        <Text size="xs" c="dimmed">
                          Target: {new Date(project.target_end_date).toLocaleDateString()}
                        </Text>
                      </Group>
                    )}
                  </div>
                  {project.budget && (
                    <Text size="sm" c="dimmed">
                      ${project.spent?.toLocaleString() || 0} / ${project.budget.toLocaleString()}
                    </Text>
                  )}
                </Group>
                <Progress 
                  value={getProgress(project)} 
                  size="sm"
                  color={project.status === "completed" ? "green" : "blue"}
                />
              </Paper>
            ))}
          </Stack>
        )}
      </Stack>

      <Modal opened={opened} onClose={close} title="New Project">
        <Stack gap="md">
          <TextInput
            label="Project Name"
            placeholder="e.g., Kitchen Renovation"
            required
            value={newProject.name}
            onChange={(e) => setNewProject({ ...newProject, name: e.target.value })}
          />
          <Textarea
            label="Description"
            placeholder="What's the project about?"
            value={newProject.description}
            onChange={(e) => setNewProject({ ...newProject, description: e.target.value })}
          />
          <TextInput
            label="Budget"
            type="number"
            placeholder="0"
            leftSection="$"
            value={newProject.budget || ""}
            onChange={(e) => setNewProject({ ...newProject, budget: parseFloat(e.target.value) || 0 })}
          />
          <Group justify="flex-end">
            <Button variant="subtle" onClick={close}>Cancel</Button>
            <Button onClick={handleAddProject}>Create Project</Button>
          </Group>
        </Stack>
      </Modal>
          </Page>
    </Shell>
  );
}
