"use client";
import { Shell } from "@/components/layout/Shell";
import { apiFetch } from "@/lib/api";
import { Page } from "@/components/layout/Page";
import { useState, useEffect } from "react";
import { 
  Card, Text, Stack, Box, Button, Group, Badge, 
  Modal, TextInput, Textarea, Select, Paper, ActionIcon,
  Loader, ThemeIcon, SimpleGrid, Tabs, Avatar, Divider,
  Rating, Tooltip, Menu
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { 
  IconPlus, IconUsers, IconPhone, IconMail, IconCheck, 
  IconUser, IconBriefcase, IconTrash, IconDotsVertical,
  IconTools, IconHome
} from "@tabler/icons-react";

interface Contractor {
  id: number;
  name: string;
  company?: string;
  phone?: string;
  email?: string;
  service_type: string;
  hourly_rate?: number;
  rating?: number;
  notes?: string;
  last_service_date?: string;
}

interface Job {
  id: number;
  description: string;
  contractor_name?: string;
  contractor_id?: number;
  status: string;
  estimated_cost?: number;
  actual_cost?: number;
  proposed_start?: string;
  confirmed_start?: string;
}

export default function ContractorsPage() {
  const [contractors, setContractors] = useState<Contractor[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [jobModalOpened, { open: openJobModal, close: closeJobModal }] = useDisclosure(false);
  const [contractorModalOpened, { open: openContractorModal, close: closeContractorModal }] = useDisclosure(false);
  
  const [newJob, setNewJob] = useState({ 
    description: "", 
    contractor_id: "",
    contractor_name: "",
    estimated_cost: 0
  });
  
  const [newContractor, setNewContractor] = useState({
    name: "",
    phone: "",
    email: "",
    service_type: "General",
    notes: "",
    rating: 0
  });

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [contractorsData, jobsData] = await Promise.all([
        apiFetch<any>("/api/contractors"),
        apiFetch<any>("/api/contractors/jobs?limit=50"),
      ]);
      setContractors(contractorsData.contractors || []);
      setJobs(jobsData.jobs || []);
    } catch (e) {
      console.error("Failed to fetch:", e);
      setError("Unable to load contractors right now.");
      notifications.show({
        title: "Load failed",
        message: "Could not load contractors and jobs",
        color: "red",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleAddJob = async () => {
    if (!newJob.description.trim()) {
      notifications.show({ title: "Error", message: "Job description required", color: "red" });
      return;
    }

    // Get contractor name from selection
    const selectedContractor = contractors.find(c => c.id.toString() === newJob.contractor_id);
    
    try {
      await apiFetch("/api/contractors/jobs", {
        method: "POST",
        body: JSON.stringify({
          description: newJob.description,
          contractor_name: selectedContractor?.name || newJob.contractor_name,
          contractor_id: newJob.contractor_id ? parseInt(newJob.contractor_id) : null,
          estimated_cost: newJob.estimated_cost || null,
        }),
      });

      notifications.show({ title: "Job Created", message: "Contractor job added", color: "green" });
      setNewJob({ description: "", contractor_id: "", contractor_name: "", estimated_cost: 0 });
      closeJobModal();
      fetchData();
    } catch (e) {
      notifications.show({ title: "Error", message: "Could not create job", color: "red" });
    }
  };

  const handleAddContractor = async () => {
    if (!newContractor.name.trim()) {
      notifications.show({ title: "Error", message: "Name required", color: "red" });
      return;
    }

    try {
      await apiFetch("/api/contractors", {
        method: "POST",
        body: JSON.stringify(newContractor),
      });

      notifications.show({ title: "Contractor Added", message: `Added ${newContractor.name}`, color: "green" });
      setNewContractor({ name: "", phone: "", email: "", service_type: "General", notes: "", rating: 0 });
      closeContractorModal();
      fetchData();
    } catch (e) {
      notifications.show({ title: "Error", message: "Could not add contractor", color: "red" });
    }
  };

  const handleDeleteContractor = async (id: number, name: string) => {
    if (!confirm(`Delete ${name}?`)) return;
    
    try {
      await apiFetch(`/api/contractors/${id}`, { method: "DELETE" });
      notifications.show({ title: "Deleted", message: `Removed ${name}`, color: "orange" });
      fetchData();
    } catch (e) {
      notifications.show({ title: "Error", message: "Could not delete", color: "red" });
    }
  };

  const handleCompleteJob = async (jobId: number) => {
    try {
      await apiFetch(`/api/contractors/jobs/${jobId}/complete`, { 
        method: "PATCH",
        body: JSON.stringify({ evidence: "Marked complete via UI" })
      });
      notifications.show({ title: "Job Completed", message: "Job marked as done", color: "green" });
      fetchData();
    } catch (e) {
      notifications.show({ title: "Error", message: "Failed to complete", color: "red" });
    }
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      completed: "green",
      in_progress: "blue", 
      scheduled: "orange",
      pending: "yellow",
      proposed: "gray",
      blocked: "red"
    };
    return colors[status] || "gray";
  };

  const getServiceIcon = (type: string) => {
    if (type?.toLowerCase().includes("manager") || type?.toLowerCase().includes("assistant")) {
      return <IconHome size={16} />;
    }
    return <IconTools size={16} />;
  };

  const activeJobs = jobs.filter(j => j.status !== "completed" && j.status !== "cancelled");
  const completedJobs = jobs.filter(j => j.status === "completed");
  const totalEst = activeJobs.reduce((sum, j) => sum + (j.estimated_cost || 0), 0);
  const statsUnavailable = Boolean(error);

  const subtitle = statsUnavailable
    ? "Contractor data unavailable"
    : loading
      ? "Loading contractors..."
      : `${contractors.length} contractors • ${activeJobs.length} active jobs`;

  return (
    <Shell>
      <Page
        title="Contractors"
        subtitle={subtitle}
        actions={
          <Group>
            <Button variant="light" leftSection={<IconUser size={16} />} onClick={openContractorModal}>
              Add Contractor
            </Button>
            <Button leftSection={<IconPlus size={16} />} onClick={openJobModal}>
              New Job
            </Button>
          </Group>
        }
      >
      <Stack gap="md" className="contractors-page">
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} className="contractors-stats">
          <Card withBorder radius="lg">
            <Text size="xs" c="dimmed" tt="uppercase" fw={600}>Contractors</Text>
            {loading ? (
              <Loader size="sm" mt={8} />
            ) : statsUnavailable ? (
              <Text size="sm" c="dimmed" mt={6}>Unavailable</Text>
            ) : (
              <Text size="xl" fw={700} mt={4}>{contractors.length}</Text>
            )}
            <Text size="xs" c="dimmed">Active profiles</Text>
          </Card>
          <Card withBorder radius="lg">
            <Text size="xs" c="dimmed" tt="uppercase" fw={600}>Active jobs</Text>
            {loading ? (
              <Loader size="sm" mt={8} />
            ) : statsUnavailable ? (
              <Text size="sm" c="dimmed" mt={6}>Unavailable</Text>
            ) : (
              <Text size="xl" fw={700} mt={4}>{activeJobs.length}</Text>
            )}
            <Text size="xs" c="dimmed">In pipeline</Text>
          </Card>
          <Card withBorder radius="lg">
            <Text size="xs" c="dimmed" tt="uppercase" fw={600}>Completed</Text>
            {loading ? (
              <Loader size="sm" mt={8} />
            ) : statsUnavailable ? (
              <Text size="sm" c="dimmed" mt={6}>Unavailable</Text>
            ) : (
              <Text size="xl" fw={700} mt={4}>{completedJobs.length}</Text>
            )}
            <Text size="xs" c="dimmed">Finished jobs</Text>
          </Card>
          <Card withBorder radius="lg">
            <Text size="xs" c="dimmed" tt="uppercase" fw={600}>Est. active spend</Text>
            {loading ? (
              <Loader size="sm" mt={8} />
            ) : statsUnavailable ? (
              <Text size="sm" c="dimmed" mt={6}>Unavailable</Text>
            ) : (
              <Text size="xl" fw={700} mt={4}>
                {totalEst > 0 ? `$${totalEst.toLocaleString()}` : "—"}
              </Text>
            )}
            <Text size="xs" c="dimmed">From active jobs</Text>
          </Card>
        </SimpleGrid>

        {loading ? (
          <Card withBorder p="xl">
            <Box py="xl" style={{ textAlign: "center" }}>
              <Loader />
              <Text c="dimmed" mt="md">Loading...</Text>
            </Box>
          </Card>
        ) : error ? (
          <Card withBorder p="xl">
            <Box py="xl" style={{ textAlign: "center" }}>
              <Text fw={600}>{error}</Text>
              <Text c="dimmed" size="sm">Check your backend connection and try again.</Text>
              <Button mt="md" variant="light" onClick={fetchData}>Retry</Button>
            </Box>
          </Card>
        ) : (
          <Tabs defaultValue="contractors" className="contractors-tabs">
            <Tabs.List mb="md" className="contractors-tabs-list">
              <Tabs.Tab value="contractors" leftSection={<IconUsers size={16} />}>
                Contractors ({contractors.length})
              </Tabs.Tab>
              <Tabs.Tab value="jobs" leftSection={<IconBriefcase size={16} />}>
                Jobs ({activeJobs.length})
              </Tabs.Tab>
            </Tabs.List>

            {/* Contractors Tab */}
            <Tabs.Panel value="contractors">
              {contractors.length === 0 ? (
                <Card withBorder p="xl">
                  <Box py="xl" style={{ textAlign: "center" }}>
                    <IconUsers size={48} stroke={1.5} style={{ opacity: 0.3 }} />
                    <Text size="lg" fw={500} mt="md">No contractors yet</Text>
                    <Text c="dimmed" size="sm">Add your first contractor to get started</Text>
                    <Button mt="md" onClick={openContractorModal}>Add Contractor</Button>
                  </Box>
                </Card>
              ) : (
                <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} className="contractors-grid">
                  {contractors.map(contractor => (
                    <Card key={contractor.id} withBorder p="lg" radius="md">
                      <Group justify="space-between" mb="sm">
                        <Group gap="sm">
                          <Avatar color={contractor.service_type === "House Manager" ? "violet" : "blue"} radius="xl">
                            {contractor.name.charAt(0)}
                          </Avatar>
                          <div>
                            <Text fw={600}>{contractor.name}</Text>
                            <Group gap={4}>
                              <ThemeIcon size="xs" variant="light" color="gray">
                                {getServiceIcon(contractor.service_type)}
                              </ThemeIcon>
                              <Text size="xs" c="dimmed">{contractor.service_type}</Text>
                            </Group>
                          </div>
                        </Group>
                        <Menu shadow="md" width={150}>
                          <Menu.Target>
                            <ActionIcon variant="subtle" color="gray">
                              <IconDotsVertical size={16} />
                            </ActionIcon>
                          </Menu.Target>
                          <Menu.Dropdown>
                            <Menu.Item 
                              color="red" 
                              leftSection={<IconTrash size={14} />}
                              onClick={() => handleDeleteContractor(contractor.id, contractor.name)}
                            >
                              Delete
                            </Menu.Item>
                          </Menu.Dropdown>
                        </Menu>
                      </Group>

                      <Stack gap="xs">
                        {contractor.phone && (
                          <Group gap="xs">
                            <ThemeIcon size="sm" variant="light" color="gray">
                              <IconPhone size={12} />
                            </ThemeIcon>
                            <Text size="sm">{contractor.phone}</Text>
                          </Group>
                        )}
                        {contractor.email && (
                          <Group gap="xs">
                            <ThemeIcon size="sm" variant="light" color="gray">
                              <IconMail size={12} />
                            </ThemeIcon>
                            <Text size="sm">{contractor.email}</Text>
                          </Group>
                        )}
                        {contractor.rating && contractor.rating > 0 && (
                          <Group gap="xs">
                            <Rating value={contractor.rating} readOnly size="xs" />
                            <Text size="xs" c="dimmed">({contractor.rating}/5)</Text>
                          </Group>
                        )}
                        {contractor.notes && (
                          <Text size="xs" c="dimmed" lineClamp={2}>
                            {contractor.notes}
                          </Text>
                        )}
                      </Stack>

                      <Divider my="sm" />

                      <Group>
                        {contractor.phone && (
                          <Button 
                            size="xs" 
                            variant="light" 
                            leftSection={<IconPhone size={14} />}
                            component="a"
                            href={`tel:${contractor.phone}`}
                          >
                            Call
                          </Button>
                        )}
                        <Button 
                          size="xs" 
                          variant="light"
                          onClick={() => {
                            setNewJob({ ...newJob, contractor_id: contractor.id.toString(), contractor_name: contractor.name });
                            openJobModal();
                          }}
                        >
                          Create Job
                        </Button>
                      </Group>
                    </Card>
                  ))}
                </SimpleGrid>
              )}
            </Tabs.Panel>

            {/* Jobs Tab */}
            <Tabs.Panel value="jobs">
              {activeJobs.length === 0 && completedJobs.length === 0 ? (
                <Card withBorder p="xl">
                  <Box py="xl" style={{ textAlign: "center" }}>
                    <IconBriefcase size={48} stroke={1.5} style={{ opacity: 0.3 }} />
                    <Text size="lg" fw={500} mt="md">No jobs yet</Text>
                    <Text c="dimmed" size="sm">Create a job to track contractor work</Text>
                    <Button mt="md" onClick={openJobModal}>Create Job</Button>
                  </Box>
                </Card>
              ) : (
                <Stack gap="md" className="contractors-jobs">
                  {/* Active Jobs */}
                  {activeJobs.length > 0 && (
                    <>
                      <Text fw={600}>Active Jobs ({activeJobs.length})</Text>
                      <Stack gap="sm">
                        {activeJobs.map(job => (
                          <Paper key={job.id} withBorder p="md" radius="md">
                            <Group justify="space-between" align="flex-start">
                              <div style={{ flex: 1 }}>
                                <Group gap="xs" mb={4}>
                                  <Text fw={600}>{job.description}</Text>
                                  <Badge size="sm" color={getStatusColor(job.status)}>
                                    {job.status.replace("_", " ")}
                                  </Badge>
                                </Group>
                                {job.contractor_name && (
                                  <Group gap={4}>
                                    <ThemeIcon size="sm" variant="light" color="gray">
                                      <IconUser size={12} />
                                    </ThemeIcon>
                                    <Text size="sm" c="dimmed">{job.contractor_name}</Text>
                                  </Group>
                                )}
                                {job.estimated_cost && job.estimated_cost > 0 && (
                                  <Text size="sm" c="orange" mt={4}>
                                    Est. ${job.estimated_cost.toLocaleString()}
                                  </Text>
                                )}
                              </div>
                              <Tooltip label="Mark Complete">
                                <ActionIcon 
                                  variant="light" 
                                  color="green"
                                  onClick={() => handleCompleteJob(job.id)}
                                >
                                  <IconCheck size={16} />
                                </ActionIcon>
                              </Tooltip>
                            </Group>
                          </Paper>
                        ))}
                      </Stack>
                    </>
                  )}

                  {/* Completed Jobs */}
                  {completedJobs.length > 0 && (
                    <>
                      <Text fw={600} mt="md">Completed ({completedJobs.length})</Text>
                      <Stack gap="sm">
                        {completedJobs.slice(0, 5).map(job => (
                          <Paper key={job.id} withBorder p="sm" radius="md" style={{ opacity: 0.6 }}>
                            <Group justify="space-between">
                              <div>
                                <Text size="sm" td="line-through">{job.description}</Text>
                                <Text size="xs" c="dimmed">{job.contractor_name}</Text>
                              </div>
                              <Badge size="xs" color="green">Done</Badge>
                            </Group>
                          </Paper>
                        ))}
                      </Stack>
                    </>
                  )}
                </Stack>
              )}
            </Tabs.Panel>
          </Tabs>
        )}
      </Stack>

      {/* Add Job Modal */}
      <Modal opened={jobModalOpened} onClose={closeJobModal} title="Create Contractor Job">
        <Stack gap="md">
          <Textarea
            label="Job Description"
            placeholder="e.g., Fix deck railing, deep clean kitchen..."
            required
            value={newJob.description}
            onChange={(e) => setNewJob({ ...newJob, description: e.target.value })}
            minRows={2}
          />
          <Select
            label="Contractor"
            placeholder="Select contractor"
            data={contractors.map(c => ({ value: c.id.toString(), label: `${c.name} (${c.service_type})` }))}
            value={newJob.contractor_id}
            onChange={(val) => setNewJob({ ...newJob, contractor_id: val || "" })}
            clearable
          />
          <TextInput
            label="Estimated Cost"
            type="number"
            placeholder="0"
            leftSection="$"
            value={newJob.estimated_cost || ""}
            onChange={(e) => setNewJob({ ...newJob, estimated_cost: parseFloat(e.target.value) || 0 })}
          />
          <Group justify="flex-end">
            <Button variant="subtle" onClick={closeJobModal}>Cancel</Button>
            <Button onClick={handleAddJob}>Create Job</Button>
          </Group>
        </Stack>
      </Modal>

      {/* Add Contractor Modal */}
      <Modal opened={contractorModalOpened} onClose={closeContractorModal} title="Add Contractor">
        <Stack gap="md">
          <TextInput
            label="Name"
            placeholder="e.g., John Smith"
            required
            value={newContractor.name}
            onChange={(e) => setNewContractor({ ...newContractor, name: e.target.value })}
          />
          <Select
            label="Service Type"
            data={["General", "House Manager", "Plumber", "Electrician", "Cleaner", "Landscaper", "HVAC", "Handyman", "Other"]}
            value={newContractor.service_type}
            onChange={(val) => setNewContractor({ ...newContractor, service_type: val || "General" })}
          />
          <TextInput
            label="Phone"
            placeholder="+1 555 123 4567"
            value={newContractor.phone}
            onChange={(e) => setNewContractor({ ...newContractor, phone: e.target.value })}
          />
          <TextInput
            label="Email"
            placeholder="contractor@example.com"
            value={newContractor.email}
            onChange={(e) => setNewContractor({ ...newContractor, email: e.target.value })}
          />
          <Textarea
            label="Notes"
            placeholder="Any notes about this contractor..."
            value={newContractor.notes}
            onChange={(e) => setNewContractor({ ...newContractor, notes: e.target.value })}
          />
          <Group justify="flex-end">
            <Button variant="subtle" onClick={closeContractorModal}>Cancel</Button>
            <Button onClick={handleAddContractor}>Add Contractor</Button>
          </Group>
        </Stack>
      </Modal>
          </Page>
    </Shell>
  );
}
