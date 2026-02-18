"use client";
import { Shell } from "@/components/layout/Shell";
import { Page } from "@/components/layout/Page";
import { StatCard } from "@/components/widgets/WidgetCard";
import { useState, useEffect, useMemo } from "react";
import {
  Card, Text, Stack, Box, Button, Group, Badge,
  Modal, TextInput, Textarea, Select, Paper, ActionIcon,
  Loader, Tabs, SimpleGrid, ThemeIcon, Tooltip,
  SegmentedControl, ScrollArea, rem, Alert,
} from "@mantine/core";
import { apiFetch } from "@/lib/api";
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import {
  IconPlus, IconTool, IconCheck, IconTrash, IconCalendar,
  IconLayoutKanban, IconList, IconClock, IconAlertTriangle,
  IconChevronRight, IconCircle, IconGripVertical,
  IconCalendarEvent, IconFilter, IconRefresh,
} from "@tabler/icons-react";
import { tokens } from "@/theme/tokens";

interface Task {
  id: number;
  title: string;
  description?: string;
  status: string;
  priority: string;
  category?: string;
  scheduled_date?: string;
  due_date?: string;
  created_at?: string;
}

// Priority configuration
const priorities = {
  urgent: { label: "Urgent", color: tokens.colors.error[500], bgColor: tokens.colors.error[50] },
  high: { label: "High", color: tokens.colors.warn[600], bgColor: tokens.colors.warn[50] },
  medium: { label: "Medium", color: tokens.colors.primary[500], bgColor: tokens.colors.primary[50] },
  low: { label: "Low", color: tokens.colors.neutral[500], bgColor: tokens.colors.neutral[100] },
};

// Category configuration
const categories = [
  { value: "general", label: "General", icon: IconTool },
  { value: "plumbing", label: "Plumbing", icon: IconTool },
  { value: "electrical", label: "Electrical", icon: IconTool },
  { value: "hvac", label: "HVAC", icon: IconTool },
  { value: "exterior", label: "Exterior", icon: IconTool },
  { value: "interior", label: "Interior", icon: IconTool },
  { value: "appliance", label: "Appliance", icon: IconTool },
];

// Check if task is overdue
function isOverdue(task: Task): boolean {
  if (!task.due_date || task.status === "completed") return false;
  return new Date(task.due_date) < new Date();
}

// Check if task is due soon (within 3 days)
function isDueSoon(task: Task): boolean {
  if (!task.due_date || task.status === "completed") return false;
  const dueDate = new Date(task.due_date);
  const now = new Date();
  const diffDays = (dueDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24);
  return diffDays > 0 && diffDays <= 3;
}

// Task card component
function TaskCard({
  task,
  onComplete,
  onDelete,
  onClick,
}: {
  task: Task;
  onComplete: () => void;
  onDelete: () => void;
  onClick?: () => void;
}) {
  const priority = priorities[task.priority as keyof typeof priorities] || priorities.medium;
  const overdue = isOverdue(task);
  const dueSoon = isDueSoon(task);

  return (
    <Paper
      withBorder
      p="md"
      radius="lg"
      style={{
        borderLeft: `4px solid ${priority.color}`,
        backgroundColor: overdue
          ? "var(--task-overdue-bg)"
          : dueSoon
            ? "var(--task-due-soon-bg)"
            : undefined,
        cursor: onClick ? "pointer" : undefined,
        transition: "all 200ms ease",
      }}
      onClick={onClick}
      className={onClick ? "card-clickable" : ""}
    >
      <Group justify="space-between" wrap="nowrap">
        <Stack gap={4} style={{ flex: 1, minWidth: 0 }}>
          <Group gap="xs" wrap="nowrap">
            <Text fw={600} size="sm" truncate>
              {task.title}
            </Text>
            {overdue && (
              <Badge size="xs" color="error" variant="filled">
                Overdue
              </Badge>
            )}
            {dueSoon && !overdue && (
              <Badge size="xs" color="warning" variant="light">
                Due Soon
              </Badge>
            )}
          </Group>

          {task.description && (
            <Text size="xs" c="dimmed" lineClamp={2}>
              {task.description}
            </Text>
          )}

          <Group gap="xs" mt={4}>
            <Badge size="xs" color={priority.color} variant="light">
              {priority.label}
            </Badge>
            {task.category && (
              <Badge size="xs" variant="outline">
                {task.category}
              </Badge>
            )}
            {task.due_date && (
              <Group gap={4}>
                <IconCalendar size={12} style={{ opacity: 0.5 }} />
                <Text size="xs" c={overdue ? "error" : "dimmed"}>
                  {new Date(task.due_date).toLocaleDateString()}
                </Text>
              </Group>
            )}
          </Group>
        </Stack>

        <Group gap="xs">
          <Tooltip label="Mark Complete">
            <ActionIcon
              variant="light"
              color="success"
              radius="md"
              onClick={(e) => {
                e.stopPropagation();
                onComplete();
              }}
            >
              <IconCheck size={16} />
            </ActionIcon>
          </Tooltip>
          <Tooltip label="Delete">
            <ActionIcon
              variant="subtle"
              color="gray"
              radius="md"
              onClick={(e) => {
                e.stopPropagation();
                onDelete();
              }}
            >
              <IconTrash size={16} />
            </ActionIcon>
          </Tooltip>
        </Group>
      </Group>
    </Paper>
  );
}

