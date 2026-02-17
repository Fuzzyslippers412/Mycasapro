"use client";

import { useState, useEffect, useCallback } from "react";
import { getApiBaseUrl } from "@/lib/api";
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
  Button,
  Modal,
  TextInput,
  Textarea,
  Select,
  NumberInput,
  Switch,
  SimpleGrid,
  Center,
  ThemeIcon,
  Code,
  Divider,
  ScrollArea,
  Collapse,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import {
  IconClock,
  IconPlayerPlay,
  IconPlayerStop,
  IconPlus,
  IconRefresh,
  IconTrash,
  IconPencil,
  IconCalendarEvent,
  IconCheck,
  IconX,
  IconRobot,
  IconChevronDown,
  IconChevronUp,
  IconTemplate,
} from "@tabler/icons-react";

const API_URL = getApiBaseUrl();

interface ScheduledJob {
  id: string;
  name: string;
  description: string;
  agent: string;
  task: string;
  frequency: string;
  next_run: string;
  enabled: boolean;
  created_at: string;
  last_run: string | null;
  last_result: string | null;
  last_status: string | null;
  run_count: number;
  failure_count: number;
  hour: number;
  minute: number;
  day_of_week: number;
  day_of_month: number;
}

interface JobTemplate {
  id: string;
  name: string;
  description: string;
  agent: string;
  task: string;
  frequency: string;
}

interface SchedulerStatus {
  running: boolean;
  total_jobs: number;
  enabled_jobs: number;
  due_jobs: number;
  next_job: string | null;
  total_runs: number;
  recent_failures: number;
}

const FREQUENCY_OPTIONS = [
  { value: "once", label: "Once" },
  { value: "hourly", label: "Hourly" },
  { value: "daily", label: "Daily" },
  { value: "weekly", label: "Weekly" },
  { value: "monthly", label: "Monthly" },
];

const AGENT_OPTIONS = [
  { value: "manager", label: "Manager" },
  { value: "finance", label: "Finance" },
  { value: "maintenance", label: "Maintenance" },
  { value: "security", label: "Security" },
  { value: "contractors", label: "Contractors" },
  { value: "janitor", label: "Janitor" },
];

const DAY_OPTIONS = [
  { value: "0", label: "Monday" },
  { value: "1", label: "Tuesday" },
  { value: "2", label: "Wednesday" },
  { value: "3", label: "Thursday" },
  { value: "4", label: "Friday" },
  { value: "5", label: "Saturday" },
  { value: "6", label: "Sunday" },
];

function formatDateTime(isoString: string | null): string {
  if (!isoString) return "Never";
  return new Date(isoString).toLocaleString();
}

function formatSchedule(job: ScheduledJob): string {
  switch (job.frequency) {
    case "once":
      return `Once at ${formatDateTime(job.next_run)}`;
    case "hourly":
      return `Every hour at :${String(job.minute).padStart(2, "0")}`;
    case "daily":
      return `Daily at ${String(job.hour).padStart(2, "0")}:${String(job.minute).padStart(2, "0")}`;
    case "weekly":
      const day = DAY_OPTIONS.find(d => d.value === String(job.day_of_week))?.label || "Monday";
      return `Every ${day} at ${String(job.hour).padStart(2, "0")}:${String(job.minute).padStart(2, "0")}`;
    case "monthly":
      return `Day ${job.day_of_month} of each month at ${String(job.hour).padStart(2, "0")}:${String(job.minute).padStart(2, "0")}`;
    default:
      return job.frequency;
  }
}