// Kanban column
function KanbanColumn({
  title,
  tasks,
  color,
  onComplete,
  onDelete,
}: {
  title: string;
  tasks: Task[];
  color: string;
  onComplete: (id: number) => void;
  onDelete: (id: number) => void;
}) {
  return (
    <Card
      withBorder
      radius="lg"
      p={0}
      style={{ flex: 1, minWidth: 280, display: "flex", flexDirection: "column" }}
    >
      <Box
        p="sm"
        style={{
          borderBottom: "1px solid var(--mantine-color-default-border)",
        }}
      >
        <Group justify="space-between">
          <Group gap="xs">
            <IconCircle size={10} fill={color} color={color} />
            <Text fw={600} size="sm">{title}</Text>
          </Group>
          <Badge size="sm" variant="light">{tasks.length}</Badge>
        </Group>
      </Box>
      <ScrollArea style={{ flex: 1 }} p="sm">
        <Stack gap="sm">
          {tasks.length === 0 ? (
            <Text size="sm" c="dimmed" ta="center" py="md">
              No tasks
            </Text>
          ) : (
            tasks.map((task) => (
              <TaskCard
                key={task.id}
                task={task}
                onComplete={() => onComplete(task.id)}
                onDelete={() => onDelete(task.id)}
              />
            ))
          )}
        </Stack>
      </ScrollArea>
    </Card>
  );
}

// Calendar day cell
function CalendarDay({
  date,
  tasks,
  isToday,
  isCurrentMonth,
  onClick,
}: {
  date: Date;
  tasks: Task[];
  isToday: boolean;
  isCurrentMonth: boolean;
  onClick: () => void;
}) {
  const hasOverdue = tasks.some(isOverdue);

  return (
    <Paper
      p="xs"
      radius="md"
      style={{
        minHeight: 80,
        opacity: isCurrentMonth ? 1 : 0.4,
        cursor: tasks.length > 0 ? "pointer" : undefined,
        backgroundColor: isToday
          ? "var(--calendar-today-bg)"
          : hasOverdue
            ? "var(--task-overdue-bg)"
            : undefined,
        border: isToday ? `2px solid ${tokens.colors.primary[500]}` : "1px solid transparent",
      }}
      onClick={onClick}
    >
      <Text
        size="xs"
        fw={isToday ? 700 : 400}
        c={isToday ? "primary" : undefined}
        mb={4}
      >
        {date.getDate()}
      </Text>
      <Stack gap={2}>
        {tasks.slice(0, 3).map((task) => {
          const priority = priorities[task.priority as keyof typeof priorities] || priorities.medium;
          return (
            <Box
              key={task.id}
              style={{
                backgroundColor: priority.color,
                borderRadius: 4,
                padding: "2px 6px",
              }}
            >
              <Text size="xs" c="white" truncate>
                {task.title}
              </Text>
            </Box>
          );
        })}
        {tasks.length > 3 && (
          <Text size="xs" c="dimmed">
            +{tasks.length - 3} more
          </Text>
        )}
      </Stack>
    </Paper>
  );
}