function JobCard({
  job,
  onEdit,
  onDelete,
  onToggle,
  onRunNow,
}: {
  job: ScheduledJob;
  onEdit: () => void;
  onDelete: () => void;
  onToggle: () => void;
  onRunNow: () => void;
}) {
  const [expanded, { toggle }] = useDisclosure(false);
  
  const statusColor = job.last_status === "completed" ? "green" : 
                      job.last_status === "failed" ? "red" : "gray";

  return (
    <Card withBorder p="sm">
      <Group justify="space-between" mb="xs">
        <Group gap="sm">
          <ThemeIcon 
            size="md" 
            variant="light" 
            color={job.enabled ? "blue" : "gray"}
          >
            <IconCalendarEvent size={16} />
          </ThemeIcon>
          <div>
            <Group gap="xs">
              <Text fw={600}>{job.name}</Text>
              {!job.enabled && <Badge size="xs" color="gray">Disabled</Badge>}
            </Group>
            <Text size="xs" c="dimmed">{formatSchedule(job)}</Text>
          </div>
        </Group>
        
        <Group gap="xs">
          <Badge size="sm" variant="light">{job.agent}</Badge>
          <Tooltip label={expanded ? "Collapse" : "Expand"}>
            <ActionIcon variant="subtle" onClick={toggle}>
              {expanded ? <IconChevronUp size={16} /> : <IconChevronDown size={16} />}
            </ActionIcon>
          </Tooltip>
        </Group>
      </Group>

      <Collapse in={expanded}>
        <Stack gap="xs" mt="sm">
          <Divider />
          
          <Text size="sm" c="dimmed">{job.description || "No description"}</Text>
          
          <Paper p="xs" bg="gray.0">
            <Text size="xs" fw={500} mb={4}>Task:</Text>
            <Text size="sm">{job.task}</Text>
          </Paper>

          <SimpleGrid cols={3}>
            <div>
              <Text size="xs" c="dimmed">Next Run</Text>
              <Text size="sm">{formatDateTime(job.next_run)}</Text>
            </div>
            <div>
              <Text size="xs" c="dimmed">Last Run</Text>
              <Text size="sm">{formatDateTime(job.last_run)}</Text>
            </div>
            <div>
              <Text size="xs" c="dimmed">Stats</Text>
              <Group gap={4}>
                <Badge size="xs" color="green">{job.run_count} runs</Badge>
                {job.failure_count > 0 && (
                  <Badge size="xs" color="red">{job.failure_count} failed</Badge>
                )}
              </Group>
            </div>
          </SimpleGrid>

          {job.last_result && (
            <Paper p="xs" bg="gray.0">
              <Text size="xs" fw={500} mb={4}>
                Last Result 
                <Badge size="xs" ml={4} color={statusColor}>{job.last_status}</Badge>
              </Text>
              <Code block style={{ maxHeight: 100, overflow: "auto" }}>
                {job.last_result}
              </Code>
            </Paper>
          )}

          <Group gap="xs">
            <Switch
              size="xs"
              checked={job.enabled}
              onChange={onToggle}
              label={job.enabled ? "Enabled" : "Disabled"}
            />
            <Button size="xs" variant="light" onClick={onRunNow} leftSection={<IconPlayerPlay size={14} />}>
              Run Now
            </Button>
            <Button size="xs" variant="subtle" onClick={onEdit} leftSection={<IconPencil size={14} />}>
              Edit
            </Button>
            <Button size="xs" variant="subtle" color="red" onClick={onDelete} leftSection={<IconTrash size={14} />}>
              Delete
            </Button>
          </Group>
        </Stack>
      </Collapse>
    </Card>
  );
}