// Calendar view
function CalendarView({
  tasks,
  onTaskClick,
}: {
  tasks: Task[];
  onTaskClick: (task: Task) => void;
}) {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedDay, setSelectedDay] = useState<{
    date: Date;
    tasks: Task[];
  } | null>(null);

  const { days, weeks } = useMemo(() => {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const startDay = new Date(firstDay);
    startDay.setDate(startDay.getDate() - firstDay.getDay());

    const days: { date: Date; tasks: Task[]; isCurrentMonth: boolean }[] = [];
    const current = new Date(startDay);

    while (current <= lastDay || days.length % 7 !== 0) {
      const dateStr = current.toISOString().split("T")[0];
      const dayTasks = tasks.filter((t) => {
        const taskDate = t.due_date || t.scheduled_date;
        return taskDate && taskDate.startsWith(dateStr);
      });

      days.push({
        date: new Date(current),
        tasks: dayTasks,
        isCurrentMonth: current.getMonth() === month,
      });
      current.setDate(current.getDate() + 1);
    }

    const weeks: typeof days[] = [];
    for (let i = 0; i < days.length; i += 7) {
      weeks.push(days.slice(i, i + 7));
    }

    return { days, weeks };
  }, [currentDate, tasks]);

  const today = new Date();
  const monthName = currentDate.toLocaleDateString("en-US", { month: "long", year: "numeric" });

  return (
    <Card withBorder radius="lg" p="md">
      <Group justify="space-between" mb="md">
        <Group gap="xs">
          <ActionIcon
            variant="subtle"
            onClick={() => setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1))}
          >
            <IconChevronRight size={16} style={{ transform: "rotate(180deg)" }} />
          </ActionIcon>
          <Text fw={600}>{monthName}</Text>
          <ActionIcon
            variant="subtle"
            onClick={() => setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1))}
          >
            <IconChevronRight size={16} />
          </ActionIcon>
        </Group>
        <Button
          variant="subtle"
          size="xs"
          onClick={() => setCurrentDate(new Date())}
        >
          Today
        </Button>
      </Group>

      {/* Day headers */}
      <SimpleGrid cols={7} spacing={4} mb={4}>
        {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((day) => (
          <Text key={day} size="xs" fw={600} ta="center" c="dimmed">
            {day}
          </Text>
        ))}
      </SimpleGrid>

      {/* Calendar grid */}
      <Stack gap={4}>
        {weeks.map((week, weekIndex) => (
          <SimpleGrid key={weekIndex} cols={7} spacing={4}>
            {week.map((day) => (
              <CalendarDay
                key={day.date.toISOString()}
                date={day.date}
                tasks={day.tasks}
                isToday={day.date.toDateString() === today.toDateString()}
                isCurrentMonth={day.isCurrentMonth}
                onClick={() => {
                  setSelectedDay({ date: day.date, tasks: day.tasks });
                  if (day.tasks.length === 1) {
                    onTaskClick(day.tasks[0]);
                  }
                }}
              />
            ))}
          </SimpleGrid>
        ))}
      </Stack>

      {selectedDay && (
        <Box mt="md">
          <Group justify="space-between" mb="xs">
            <Text fw={600} size="sm">
              {selectedDay.date.toLocaleDateString(undefined, { weekday: "long", month: "short", day: "numeric" })}
            </Text>
            <Badge size="sm" variant="light">
              {selectedDay.tasks.length} task{selectedDay.tasks.length === 1 ? "" : "s"}
            </Badge>
          </Group>
          {selectedDay.tasks.length === 0 ? (
            <Text size="sm" c="dimmed">
              No tasks scheduled for this day.
            </Text>
          ) : (
            <Stack gap="xs">
              {selectedDay.tasks.map((task) => (
                <Paper
                  key={task.id}
                  withBorder
                  radius="md"
                  p="sm"
                  style={{ cursor: "pointer" }}
                  onClick={() => onTaskClick(task)}
                >
                  <Group justify="space-between" wrap="nowrap">
                    <Text size="sm" fw={600} truncate>
                      {task.title}
                    </Text>
                    <Badge size="xs" variant="light">
                      {task.priority}
                    </Badge>
                  </Group>
                  {task.description && (
                    <Text size="xs" c="dimmed" lineClamp={1}>
                      {task.description}
                    </Text>
                  )}
                </Paper>
              ))}
            </Stack>
          )}
        </Box>
      )}
    </Card>
  );
}