export function SchedulerManager() {
  const [status, setStatus] = useState<SchedulerStatus | null>(null);
  const [jobs, setJobs] = useState<ScheduledJob[]>([]);
  const [templates, setTemplates] = useState<JobTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [createModalOpen, { open: openCreateModal, close: closeCreateModal }] = useDisclosure(false);
  const [templateModalOpen, { open: openTemplateModal, close: closeTemplateModal }] = useDisclosure(false);
  const [editingJob, setEditingJob] = useState<ScheduledJob | null>(null);
  
  // Form state
  const [formName, setFormName] = useState("");
  const [formDescription, setFormDescription] = useState("");
  const [formAgent, setFormAgent] = useState("");
  const [formTask, setFormTask] = useState("");
  const [formFrequency, setFormFrequency] = useState("daily");
  const [formHour, setFormHour] = useState(9);
  const [formMinute, setFormMinute] = useState(0);
  const [formDayOfWeek, setFormDayOfWeek] = useState("0");
  const [formDayOfMonth, setFormDayOfMonth] = useState(1);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [statusRes, jobsRes, templatesRes] = await Promise.all([
        fetch(`${API_URL}/api/scheduler/status`),
        fetch(`${API_URL}/api/scheduler/jobs?include_disabled=true`),
        fetch(`${API_URL}/api/scheduler/templates`),
      ]);
      
      if (statusRes.ok) setStatus(await statusRes.json());
      if (jobsRes.ok) setJobs((await jobsRes.json()).jobs);
      if (templatesRes.ok) setTemplates((await templatesRes.json()).templates);
      
      setError(null);
    } catch (e) {
      setError("Backend offline");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const resetForm = () => {
    setFormName("");
    setFormDescription("");
    setFormAgent("");
    setFormTask("");
    setFormFrequency("daily");
    setFormHour(9);
    setFormMinute(0);
    setFormDayOfWeek("0");
    setFormDayOfMonth(1);
    setEditingJob(null);
  };

  const handleCreateJob = async () => {
    try {
      const payload = {
        name: formName,
        description: formDescription,
        agent: formAgent,
        task: formTask,
        frequency: formFrequency,
        hour: formHour,
        minute: formMinute,
        day_of_week: parseInt(formDayOfWeek),
        day_of_month: formDayOfMonth,
      };
      
      const method = editingJob ? "PUT" : "POST";
      const url = editingJob 
        ? `${API_URL}/api/scheduler/jobs/${editingJob.id}`
        : `${API_URL}/api/scheduler/jobs`;
      
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      
      if (res.ok) {
        closeCreateModal();
        resetForm();
        fetchAll();
      } else {
        const data = await res.json();
        setError(data.detail || "Failed to save job");
      }
    } catch (e) {
      setError("Failed to save job");
    }
  };

  const handleEditJob = (job: ScheduledJob) => {
    setEditingJob(job);
    setFormName(job.name);
    setFormDescription(job.description);
    setFormAgent(job.agent);
    setFormTask(job.task);
    setFormFrequency(job.frequency);
    setFormHour(job.hour);
    setFormMinute(job.minute);
    setFormDayOfWeek(String(job.day_of_week));
    setFormDayOfMonth(job.day_of_month);
    openCreateModal();
  };

  const handleDeleteJob = async (jobId: string) => {
    if (!confirm("Delete this job?")) return;
    
    try {
      await fetch(`${API_URL}/api/scheduler/jobs/${jobId}`, { method: "DELETE" });
      fetchAll();
    } catch (e) {
      setError("Failed to delete job");
    }
  };

  const handleToggleJob = async (job: ScheduledJob) => {
    try {
      const endpoint = job.enabled ? "disable" : "enable";
      await fetch(`${API_URL}/api/scheduler/jobs/${job.id}/${endpoint}`, { method: "POST" });
      fetchAll();
    } catch (e) {
      setError("Failed to toggle job");
    }
  };

  const handleRunNow = async (jobId: string) => {
    try {
      await fetch(`${API_URL}/api/scheduler/jobs/${jobId}/run`, { method: "POST" });
      fetchAll();
    } catch (e) {
      setError("Failed to run job");
    }
  };

  const handleCreateFromTemplate = async (templateId: string) => {
    try {
      const res = await fetch(`${API_URL}/api/scheduler/templates/${templateId}/create`, { 
        method: "POST" 
      });
      if (res.ok) {
        closeTemplateModal();
        fetchAll();
      }
    } catch (e) {
      setError("Failed to create from template");
    }
  };

  if (loading && !status) {
    return (
      <Center py="xl">
        <Loader />
      </Center>
    );
  }

  return (
    <Stack gap="md">
      {/* Header */}
      <Group justify="space-between">
        <Group gap="xs">
          <ThemeIcon size="lg" variant="light" color="blue">
            <IconClock size={20} />
          </ThemeIcon>
          <div>
            <Text fw={600}>Agent Scheduler</Text>
            <Text size="xs" c="dimmed">
              {status?.enabled_jobs || 0} active jobs, {status?.total_runs || 0} total runs
            </Text>
          </div>
        </Group>
        <Group gap="xs">
          <Button 
            size="xs" 
            variant="light" 
            leftSection={<IconTemplate size={16} />}
            onClick={openTemplateModal}
          >
            Templates
          </Button>
          <Button 
            size="xs" 
            leftSection={<IconPlus size={16} />}
            onClick={() => { resetForm(); openCreateModal(); }}
          >
            New Job
          </Button>
          <ActionIcon variant="light" onClick={fetchAll}>
            <IconRefresh size={18} />
          </ActionIcon>
        </Group>
      </Group>

      {error && (
        <Alert color="red" onClose={() => setError(null)} withCloseButton>
          {error}
        </Alert>
      )}

      {/* Status cards */}
      <SimpleGrid cols={{ base: 2, sm: 4 }}>
        <Paper p="xs" withBorder>
          <Text size="xs" c="dimmed">Active Jobs</Text>
          <Text size="lg" fw={700} c="blue">{status?.enabled_jobs || 0}</Text>
        </Paper>
        <Paper p="xs" withBorder>
          <Text size="xs" c="dimmed">Due Now</Text>
          <Text size="lg" fw={700} c={status?.due_jobs ? "orange" : "gray"}>
            {status?.due_jobs || 0}
          </Text>
        </Paper>
        <Paper p="xs" withBorder>
          <Text size="xs" c="dimmed">Total Runs</Text>
          <Text size="lg" fw={700} c="green">{status?.total_runs || 0}</Text>
        </Paper>
        <Paper p="xs" withBorder>
          <Text size="xs" c="dimmed">Recent Failures</Text>
          <Text size="lg" fw={700} c={status?.recent_failures ? "red" : "gray"}>
            {status?.recent_failures || 0}
          </Text>
        </Paper>
      </SimpleGrid>

      {/* Jobs list */}
      <Card withBorder p="sm">
        <Title order={6} mb="sm">Scheduled Jobs</Title>
        
        {jobs.length === 0 ? (
          <Center py="xl">
            <Stack align="center" gap="xs">
              <IconCalendarEvent size={48} stroke={1} color="gray" />
              <Text c="dimmed">No scheduled jobs</Text>
              <Button size="xs" onClick={openTemplateModal}>Create from Template</Button>
            </Stack>
          </Center>
        ) : (
          <Stack gap="sm">
            {jobs.map(job => (
              <JobCard
                key={job.id}
                job={job}
                onEdit={() => handleEditJob(job)}
                onDelete={() => handleDeleteJob(job.id)}
                onToggle={() => handleToggleJob(job)}
                onRunNow={() => handleRunNow(job.id)}
              />
            ))}
          </Stack>
        )}
      </Card>

      {/* Create/Edit Modal */}
      <Modal
        opened={createModalOpen}
        onClose={() => { closeCreateModal(); resetForm(); }}
        title={editingJob ? "Edit Job" : "Create Scheduled Job"}
        size="lg"
      >
        <Stack gap="sm">
          <TextInput
            label="Name"
            placeholder="Daily Finance Review"
            value={formName}
            onChange={e => setFormName(e.currentTarget.value)}
            required
          />
          
          <Textarea
            label="Description"
            placeholder="What this job does..."
            value={formDescription}
            onChange={e => setFormDescription(e.currentTarget.value)}
          />
          
          <Select
            label="Agent"
            placeholder="Select agent"
            data={AGENT_OPTIONS}
            value={formAgent}
            onChange={v => setFormAgent(v || "")}
            required
          />
          
          <Textarea
            label="Task"
            placeholder="The prompt/task for the agent..."
            value={formTask}
            onChange={e => setFormTask(e.currentTarget.value)}
            required
            minRows={3}
          />
          
          <Select
            label="Frequency"
            data={FREQUENCY_OPTIONS}
            value={formFrequency}
            onChange={v => setFormFrequency(v || "daily")}
          />
          
          <SimpleGrid cols={2}>
            <NumberInput
              label="Hour"
              min={0}
              max={23}
              value={formHour}
              onChange={v => setFormHour(Number(v))}
            />
            <NumberInput
              label="Minute"
              min={0}
              max={59}
              value={formMinute}
              onChange={v => setFormMinute(Number(v))}
            />
          </SimpleGrid>
          
          {formFrequency === "weekly" && (
            <Select
              label="Day of Week"
              data={DAY_OPTIONS}
              value={formDayOfWeek}
              onChange={v => setFormDayOfWeek(v || "0")}
            />
          )}
          
          {formFrequency === "monthly" && (
            <NumberInput
              label="Day of Month"
              min={1}
              max={28}
              value={formDayOfMonth}
              onChange={v => setFormDayOfMonth(Number(v))}
            />
          )}
          
          <Group justify="flex-end" mt="md">
            <Button variant="subtle" onClick={() => { closeCreateModal(); resetForm(); }}>
              Cancel
            </Button>
            <Button onClick={handleCreateJob}>
              {editingJob ? "Update" : "Create"}
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Templates Modal */}
      <Modal
        opened={templateModalOpen}
        onClose={closeTemplateModal}
        title="Job Templates"
        size="lg"
      >
        <ScrollArea h={400}>
          <Stack gap="sm">
            {templates.map(template => (
              <Card key={template.id} withBorder p="sm">
                <Group justify="space-between">
                  <div>
                    <Text fw={600}>{template.name}</Text>
                    <Text size="xs" c="dimmed">{template.description}</Text>
                    <Group gap={4} mt={4}>
                      <Badge size="xs" variant="light">{template.agent}</Badge>
                      <Badge size="xs" variant="outline">{template.frequency}</Badge>
                    </Group>
                  </div>
                  <Button 
                    size="xs" 
                    onClick={() => handleCreateFromTemplate(template.id)}
                  >
                    Use
                  </Button>
                </Group>
              </Card>
            ))}
          </Stack>
        </ScrollArea>
      </Modal>
    </Stack>
  );
}