export default function MaintenancePage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [tasksError, setTasksError] = useState<string | null>(null);
  const [opened, { open, close }] = useDisclosure(false);
  const [detailOpened, { open: openDetail, close: closeDetail }] = useDisclosure(false);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [viewMode, setViewMode] = useState<"list" | "kanban" | "calendar">("list");
  const [filterPriority, setFilterPriority] = useState<string | null>(null);
  const [newTask, setNewTask] = useState({
    title: "",
    description: "",
    priority: "medium",
    category: "general",
    due_date: null as Date | null,
  });

  const fetchTasks = async () => {
    setTasksError(null);
    try {
      const res = await apiFetch<{ tasks?: Task[] }>("/tasks?limit=50");
      if (res && "tasks" in res) {
        setTasks(res.tasks || []);
      }
    } catch (e) {
      console.error("Failed to fetch tasks:", e);
      setTasks([]);
      setTasksError("Unable to load tasks from the backend.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTasks();
  }, []);

  useEffect(() => {
    const handler = () => fetchTasks();
    window.addEventListener("mycasa-system-sync", handler as EventListener);
    return () => window.removeEventListener("mycasa-system-sync", handler as EventListener);
  }, []);

  const handleAddTask = async () => {
    if (!newTask.title.trim()) {
      notifications.show({ title: "Error", message: "Title is required", color: "red" });
      return;
    }

    try {
      const taskData = {
        ...newTask,
        due_date: newTask.due_date?.toISOString(),
      };
      const res = await apiFetch<{ id: number }>("/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(taskData),
      });

      if (res) {
        notifications.show({ title: "Task Added", message: `"${newTask.title}" created`, color: "green" });
        setNewTask({ title: "", description: "", priority: "medium", category: "general", due_date: null });
        close();
        fetchTasks();
      }
    } catch (e) {
      notifications.show({ title: "Error", message: "Failed to add task", color: "red" });
    }
  };

  const handleCompleteTask = async (taskId: number) => {
    try {
      const task = tasks.find((t) => t.id === taskId);
      await apiFetch(`/tasks/${taskId}/complete`, { method: "PATCH" });
      notifications.show({ title: "Task Completed", message: "Nice work!", color: "green" });
      fetchTasks();
      if (typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent("mycasa-chat-sync", {
          detail: { conversationId: task?.conversation_id || null },
        }));
      }
    } catch (e) {
      notifications.show({ title: "Error", message: "Failed to complete task", color: "red" });
    }
  };

  const handleDeleteTask = async (taskId: number) => {
    try {
      const task = tasks.find((t) => t.id === taskId);
      await apiFetch(`/tasks/${taskId}`, { method: "DELETE" });
      notifications.show({ title: "Task Deleted", message: "Task removed", color: "gray" });
      fetchTasks();
      if (typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent("mycasa-chat-sync", {
          detail: { conversationId: task?.conversation_id || null },
        }));
      }
    } catch (e) {
      notifications.show({ title: "Error", message: "Failed to delete task", color: "red" });
    }
  };

  // Filter tasks
  const filteredTasks = useMemo(() => {
    let result = tasks;
    if (filterPriority) {
      result = result.filter((t) => t.priority === filterPriority);
    }
    return result;
  }, [tasks, filterPriority]);

  const pendingTasks = filteredTasks.filter((t) => t.status === "pending");
  const completedTasks = filteredTasks.filter((t) => t.status === "completed");
  const overdueTasks = pendingTasks.filter(isOverdue);

  // Group tasks by priority for kanban
  const tasksByPriority = {
    urgent: pendingTasks.filter((t) => t.priority === "urgent"),
    high: pendingTasks.filter((t) => t.priority === "high"),
    medium: pendingTasks.filter((t) => t.priority === "medium"),
    low: pendingTasks.filter((t) => t.priority === "low"),
  };
  
  const handleOpenTask = (task: Task) => {
    setSelectedTask(task);
    openDetail();
  };

  return (
    <Shell>
      <Page
        title="Maintenance"
        subtitle={`${pendingTasks.length} pending tasks${overdueTasks.length > 0 ? ` - ${overdueTasks.length} overdue` : ""}`}
        actions={
          <Group gap="sm">
            <Button leftSection={<IconPlus size={16} />} onClick={open}>
              Add Task
            </Button>
            <ActionIcon variant="light" size="lg" onClick={fetchTasks}>
              <IconRefresh size={18} />
            </ActionIcon>
          </Group>
        }
      >
        <Stack gap="lg" className="maintenance-page">
          {tasksError && (
            <Alert color="red" title="Tasks unavailable">
              {tasksError}
            </Alert>
          )}
          {/* Stats */}
          <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} spacing="md" className="maintenance-stats">
            <StatCard
              title="Pending Tasks"
              value={pendingTasks.length}
              icon={<IconTool size={22} />}
              color="primary"
            />
            <StatCard
              title="Overdue"
              value={overdueTasks.length}
              icon={<IconAlertTriangle size={22} />}
              color={overdueTasks.length > 0 ? "error" : "neutral"}
            />
            <StatCard
              title="Due This Week"
              value={pendingTasks.filter(isDueSoon).length}
              icon={<IconClock size={22} />}
              color="warning"
            />
            <StatCard
              title="Completed"
              value={completedTasks.length}
              icon={<IconCheck size={22} />}
              color="success"
            />
          </SimpleGrid>

          {/* View controls */}
          <Group justify="space-between" className="maintenance-controls">
            <SegmentedControl
              value={viewMode}
              onChange={(v) => setViewMode(v as typeof viewMode)}
              data={[
                { value: "list", label: <Group gap={6}><IconList size={16} /><Text size="sm">List</Text></Group> },
                { value: "kanban", label: <Group gap={6}><IconLayoutKanban size={16} /><Text size="sm">Kanban</Text></Group> },
                { value: "calendar", label: <Group gap={6}><IconCalendar size={16} /><Text size="sm">Calendar</Text></Group> },
              ]}
            />
            <Select
              placeholder="Filter by priority"
              clearable
              size="sm"
              w={180}
              leftSection={<IconFilter size={16} />}
              value={filterPriority}
              onChange={setFilterPriority}
              data={Object.entries(priorities).map(([value, { label }]) => ({ value, label }))}
            />
          </Group>

          {/* Content */}
          {loading ? (
            <Card withBorder p="xl" radius="lg">
              <Box py="xl" style={{ textAlign: "center" }}>
                <Loader />
                <Text c="dimmed" mt="md">Loading tasks...</Text>
              </Box>
            </Card>
          ) : viewMode === "list" ? (
            <Stack gap="md">
              {pendingTasks.length === 0 ? (
                <Card withBorder p="xl" radius="lg">
                  <Box py="xl" style={{ textAlign: "center" }}>
                    <IconTool size={48} stroke={1.5} style={{ color: "var(--mantine-color-dimmed)" }} />
                    <Text size="lg" fw={500} mt="md">No pending tasks</Text>
                    <Text c="dimmed" size="sm">Add maintenance tasks to get started</Text>
                    <Button mt="md" leftSection={<IconPlus size={16} />} onClick={open}>
                      Add Task
                    </Button>
                  </Box>
                </Card>
              ) : (
                <Stack gap="sm">
                  {pendingTasks.map((task) => (
                    <TaskCard
                      key={task.id}
                      task={task}
                      onComplete={() => handleCompleteTask(task.id)}
                      onDelete={() => handleDeleteTask(task.id)}
                      onClick={() => handleOpenTask(task)}
                    />
                  ))}
                </Stack>
              )}

              {completedTasks.length > 0 && (
                <>
                  <Text fw={600} mt="md">Completed ({completedTasks.length})</Text>
                  <Stack gap="sm">
                    {completedTasks.slice(0, 5).map((task) => (
                      <Paper key={task.id} withBorder p="sm" radius="lg" style={{ opacity: 0.6 }}>
                        <Group justify="space-between">
                          <Text size="sm" td="line-through">{task.title}</Text>
                          <Badge size="xs" color="success">Done</Badge>
                        </Group>
                      </Paper>
                    ))}
                  </Stack>
                </>
              )}
            </Stack>
          ) : viewMode === "kanban" ? (
            <Group gap="md" align="stretch" style={{ minHeight: 400 }}>
              <KanbanColumn
                title="Urgent"
                tasks={tasksByPriority.urgent}
                color={priorities.urgent.color}
                onComplete={handleCompleteTask}
                onDelete={handleDeleteTask}
              />
              <KanbanColumn
                title="High"
                tasks={tasksByPriority.high}
                color={priorities.high.color}
                onComplete={handleCompleteTask}
                onDelete={handleDeleteTask}
              />
              <KanbanColumn
                title="Medium"
                tasks={tasksByPriority.medium}
                color={priorities.medium.color}
                onComplete={handleCompleteTask}
                onDelete={handleDeleteTask}
              />
              <KanbanColumn
                title="Low"
                tasks={tasksByPriority.low}
                color={priorities.low.color}
                onComplete={handleCompleteTask}
                onDelete={handleDeleteTask}
              />
            </Group>
          ) : (
            <CalendarView tasks={pendingTasks} onTaskClick={handleOpenTask} />
          )}
        </Stack>

        {/* Add Task Modal */}
        <Modal opened={opened} onClose={close} title="Add Task" radius="lg">
          <Stack gap="md">
            <TextInput
              label="Title"
              placeholder="e.g., Clean gutters"
              required
              value={newTask.title}
              onChange={(e) => setNewTask({ ...newTask, title: e.target.value })}
            />
            <Textarea
              label="Description"
              placeholder="Details..."
              value={newTask.description}
              onChange={(e) => setNewTask({ ...newTask, description: e.target.value })}
            />
            <Group grow>
              <Select
                label="Priority"
                data={Object.entries(priorities).map(([value, { label }]) => ({ value, label }))}
                value={newTask.priority}
                onChange={(v) => setNewTask({ ...newTask, priority: v || "medium" })}
              />
              <Select
                label="Category"
                data={categories.map((c) => ({ value: c.value, label: c.label }))}
                value={newTask.category}
                onChange={(v) => setNewTask({ ...newTask, category: v || "general" })}
              />
            </Group>
            <TextInput
              label="Due Date"
              type="date"
              value={newTask.due_date ? newTask.due_date.toISOString().split('T')[0] : ''}
              onChange={(e) => setNewTask({ ...newTask, due_date: e.target.value ? new Date(e.target.value) : null })}
            />
            <Group justify="flex-end" mt="md">
              <Button variant="subtle" onClick={close}>Cancel</Button>
              <Button onClick={handleAddTask}>Add Task</Button>
            </Group>
          </Stack>
        </Modal>

        {/* Task Detail Modal */}
        <Modal
          opened={detailOpened}
          onClose={closeDetail}
          title={selectedTask ? selectedTask.title : "Task Details"}
          radius="lg"
        >
          {selectedTask ? (
            <Stack gap="sm">
              <Group gap="xs">
                <Badge size="sm" color={priorities[selectedTask.priority as keyof typeof priorities]?.color || "gray"}>
                  {priorities[selectedTask.priority as keyof typeof priorities]?.label || selectedTask.priority}
                </Badge>
                {selectedTask.category && (
                  <Badge size="sm" variant="outline">
                    {selectedTask.category}
                  </Badge>
                )}
                <Badge size="sm" variant="light">
                  {selectedTask.status}
                </Badge>
              </Group>
              {selectedTask.description && (
                <Text size="sm" c="dimmed">
                  {selectedTask.description}
                </Text>
              )}
              <Group gap="xs">
                <IconCalendar size={14} style={{ opacity: 0.6 }} />
                <Text size="sm">
                  {selectedTask.due_date ? new Date(selectedTask.due_date).toLocaleDateString() : "No due date"}
                </Text>
              </Group>
              <Group justify="flex-end" mt="md">
                {selectedTask.status !== "completed" && (
                  <Button
                    leftSection={<IconCheck size={16} />}
                    onClick={() => {
                      handleCompleteTask(selectedTask.id);
                      closeDetail();
                    }}
                  >
                    Mark Complete
                  </Button>
                )}
                <Button
                  variant="light"
                  color="red"
                  leftSection={<IconTrash size={16} />}
                  onClick={() => {
                    handleDeleteTask(selectedTask.id);
                    closeDetail();
                  }}
                >
                  Delete Task
                </Button>
              </Group>
            </Stack>
          ) : (
            <Text c="dimmed" size="sm">
              Task details unavailable.
            </Text>
          )}
        </Modal>
      </Page>
    </Shell>
  );
}
