"use client";

import { useState, useEffect } from "react";
import { getApiBaseUrl } from "@/lib/api";
import {
  Modal, Stepper, Button, Group, TextInput, Select, NumberInput,
  Stack, Text, Title, Paper, ThemeIcon, Box, Progress, Checkbox,
  Textarea, SimpleGrid, Badge, Alert, Divider, PasswordInput,
  ActionIcon, Tooltip, Switch, Card, Center, RingProgress, Loader,
  Table, Image, Code, Transition
} from "@mantine/core";
import {
  IconHome, IconCoin, IconTool, IconBell, IconUsers, IconCheck,
  IconRocket, IconArrowRight, IconArrowLeft, IconX, IconSparkles,
  IconBrandWhatsapp, IconMail, IconCalendar, IconShield, IconSettings,
  IconChevronRight, IconCircleCheck, IconAlertCircle, IconPlus, IconTrash,
  IconPhone, IconQrcode, IconUserPlus, IconBrandGoogle, IconUpload,
  IconExternalLink, IconRefresh, IconDownload, IconRobot, IconTerminal2
} from "@tabler/icons-react";
import { notifications } from "@mantine/notifications";

// Contractor interface
interface Contractor {
  id: string;
  name: string;
  phone: string;
  specialty: string;
}

// WhatsApp contact interface
interface WhatsAppContact {
  id: string;
  name: string;
  phone: string;
}

// Setup data interface
interface SetupData {
  // Step 1: Welcome (Tenant Setup)
  householdName: string;
  timezone: string;
  locale: string;
  
  // Step 2: Income Source (REQUIRED per spec)
  primaryIncomeSource: string;
  incomeFrequency: string;
  
  // Step 3: Budgets
  monthlyBudget: number;
  systemCostCap: number;
  approvalThreshold: number;
  investmentStyle: string;
  
  // Step 4: Contractors
  contractors: Contractor[];
  
  // Step 5: WhatsApp
  enableWhatsapp: boolean;
  whatsappNumber: string;
  whatsappContacts: WhatsAppContact[];
  whatsappLinked: boolean;
  
  // Step 6: Google OAuth (gog)
  googleCredentialsConfigured: boolean;
  googleAccountEmail: string;
  googleAuthenticated: boolean;
  
  // Step 7: Connectors (optional)
  enableGmail: boolean;
  gmailAccount: string;
  enableCalendar: boolean;
  
  // Step 8: Notifications
  enableInApp: boolean;
  enablePush: boolean;
  enableEmail: boolean;
  alertEmail: string;
}

const API_URL = getApiBaseUrl();

// Log action to Janitor agent
async function logToJanitor(action: string, details: string) {
  try {
    await fetch(`${API_URL}/api/agents/janitor/log`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, details }),
    });
  } catch (e) {
    console.log("[SetupWizard] Janitor logging failed (backend may be offline)");
  }
}

// Notify Manager agent
async function notifyManager(message: string) {
  try {
    await fetch(`${API_URL}/api/agents/manager/notify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
  } catch (e) {
    console.log("[SetupWizard] Manager notify failed (backend may be offline)");
  }
}

const defaultSetupData: SetupData = {
  householdName: "",
  timezone: "America/Los_Angeles",
  locale: "en-US",
  primaryIncomeSource: "",
  incomeFrequency: "monthly",
  monthlyBudget: 10000,
  systemCostCap: 1000,
  approvalThreshold: 500,
  investmentStyle: "moderate",
  contractors: [],
  enableWhatsapp: false,
  whatsappNumber: "",
  whatsappContacts: [],
  whatsappLinked: false,
  googleCredentialsConfigured: false,
  googleAccountEmail: "",
  googleAuthenticated: false,
  enableGmail: false,
  gmailAccount: "",
  enableCalendar: false,
  enableInApp: true,
  enablePush: false,
  enableEmail: false,
  alertEmail: "",
};

// ============ STEP COMPONENTS ============

function WelcomeStep({ data, setData }: { data: SetupData; setData: (d: SetupData) => void }) {
  return (
    <Stack gap="xl" align="center">
      <Center>
        <ThemeIcon size={80} radius="xl" variant="gradient" gradient={{ from: "indigo", to: "violet" }}>
          <IconHome size={40} />
        </ThemeIcon>
      </Center>
      
      <div style={{ textAlign: "center" }}>
        <Title order={2}>Welcome to MyCasa Pro</Title>
        <Text size="lg" c="dimmed" mt="xs">Your home operating system</Text>
      </div>
      
      <Paper withBorder p="xl" radius="md" w="100%" maw={500}>
        <Stack gap="md">
          <TextInput
            label="Household Name"
            description="Give your home a name"
            placeholder="e.g., Tenkiang Residence"
            value={data.householdName}
            onChange={(e) => setData({ ...data, householdName: e.target.value })}
            leftSection={<IconHome size={16} />}
          />
          
          <Select
            label="Timezone"
            description="Your local timezone for scheduling"
            value={data.timezone}
            onChange={(v) => setData({ ...data, timezone: v || data.timezone })}
            data={[
              { value: "America/Los_Angeles", label: "🌴 Pacific Time (PT)" },
              { value: "America/Denver", label: "🏔️ Mountain Time (MT)" },
              { value: "America/Chicago", label: "🌾 Central Time (CT)" },
              { value: "America/New_York", label: "🗽 Eastern Time (ET)" },
              { value: "Europe/London", label: "🇬🇧 London (GMT)" },
              { value: "Europe/Paris", label: "🇫🇷 Paris (CET)" },
              { value: "Europe/Lisbon", label: "🇵🇹 Lisbon (WET)" },
            ]}
          />
          
          <Select
            label="Locale"
            description="Language and regional format preferences"
            value={data.locale}
            onChange={(v) => setData({ ...data, locale: v || data.locale })}
            data={[
              { value: "en-US", label: "🇺🇸 English (US)" },
              { value: "en-GB", label: "🇬🇧 English (UK)" },
              { value: "pt-PT", label: "🇵🇹 Português" },
              { value: "fr-FR", label: "🇫🇷 Français" },
              { value: "es-ES", label: "🇪🇸 Español" },
            ]}
          />
        </Stack>
      </Paper>
    </Stack>
  );
}

function ClawdbotImportStep({ data, setData }: { data: SetupData; setData: (d: SetupData) => void }) {
  const [loading, setLoading] = useState(false);
  const [clawdbotPrefs, setClawdbotPrefs] = useState<any>(null);
  const [imported, setImported] = useState(false);
  
  // Detect Clawdbot on mount
  useEffect(() => {
    detectClawdbot();
  }, []);
  
  const detectClawdbot = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/clawdbot-import/detect`);
      if (res.ok) {
        const prefs = await res.json();
        setClawdbotPrefs(prefs);
      }
    } catch (e) {
      console.error("Failed to detect Clawdbot:", e);
    } finally {
      setLoading(false);
    }
  };
  
  const importPreferences = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/clawdbot-import/import`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          import_contacts: true,
          import_model: true,
          import_whatsapp: true,
        }),
      });
      
      if (res.ok) {
        const result = await res.json();
        
        // Apply imported preferences to wizard data
        if (result.imported.contacts) {
          const whatsappContacts = result.imported.contacts.map((c: any) => ({
            id: `imported_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            name: c.name,
            phone: c.phone,
          }));
          setData({ ...data, whatsappContacts });
        }
        
        if (result.imported.timezone) {
          setData({ ...data, timezone: result.imported.timezone });
        }
        
        setImported(true);
        notifications.show({
          title: "✅ Preferences Imported!",
          message: `Imported ${result.imported.contact_count || 0} contacts and settings from Clawdbot`,
          color: "green",
        });
      }
    } catch (e) {
      notifications.show({
        title: "Import Failed",
        message: "Could not import Clawdbot preferences",
        color: "red",
      });
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <Stack gap="xl" align="center">
      <Center>
        <ThemeIcon size={60} radius="xl" variant="light" color="violet">
          <IconRobot size={30} />
        </ThemeIcon>
      </Center>
      
      <div style={{ textAlign: "center" }}>
        <Title order={3}>Import from Clawdbot</Title>
        <Text c="dimmed">Bring your existing preferences and contacts</Text>
      </div>
      
      <Paper withBorder p="xl" radius="md" w="100%" maw={550}>
        {loading && !clawdbotPrefs ? (
          <Center py="xl">
            <Loader />
            <Text ml="md">Detecting Clawdbot...</Text>
          </Center>
        ) : clawdbotPrefs?.detected ? (
          <Stack gap="lg">
            <Alert icon={<IconCheck size={16} />} color="green" variant="light">
              <Text fw={500}>Clawdbot detected!</Text>
              <Text size="sm">Found configuration at {clawdbotPrefs.config_path}</Text>
            </Alert>
            
            {/* What can be imported */}
            <div>
              <Text fw={500} mb="sm">Available to import:</Text>
              <Stack gap="xs">
                {clawdbotPrefs.contacts?.length > 0 && (
                  <Group gap="xs">
                    <Badge color="blue" variant="light">
                      {clawdbotPrefs.contacts.length} Contacts
                    </Badge>
                    <Text size="xs" c="dimmed">
                      {clawdbotPrefs.contacts.slice(0, 3).map((c: any) => c.name).join(", ")}
                      {clawdbotPrefs.contacts.length > 3 && "..."}
                    </Text>
                  </Group>
                )}
                
                {clawdbotPrefs.primary_model && (
                  <Group gap="xs">
                    <Badge color="violet" variant="light">Model</Badge>
                    <Text size="xs" c="dimmed">{clawdbotPrefs.primary_model}</Text>
                  </Group>
                )}
                
                {clawdbotPrefs.whatsapp_enabled && (
                  <Group gap="xs">
                    <Badge color="green" variant="light">WhatsApp</Badge>
                    <Text size="xs" c="dimmed">
                      {clawdbotPrefs.whatsapp_allow_from?.length || 0} allowed numbers
                    </Text>
                  </Group>
                )}
                
                {clawdbotPrefs.timezone && (
                  <Group gap="xs">
                    <Badge color="orange" variant="light">Timezone</Badge>
                    <Text size="xs" c="dimmed">{clawdbotPrefs.timezone}</Text>
                  </Group>
                )}
                
                {clawdbotPrefs.enabled_skills?.length > 0 && (
                  <Group gap="xs">
                    <Badge color="cyan" variant="light">
                      {clawdbotPrefs.enabled_skills.length} Skills
                    </Badge>
                  </Group>
                )}
              </Stack>
            </div>
            
            <Divider />
            
            {imported ? (
              <Alert icon={<IconCircleCheck size={16} />} color="green">
                Preferences imported successfully! Continue to customize further.
              </Alert>
            ) : (
              <Button
                leftSection={<IconDownload size={18} />}
                onClick={importPreferences}
                loading={loading}
                fullWidth
                size="md"
              >
                Import Clawdbot Preferences
              </Button>
            )}
          </Stack>
        ) : (
          <Stack gap="md" align="center" py="md">
            <ThemeIcon size={50} radius="xl" variant="light" color="gray">
              <IconRobot size={24} />
            </ThemeIcon>
            <Text c="dimmed" ta="center">
              No Clawdbot installation detected.
              <br />
              You can configure everything manually in the next steps.
            </Text>
          </Stack>
        )}
        
        <Text size="sm" c="dimmed" ta="center" mt="md">
          You can skip this step and configure everything manually.
        </Text>
      </Paper>
    </Stack>
  );
}

function IncomeSourceStep({ data, setData }: { data: SetupData; setData: (d: SetupData) => void }) {
  return (
    <Stack gap="xl" align="center">
      <Center>
        <ThemeIcon size={60} radius="xl" variant="light" color="green">
          <IconCoin size={30} />
        </ThemeIcon>
      </Center>
      
      <div style={{ textAlign: "center" }}>
        <Title order={3}>Income Source</Title>
        <Text c="dimmed">Help us understand your financial setup</Text>
      </div>
      
      <Paper withBorder p="xl" radius="md" w="100%" maw={500}>
        <Stack gap="md">
          <TextInput
            label="Primary Income Source"
            description="Your main source of income"
            placeholder="e.g., Software Engineering, Business Owner"
            value={data.primaryIncomeSource}
            onChange={(e) => setData({ ...data, primaryIncomeSource: e.target.value })}
            required
          />
          
          <Select
            label="Income Frequency"
            value={data.incomeFrequency}
            onChange={(v) => setData({ ...data, incomeFrequency: v || "monthly" })}
            data={[
              { value: "weekly", label: "Weekly" },
              { value: "biweekly", label: "Bi-weekly" },
              { value: "monthly", label: "Monthly" },
              { value: "variable", label: "Variable/Irregular" },
            ]}
          />
        </Stack>
      </Paper>
    </Stack>
  );
}

function BudgetsStep({ data, setData }: { data: SetupData; setData: (d: SetupData) => void }) {
  return (
    <Stack gap="xl" align="center">
      <Center>
        <ThemeIcon size={60} radius="xl" variant="light" color="blue">
          <IconCoin size={30} />
        </ThemeIcon>
      </Center>
      
      <div style={{ textAlign: "center" }}>
        <Title order={3}>Budget Settings</Title>
        <Text c="dimmed">Set spending limits and preferences</Text>
      </div>
      
      <Paper withBorder p="xl" radius="md" w="100%" maw={500}>
        <Stack gap="md">
          <NumberInput
            label="Monthly Budget"
            description="Total household budget per month"
            value={data.monthlyBudget}
            onChange={(v) => setData({ ...data, monthlyBudget: Number(v) || 0 })}
            min={0}
            prefix="$"
            thousandSeparator
          />
          
          <NumberInput
            label="System Cost Cap"
            description="Max monthly spend on model operations"
            value={data.systemCostCap}
            onChange={(v) => setData({ ...data, systemCostCap: Number(v) || 0 })}
            min={0}
            prefix="$"
          />
          
          <NumberInput
            label="Approval Threshold"
            description="Expenses above this require your approval"
            value={data.approvalThreshold}
            onChange={(v) => setData({ ...data, approvalThreshold: Number(v) || 0 })}
            min={0}
            prefix="$"
          />
          
          <Select
            label="Investment Style"
            value={data.investmentStyle}
            onChange={(v) => setData({ ...data, investmentStyle: v || "moderate" })}
            data={[
              { value: "conservative", label: "🛡️ Conservative" },
              { value: "moderate", label: "⚖️ Moderate" },
              { value: "aggressive", label: "🚀 Aggressive" },
            ]}
          />
        </Stack>
      </Paper>
    </Stack>
  );
}

function ContractorsStep({ data, setData }: { data: SetupData; setData: (d: SetupData) => void }) {
  const [newName, setNewName] = useState("");
  const [newPhone, setNewPhone] = useState("");
  const [newSpecialty, setNewSpecialty] = useState("general");
  
  const addContractor = () => {
    if (!newName.trim() || !newPhone.trim()) return;
    
    const contractor: Contractor = {
      id: `c_${Date.now()}`,
      name: newName.trim(),
      phone: newPhone.trim(),
      specialty: newSpecialty,
    };
    
    setData({ ...data, contractors: [...data.contractors, contractor] });
    setNewName("");
    setNewPhone("");
    setNewSpecialty("general");
  };
  
  const removeContractor = (id: string) => {
    setData({ ...data, contractors: data.contractors.filter(c => c.id !== id) });
  };
  
  return (
    <Stack gap="xl" align="center">
      <Center>
        <ThemeIcon size={60} radius="xl" variant="light" color="orange">
          <IconTool size={30} />
        </ThemeIcon>
      </Center>
      
      <div style={{ textAlign: "center" }}>
        <Title order={3}>Your Contractors</Title>
        <Text c="dimmed">Add service providers you work with</Text>
      </div>
      
      <Paper withBorder p="xl" radius="md" w="100%" maw={550}>
        <Stack gap="md">
          {/* Add new contractor form */}
          <SimpleGrid cols={2}>
            <TextInput
              placeholder="Name (e.g., Juan)"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              leftSection={<IconUsers size={16} />}
            />
            <TextInput
              placeholder="Phone (+1...)"
              value={newPhone}
              onChange={(e) => setNewPhone(e.target.value)}
              leftSection={<IconPhone size={16} />}
            />
          </SimpleGrid>
          
          <Group>
            <Select
              placeholder="Specialty"
              value={newSpecialty}
              onChange={(v) => setNewSpecialty(v || "general")}
              data={[
                { value: "general", label: "🔧 General Handyman" },
                { value: "plumber", label: "🚿 Plumber" },
                { value: "electrician", label: "⚡ Electrician" },
                { value: "hvac", label: "❄️ HVAC" },
                { value: "landscaper", label: "🌳 Landscaper" },
                { value: "cleaner", label: "🧹 Cleaner" },
                { value: "painter", label: "🎨 Painter" },
                { value: "roofer", label: "🏠 Roofer" },
              ]}
              style={{ flex: 1 }}
            />
            <Button onClick={addContractor} leftSection={<IconPlus size={16} />}>
              Add
            </Button>
          </Group>
          
          <Divider label="Your contractors" labelPosition="center" />
          
          {data.contractors.length === 0 ? (
            <Text c="dimmed" ta="center" py="md">
              No contractors added yet. You can add them later in Settings.
            </Text>
          ) : (
            <Stack gap="xs">
              {data.contractors.map((contractor) => (
                <Paper key={contractor.id} withBorder p="sm" radius="sm">
                  <Group justify="space-between">
                    <div>
                      <Text fw={500}>{contractor.name}</Text>
                      <Group gap="xs">
                        <Badge size="xs" variant="light">{contractor.specialty}</Badge>
                        <Text size="xs" c="dimmed">{contractor.phone}</Text>
                      </Group>
                    </div>
                    <ActionIcon 
                      color="red" 
                      variant="subtle" 
                      onClick={() => removeContractor(contractor.id)}
                    >
                      <IconTrash size={16} />
                    </ActionIcon>
                  </Group>
                </Paper>
              ))}
            </Stack>
          )}
        </Stack>
      </Paper>
    </Stack>
  );
}

function WhatsAppStep({ data, setData }: { data: SetupData; setData: (d: SetupData) => void }) {
  const [newName, setNewName] = useState("");
  const [newPhone, setNewPhone] = useState("");
  const [qrLoading, setQrLoading] = useState(false);
  const [qrCode, setQrCode] = useState<string | null>(null);
  
  const addContact = () => {
    if (!newName.trim() || !newPhone.trim()) return;
    
    const contact: WhatsAppContact = {
      id: `wa_${Date.now()}`,
      name: newName.trim(),
      phone: newPhone.trim(),
    };
    
    setData({ ...data, whatsappContacts: [...data.whatsappContacts, contact] });
    setNewName("");
    setNewPhone("");
  };
  
  const removeContact = (id: string) => {
    setData({ ...data, whatsappContacts: data.whatsappContacts.filter(c => c.id !== id) });
  };
  
  const [qrError, setQrError] = useState<string | null>(null);
  const [alreadyConnected, setAlreadyConnected] = useState(false);
  const [manualSetupNeeded, setManualSetupNeeded] = useState(false);
  const [setupInstructions, setSetupInstructions] = useState<string[]>([]);
  
  const generateQR = async () => {
    setQrLoading(true);
    setQrError(null);
    setManualSetupNeeded(false);
    try {
      const res = await fetch(`${API_URL}/api/connectors/whatsapp/qr`);
      const result = await res.json();
      
      if (result.already_connected) {
        setAlreadyConnected(true);
        setData({ ...data, whatsappLinked: true });
        notifications.show({
          title: "WhatsApp Connected",
          message: `Already linked to ${result.phone || 'your phone'}`,
          color: "green",
        });
      } else if (result.success && result.qr_code) {
        setQrCode(result.qr_code);
      } else if (result.needs_manual_setup) {
        setManualSetupNeeded(true);
        setSetupInstructions(result.instructions || []);
      } else {
        const errorMsg = typeof result.error === 'string' 
          ? result.error 
          : result.error?.message || result.message || result.hint || "Failed to generate QR";
        setQrError(errorMsg);
      }
    } catch (e: any) {
      console.error("QR generation failed:", e);
      setQrError(e?.message || "Backend offline - start MyCasa backend first");
    } finally {
      setQrLoading(false);
    }
  };
  
  // Check status on mount
  useEffect(() => {
    const checkStatus = async () => {
      try {
        const res = await fetch(`${API_URL}/api/connectors/whatsapp/status`);
        const result = await res.json();
        if (result.connected) {
          setAlreadyConnected(true);
          setData({ ...data, whatsappLinked: true });
        }
      } catch (e) {
        // Backend offline, ignore
      }
    };
    checkStatus();
  }, []);
  
  return (
    <Stack gap="xl" align="center">
      <Center>
        <ThemeIcon size={60} radius="xl" variant="light" color="green">
          <IconBrandWhatsapp size={30} />
        </ThemeIcon>
      </Center>
      
      <div style={{ textAlign: "center" }}>
        <Title order={3}>WhatsApp Setup</Title>
        <Text c="dimmed">Connect WhatsApp and add trusted contacts</Text>
      </div>
      
      <SimpleGrid cols={2} w="100%" maw={700} spacing="md">
        {/* Left: QR Code */}
        <Paper withBorder p="lg" radius="md">
          <Stack align="center" gap="md">
            <Text fw={500}>Link WhatsApp</Text>
            <Text size="sm" c="dimmed" ta="center">
              Scan this QR code with WhatsApp to sync messages
            </Text>
            
            {alreadyConnected ? (
              <Paper 
                withBorder 
                p="xl" 
                radius="md" 
                style={{ width: 200, height: 200, display: "flex", alignItems: "center", justifyContent: "center", background: "var(--mantine-color-green-light)" }}
              >
                <Stack align="center" gap="xs">
                  <IconCircleCheck size={48} color="var(--mantine-color-green-filled)" />
                  <Text size="sm" fw={500} c="green">Connected!</Text>
                </Stack>
              </Paper>
            ) : manualSetupNeeded ? (
              <Paper 
                withBorder 
                p="md" 
                radius="md" 
                style={{ width: 220 }}
              >
                <Stack gap="xs">
                  <Group gap="xs">
                    <IconTerminal2 size={18} />
                    <Text size="sm" fw={500}>Terminal Setup Required</Text>
                  </Group>
                  <Stack gap={4}>
                    {setupInstructions.map((instruction, i) => (
                      <Text key={i} size="xs" c="dimmed">{instruction}</Text>
                    ))}
                  </Stack>
                  <Code block style={{ fontSize: 10 }}>npm install -g @nicholasoxford/wacli</Code>
                  <Code block style={{ fontSize: 11 }}>wacli auth</Code>
                </Stack>
              </Paper>
            ) : qrCode ? (
              <Box 
                p="sm" 
                bg="white" 
                style={{ borderRadius: 8, maxWidth: 220, overflow: "auto" }}
              >
                <Code block style={{ whiteSpace: "pre", fontSize: 5, lineHeight: 0.9, color: "#000" }}>
                  {qrCode}
                </Code>
              </Box>
            ) : (
              <Paper 
                withBorder 
                p="xl" 
                radius="md" 
                style={{ width: 200, height: 200, display: "flex", alignItems: "center", justifyContent: "center", cursor: qrLoading ? "wait" : "pointer" }}
                onClick={!qrLoading ? generateQR : undefined}
              >
                {qrLoading ? (
                  <Stack align="center" gap="xs">
                    <Loader />
                    <Text size="xs" c="dimmed">Checking...</Text>
                  </Stack>
                ) : qrError ? (
                  <Stack align="center" gap="xs">
                    <IconAlertCircle size={48} color="var(--mantine-color-red-filled)" />
                    <Text size="xs" c="red" ta="center">{qrError}</Text>
                  </Stack>
                ) : (
                  <Stack align="center" gap="xs">
                    <IconQrcode size={48} color="gray" />
                    <Text size="xs" c="dimmed">Click to check status</Text>
                  </Stack>
                )}
              </Paper>
            )}
            
            {!alreadyConnected && (
              <Button 
                variant="light" 
                onClick={generateQR} 
                loading={qrLoading}
                leftSection={manualSetupNeeded ? <IconRefresh size={16} /> : <IconQrcode size={16} />}
              >
                {manualSetupNeeded ? "Check Again" : "Check WhatsApp Status"}
              </Button>
            )}
            
            <Switch
              label="WhatsApp linked"
              checked={data.whatsappLinked}
              onChange={(e) => setData({ ...data, whatsappLinked: e.currentTarget.checked })}
            />
          </Stack>
        </Paper>
        
        {/* Right: Contact whitelist */}
        <Paper withBorder p="lg" radius="md">
          <Stack gap="md">
            <Text fw={500}>Trusted Contacts</Text>
            <Text size="sm" c="dimmed">
              Only these contacts can interact with your system
            </Text>
            
            <Group>
              <TextInput
                placeholder="Name"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                style={{ flex: 1 }}
                size="xs"
              />
              <TextInput
                placeholder="+1234567890"
                value={newPhone}
                onChange={(e) => setNewPhone(e.target.value)}
                style={{ flex: 1 }}
                size="xs"
              />
              <ActionIcon onClick={addContact} variant="light" color="green">
                <IconUserPlus size={16} />
              </ActionIcon>
            </Group>
            
            <Box style={{ maxHeight: 150, overflowY: "auto" }}>
              {data.whatsappContacts.length === 0 ? (
                <Text size="sm" c="dimmed" ta="center" py="sm">
                  No contacts added
                </Text>
              ) : (
                <Stack gap={4}>
                  {data.whatsappContacts.map((contact) => (
                    <Group key={contact.id} justify="space-between" p={4}>
                      <div>
                        <Text size="sm" fw={500}>{contact.name}</Text>
                        <Text size="xs" c="dimmed">{contact.phone}</Text>
                      </div>
                      <ActionIcon 
                        size="sm" 
                        color="red" 
                        variant="subtle"
                        onClick={() => removeContact(contact.id)}
                      >
                        <IconTrash size={14} />
                      </ActionIcon>
                    </Group>
                  ))}
                </Stack>
              )}
            </Box>
          </Stack>
        </Paper>
      </SimpleGrid>
    </Stack>
  );
}

function GoogleAuthStep({ data, setData }: { data: SetupData; setData: (d: SetupData) => void }) {
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<{
    credentials_exist: boolean;
    accounts: string[];
    auth_status: string;
  } | null>(null);
  const [authUrl, setAuthUrl] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  
  // Check Google status on mount
  useEffect(() => {
    checkStatus();
  }, []);
  
  const checkStatus = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/google/status`);
      if (res.ok) {
        const result = await res.json();
        setStatus(result);
        setData({
          ...data,
          googleCredentialsConfigured: result.credentials_exist,
          googleAuthenticated: result.auth_status === "authenticated",
          googleAccountEmail: result.accounts?.[0] || data.googleAccountEmail,
        });
      }
    } catch (e) {
      console.error("Failed to check Google status:", e);
    } finally {
      setLoading(false);
    }
  };
  
  const handleFileUpload = async (file: File | null) => {
    if (!file) return;
    setUploadError(null);
    setLoading(true);
    
    try {
      const formData = new FormData();
      formData.append("file", file);
      
      const res = await fetch(`${API_URL}/api/google/credentials/upload`, {
        method: "POST",
        body: formData,
      });
      
      const result = await res.json();
      
      if (res.ok && result.success) {
        notifications.show({
          title: "✅ Credentials Uploaded",
          message: "Google OAuth credentials configured successfully",
          color: "green",
        });
        await checkStatus();
      } else {
        setUploadError(result.detail || "Upload failed");
      }
    } catch (e) {
      setUploadError("Failed to upload credentials file");
    } finally {
      setLoading(false);
    }
  };
  
  const startAuth = async () => {
    if (!data.googleAccountEmail) {
      notifications.show({
        title: "Email Required",
        message: "Please enter your Google account email",
        color: "orange",
      });
      return;
    }
    
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/google/auth/add`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: data.googleAccountEmail }),
      });
      
      const result = await res.json();
      
      if (result.auth_url) {
        setAuthUrl(result.auth_url);
        // Open in new tab
        window.open(result.auth_url, "_blank");
      } else if (result.success && !result.needs_browser) {
        notifications.show({
          title: "✅ Already Authenticated",
          message: result.message,
          color: "green",
        });
        await checkStatus();
      }
    } catch (e) {
      notifications.show({
        title: "Auth Error",
        message: "Failed to start authentication",
        color: "red",
      });
    } finally {
      setLoading(false);
    }
  };
  
  const verifyAuth = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/google/auth/verify?email=${encodeURIComponent(data.googleAccountEmail)}`);
      const result = await res.json();
      
      if (result.authenticated) {
        setData({ ...data, googleAuthenticated: true });
        notifications.show({
          title: "✅ Verified!",
          message: `Connected to ${result.email}`,
          color: "green",
        });
        setAuthUrl(null);
        await checkStatus();
      } else {
        notifications.show({
          title: "Not Verified",
          message: "Please complete the browser authentication first",
          color: "orange",
        });
      }
    } catch (e) {
      notifications.show({
        title: "Verification Error",
        message: "Could not verify authentication",
        color: "red",
      });
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <Stack gap="xl" align="center">
      <Center>
        <ThemeIcon size={60} radius="xl" variant="light" color="red">
          <IconBrandGoogle size={30} />
        </ThemeIcon>
      </Center>
      
      <div style={{ textAlign: "center" }}>
        <Title order={3}>Google Services Setup</Title>
        <Text c="dimmed">Connect Gmail, Calendar, and more via gog</Text>
      </div>
      
      <Paper withBorder p="xl" radius="md" w="100%" maw={550}>
        <Stack gap="lg">
          {/* Step 1: Credentials */}
          <Card withBorder padding="md" radius="md">
            <Group justify="space-between" mb="sm">
              <Group>
                <ThemeIcon 
                  size="lg" 
                  variant="light" 
                  color={status?.credentials_exist ? "green" : "gray"}
                >
                  {status?.credentials_exist ? <IconCheck size={20} /> : <IconUpload size={20} />}
                </ThemeIcon>
                <div>
                  <Text fw={500}>1. OAuth Credentials</Text>
                  <Text size="xs" c="dimmed">
                    {status?.credentials_exist 
                      ? "Credentials configured ✓" 
                      : "Upload credentials.json from Google Cloud Console"}
                  </Text>
                </div>
              </Group>
              {status?.credentials_exist && (
                <Badge color="green" variant="light">Configured</Badge>
              )}
            </Group>
            
            {!status?.credentials_exist && (
              <Stack gap="sm">
                <Alert icon={<IconAlertCircle size={16} />} color="blue" variant="light">
                  <Text size="sm">
                    To use Google services, you need OAuth credentials:
                  </Text>
                  <ol style={{ margin: "8px 0", paddingLeft: "20px", fontSize: "0.875rem" }}>
                    <li>Go to <a href="https://console.cloud.google.com/apis/credentials" target="_blank" rel="noopener noreferrer">Google Cloud Console</a></li>
                    <li>Create an OAuth 2.0 Client ID (Desktop app)</li>
                    <li>Download the credentials.json file</li>
                    <li>Upload it below</li>
                  </ol>
                </Alert>
                
                <Group>
                  <Button
                    variant="light"
                    leftSection={<IconExternalLink size={16} />}
                    component="a"
                    href="https://console.cloud.google.com/apis/credentials"
                    target="_blank"
                  >
                    Open Cloud Console
                  </Button>
                  
                  <input
                    type="file"
                    id="credentials-upload"
                    accept=".json"
                    style={{ display: "none" }}
                    onChange={(e) => handleFileUpload(e.target.files?.[0] || null)}
                  />
                  <Button
                    variant="filled"
                    leftSection={<IconUpload size={16} />}
                    onClick={() => document.getElementById("credentials-upload")?.click()}
                    loading={loading}
                  >
                    Upload credentials.json
                  </Button>
                </Group>
                
                {uploadError && (
                  <Alert color="red" variant="light">
                    {uploadError}
                  </Alert>
                )}
              </Stack>
            )}
          </Card>
          
          {/* Step 2: Authenticate Account */}
          <Card withBorder padding="md" radius="md" style={{ opacity: status?.credentials_exist ? 1 : 0.5 }}>
            <Group justify="space-between" mb="sm">
              <Group>
                <ThemeIcon 
                  size="lg" 
                  variant="light" 
                  color={data.googleAuthenticated ? "green" : "gray"}
                >
                  {data.googleAuthenticated ? <IconCheck size={20} /> : <IconMail size={20} />}
                </ThemeIcon>
                <div>
                  <Text fw={500}>2. Authenticate Account</Text>
                  <Text size="xs" c="dimmed">
                    {data.googleAuthenticated 
                      ? `Connected as ${data.googleAccountEmail}` 
                      : "Sign in with your Google account"}
                  </Text>
                </div>
              </Group>
              {data.googleAuthenticated && (
                <Badge color="green" variant="light">Connected</Badge>
              )}
            </Group>
            
            {status?.credentials_exist && !data.googleAuthenticated && (
              <Stack gap="sm">
                <TextInput
                  placeholder="your@gmail.com"
                  value={data.googleAccountEmail}
                  onChange={(e) => setData({ ...data, googleAccountEmail: e.target.value })}
                  leftSection={<IconMail size={16} />}
                  disabled={!status?.credentials_exist}
                />
                
                <Group>
                  <Button
                    variant="filled"
                    color="red"
                    leftSection={<IconBrandGoogle size={16} />}
                    onClick={startAuth}
                    loading={loading}
                    disabled={!data.googleAccountEmail}
                  >
                    Sign in with Google
                  </Button>
                  
                  {authUrl && (
                    <Button
                      variant="light"
                      leftSection={<IconRefresh size={16} />}
                      onClick={verifyAuth}
                      loading={loading}
                    >
                      I've completed sign-in
                    </Button>
                  )}
                </Group>
                
                {authUrl && (
                  <Alert color="blue" variant="light">
                    <Text size="sm">
                      Complete the sign-in in your browser, then click "I've completed sign-in" above.
                    </Text>
                  </Alert>
                )}
              </Stack>
            )}
            
            {data.googleAuthenticated && (
              <Group gap="xs">
                <Badge variant="dot" color="green">Gmail</Badge>
                <Badge variant="dot" color="blue">Calendar</Badge>
                <Badge variant="dot" color="yellow">Drive</Badge>
                <Badge variant="dot" color="violet">Contacts</Badge>
              </Group>
            )}
          </Card>
          
          {/* Skip option */}
          <Text size="sm" c="dimmed" ta="center">
            You can skip this step and configure Google services later in Settings.
          </Text>
        </Stack>
      </Paper>
    </Stack>
  );
}

function ConnectorsStep({ data, setData }: { data: SetupData; setData: (d: SetupData) => void }) {
  return (
    <Stack gap="xl" align="center">
      <Center>
        <ThemeIcon size={60} radius="xl" variant="light" color="blue">
          <IconMail size={30} />
        </ThemeIcon>
      </Center>
      
      <div style={{ textAlign: "center" }}>
        <Title order={3}>Connect Services</Title>
        <Text c="dimmed">Enable integrations (can configure later)</Text>
      </div>
      
      <Paper withBorder p="xl" radius="md" w="100%" maw={500}>
        <Stack gap="lg">
          <Card withBorder padding="md" radius="md">
            <Group justify="space-between">
              <Group>
                <ThemeIcon size="lg" variant="light" color="red">
                  <IconMail size={20} />
                </ThemeIcon>
                <div>
                  <Text fw={500}>Gmail</Text>
                  <Text size="xs" c="dimmed">Sync emails and send messages</Text>
                </div>
              </Group>
              <Switch
                checked={data.enableGmail}
                onChange={(e) => setData({ ...data, enableGmail: e.currentTarget.checked })}
              />
            </Group>
            {data.enableGmail && (
              <TextInput
                mt="sm"
                placeholder="your@gmail.com"
                value={data.gmailAccount}
                onChange={(e) => setData({ ...data, gmailAccount: e.target.value })}
                leftSection={<IconMail size={16} />}
              />
            )}
          </Card>
          
          <Card withBorder padding="md" radius="md">
            <Group justify="space-between">
              <Group>
                <ThemeIcon size="lg" variant="light" color="blue">
                  <IconCalendar size={20} />
                </ThemeIcon>
                <div>
                  <Text fw={500}>Google Calendar</Text>
                  <Text size="xs" c="dimmed">Manage events and scheduling</Text>
                </div>
              </Group>
              <Switch
                checked={data.enableCalendar}
                onChange={(e) => setData({ ...data, enableCalendar: e.currentTarget.checked })}
              />
            </Group>
          </Card>
        </Stack>
      </Paper>
    </Stack>
  );
}

function NotificationsStep({ data, setData }: { data: SetupData; setData: (d: SetupData) => void }) {
  return (
    <Stack gap="xl" align="center">
      <Center>
        <ThemeIcon size={60} radius="xl" variant="light" color="violet">
          <IconBell size={30} />
        </ThemeIcon>
      </Center>
      
      <div style={{ textAlign: "center" }}>
        <Title order={3}>Notifications</Title>
        <Text c="dimmed">How should we alert you?</Text>
      </div>
      
      <Paper withBorder p="xl" radius="md" w="100%" maw={500}>
        <Stack gap="md">
          <Switch
            label="In-app notifications"
            description="Show alerts within the app"
            checked={data.enableInApp}
            onChange={(e) => setData({ ...data, enableInApp: e.currentTarget.checked })}
          />
          
          <Switch
            label="Push notifications"
            description="Browser push notifications"
            checked={data.enablePush}
            onChange={(e) => setData({ ...data, enablePush: e.currentTarget.checked })}
          />
          
          <Switch
            label="Email alerts"
            description="Send important alerts via email"
            checked={data.enableEmail}
            onChange={(e) => setData({ ...data, enableEmail: e.currentTarget.checked })}
          />
          
          {data.enableEmail && (
            <TextInput
              label="Alert Email"
              placeholder="alerts@example.com"
              value={data.alertEmail}
              onChange={(e) => setData({ ...data, alertEmail: e.target.value })}
              leftSection={<IconMail size={16} />}
            />
          )}
        </Stack>
      </Paper>
    </Stack>
  );
}

function LaunchStep({ data, onLaunch, launching }: { data: SetupData; onLaunch: () => void; launching: boolean }) {
  const [countdown, setCountdown] = useState<number | null>(null);
  const [launched, setLaunched] = useState(false);
  
  const handleLaunch = () => {
    setCountdown(3);
  };
  
  useEffect(() => {
    if (countdown === null) return;
    
    if (countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
      return () => clearTimeout(timer);
    } else if (countdown === 0) {
      setLaunched(true);
      setTimeout(() => onLaunch(), 1500);
    }
  }, [countdown, onLaunch]);
  
  if (launched) {
    return (
      <Stack gap="xl" align="center" py="xl">
        <Box
          style={{
            animation: "rocketLaunch 1.5s ease-out forwards",
          }}
        >
          <ThemeIcon 
            size={100} 
            radius="xl" 
            variant="gradient" 
            gradient={{ from: "orange", to: "red" }}
          >
            <IconRocket size={50} />
          </ThemeIcon>
        </Box>
        <Title order={2} style={{ animation: "fadeIn 0.5s ease-out" }}>
          🎉 Launching MyCasa Pro!
        </Title>
        <style>{`
          @keyframes rocketLaunch {
            0% { transform: translateY(0) scale(1); opacity: 1; }
            100% { transform: translateY(-100px) scale(0.5); opacity: 0; }
          }
          @keyframes fadeIn {
            0% { opacity: 0; transform: translateY(20px); }
            100% { opacity: 1; transform: translateY(0); }
          }
        `}</style>
      </Stack>
    );
  }
  
  if (countdown !== null) {
    return (
      <Stack gap="xl" align="center" py="xl">
        <ThemeIcon 
          size={120} 
          radius="xl" 
          variant="gradient" 
          gradient={{ from: "indigo", to: "violet" }}
          style={{ animation: "pulse 1s infinite" }}
        >
          <Text size="3rem" fw={700} c="white">{countdown}</Text>
        </ThemeIcon>
        <Title order={2}>Get Ready...</Title>
        <style>{`
          @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.1); }
          }
        `}</style>
      </Stack>
    );
  }
  
  return (
    <Stack gap="xl" align="center">
      <Center>
        <ThemeIcon size={80} radius="xl" variant="gradient" gradient={{ from: "teal", to: "green" }}>
          <IconCircleCheck size={40} />
        </ThemeIcon>
      </Center>
      
      <div style={{ textAlign: "center" }}>
        <Title order={2}>Ready to Launch!</Title>
        <Text size="lg" c="dimmed" mt="xs">Here's your setup summary</Text>
      </div>
      
      <Paper withBorder p="xl" radius="md" w="100%" maw={500}>
        <Stack gap="sm">
          <Group justify="space-between">
            <Text c="dimmed">Household</Text>
            <Text fw={500}>{data.householdName || "Not set"}</Text>
          </Group>
          
          <Group justify="space-between">
            <Text c="dimmed">Monthly Budget</Text>
            <Text fw={500}>${data.monthlyBudget.toLocaleString()}</Text>
          </Group>
          
          <Group justify="space-between">
            <Text c="dimmed">Contractors</Text>
            <Badge>{data.contractors.length} added</Badge>
          </Group>
          
          <Group justify="space-between">
            <Text c="dimmed">WhatsApp Contacts</Text>
            <Badge>{data.whatsappContacts.length} whitelisted</Badge>
          </Group>
          
          <Group justify="space-between">
            <Text c="dimmed">WhatsApp</Text>
            <Badge color={data.whatsappLinked ? "green" : "gray"}>
              {data.whatsappLinked ? "Linked" : "Not linked"}
            </Badge>
          </Group>
          
          <Group justify="space-between">
            <Text c="dimmed">Google Services</Text>
            <Badge color={data.googleAuthenticated ? "green" : "gray"}>
              {data.googleAuthenticated ? `Connected (${data.googleAccountEmail})` : "Not connected"}
            </Badge>
          </Group>
        </Stack>
      </Paper>
      
      <Button
        size="xl"
        variant="gradient"
        gradient={{ from: "indigo", to: "violet" }}
        leftSection={<IconRocket size={24} />}
        onClick={handleLaunch}
        loading={launching}
        style={{ 
          paddingLeft: 40, 
          paddingRight: 40,
          boxShadow: "0 4px 20px rgba(99, 102, 241, 0.4)",
        }}
      >
        Launch MyCasa Pro
      </Button>
    </Stack>
  );
}

// ============ MAIN WIZARD ============

interface SetupWizardProps {
  opened: boolean;
  onClose: () => void;
  onComplete: (data: SetupData) => void;
  canSkip?: boolean;
}

export function SetupWizard({ opened, onClose, onComplete, canSkip = true }: SetupWizardProps) {
  const [active, setActive] = useState(0);
  const [data, setData] = useState<SetupData>(defaultSetupData);
  const [saving, setSaving] = useState(false);
  const [progressLoaded, setProgressLoaded] = useState(false);
  
  // Load saved progress on mount
  useEffect(() => {
    if (opened && !progressLoaded) {
      try {
        const savedStep = localStorage.getItem("mycasa_wizard_step");
        const savedData = localStorage.getItem("mycasa_wizard_data");
        
        if (savedStep) {
          const step = parseInt(savedStep, 10);
          if (!isNaN(step) && step >= 0 && step < 10) {
            setActive(step);
          }
        }
        
        if (savedData) {
          const parsed = JSON.parse(savedData);
          setData({ ...defaultSetupData, ...parsed });
        }
        
        setProgressLoaded(true);
      } catch (e) {
        console.error("Failed to load wizard progress:", e);
        setProgressLoaded(true);
      }
    }
  }, [opened, progressLoaded]);
  
  // Save progress whenever step or data changes
  useEffect(() => {
    if (progressLoaded && opened) {
      try {
        localStorage.setItem("mycasa_wizard_step", String(active));
        localStorage.setItem("mycasa_wizard_data", JSON.stringify(data));
      } catch (e) {
        console.error("Failed to save wizard progress:", e);
      }
    }
  }, [active, data, progressLoaded, opened]);
  
  // Clear progress on complete
  const clearProgress = () => {
    localStorage.removeItem("mycasa_wizard_step");
    localStorage.removeItem("mycasa_wizard_data");
  };
  
  // Log when wizard opens
  useEffect(() => {
    if (opened) {
      logToJanitor("setup_wizard_opened", "User started setup wizard");
      notifyManager("📋 User is starting the setup wizard. Manager and Janitor are now active.");
    }
  }, [opened]);
  
  const steps = [
    { label: "Welcome", icon: IconHome },
    { label: "Import", icon: IconDownload },
    { label: "Income", icon: IconCoin },
    { label: "Budgets", icon: IconCoin },
    { label: "Contractors", icon: IconTool },
    { label: "WhatsApp", icon: IconBrandWhatsapp },
    { label: "Google", icon: IconBrandGoogle },
    { label: "Connectors", icon: IconMail },
    { label: "Notifications", icon: IconBell },
    { label: "Launch", icon: IconRocket },
  ];
  
  const totalSteps = steps.length;
  const progress = ((active + 1) / totalSteps) * 100;
  
  const stepNames = [
    "Welcome", "Import", "Income Source", "Budgets", 
    "Contractors", "WhatsApp", "Google Auth", "Connectors", 
    "Notifications", "Launch"
  ];

  const nextStep = () => {
    const next = Math.min(active + 1, totalSteps - 1);
    setActive(next);
    logToJanitor("setup_step_completed", `Completed: ${stepNames[active]} → ${stepNames[next]}`);
  };
  
  const prevStep = () => setActive((prev) => Math.max(prev - 1, 0));
  
  const handleFinish = async () => {
    setSaving(true);
    
    // Log to Janitor
    logToJanitor("setup_completed", `Setup completed with: ${data.householdName || 'default'} household`);
    
    // Notify Manager
    notifyManager(`🚀 Setup completed! ${data.householdName || 'MyCasa'} is ready. Budget: $${data.monthlyBudget}/mo`);
    
    try {
      await fetch(`${API_URL}/api/settings/wizard`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      
      // Clear wizard progress
      clearProgress();
      
      localStorage.setItem("mycasa_setup_complete", "true");
      localStorage.removeItem("mycasa_setup_skipped"); // Clear skipped flag on proper completion
      localStorage.setItem("mycasa_setup_data", JSON.stringify(data));
      
      // Also mark complete on backend
      try {
        await fetch(`${API_URL}/api/settings/wizard/complete`, { method: "POST" });
      } catch (e) {
        console.warn("Failed to mark wizard complete on backend:", e);
      }
      
      notifications.show({
        title: "🚀 MyCasa Pro Launched!",
        message: "Your home system is ready",
        color: "green",
        autoClose: 3000,
      });
      
      onComplete(data);
    } catch (e) {
      clearProgress();
      localStorage.setItem("mycasa_setup_complete", "true");
      localStorage.removeItem("mycasa_setup_skipped"); // Clear skipped flag on proper completion
      onComplete(data);
    } finally {
      setSaving(false);
    }
  };
  
  const handleSkip = () => {
    // Log skip to Janitor
    logToJanitor("setup_skipped", "User skipped setup wizard");
    notifyManager("⚠️ Setup was skipped. Reminder: Complete setup for best experience.");
    
    // Keep wizard progress so they can resume later
    // Don't clear progress here
    
    localStorage.setItem("mycasa_setup_complete", "true");
    localStorage.setItem("mycasa_setup_skipped", "true");
    notifications.show({
      title: "Setup Skipped",
      message: "Configure anytime in Settings",
      color: "blue",
    });
    onClose();
  };
  
  const renderStep = () => {
    switch (active) {
      case 0: return <WelcomeStep data={data} setData={setData} />;
      case 1: return <ClawdbotImportStep data={data} setData={setData} />;
      case 2: return <IncomeSourceStep data={data} setData={setData} />;
      case 3: return <BudgetsStep data={data} setData={setData} />;
      case 4: return <ContractorsStep data={data} setData={setData} />;
      case 5: return <WhatsAppStep data={data} setData={setData} />;
      case 6: return <GoogleAuthStep data={data} setData={setData} />;
      case 7: return <ConnectorsStep data={data} setData={setData} />;
      case 8: return <NotificationsStep data={data} setData={setData} />;
      case 9: return <LaunchStep data={data} onLaunch={handleFinish} launching={saving} />;
      default: return null;
    }
  };
  
  const isLastStep = active === totalSteps - 1;
  
  return (
    <Modal
      opened={opened}
      onClose={onClose}
      size="lg"
      radius="lg"
      padding={0}
      withCloseButton={false}
      closeOnClickOutside={false}
      closeOnEscape={canSkip}
      centered
    >
      <Progress value={progress} size="xs" radius={0} />
      
      <Group justify="space-between" p="md" pb={0}>
        <Group gap="xs">
          <ThemeIcon size="sm" variant="light" color="violet">
            <IconHome size={14} />
          </ThemeIcon>
          <Text size="sm" fw={500}>MyCasa Pro Setup</Text>
        </Group>
        {canSkip && (
          <Tooltip label="Skip setup">
            <ActionIcon variant="subtle" onClick={handleSkip}>
              <IconX size={18} />
            </ActionIcon>
          </Tooltip>
        )}
      </Group>
      
      <Box px="xl" pt="md">
        <Stepper active={active} size="xs" iconSize={28} allowNextStepsSelect={false}>
          {steps.map((step) => (
            <Stepper.Step key={step.label} label={step.label} icon={<step.icon size={14} />} />
          ))}
        </Stepper>
      </Box>
      
      <Box p="xl" pt="lg" pb="md" style={{ minHeight: 420 }}>
        {renderStep()}
      </Box>
      
      {!isLastStep && (
        <Group justify="space-between" p="md" pt={0}>
          <Button
            variant="subtle"
            onClick={prevStep}
            disabled={active === 0}
            leftSection={<IconArrowLeft size={16} />}
          >
            Back
          </Button>
          
          <Button onClick={nextStep} rightSection={<IconArrowRight size={16} />}>
            Continue
          </Button>
        </Group>
      )}
      
      {isLastStep && (
        <Group justify="center" p="md" pt={0}>
          <Button variant="subtle" onClick={prevStep} leftSection={<IconArrowLeft size={16} />}>
            Back
          </Button>
        </Group>
      )}
    </Modal>
  );
}

export function useSetupWizard() {
  const [needsSetup, setNeedsSetup] = useState(false);
  const [showWizard, setShowWizard] = useState(false);
  
  useEffect(() => {
    const setupComplete = localStorage.getItem("mycasa_setup_complete");
    if (!setupComplete) {
      setNeedsSetup(true);
      setShowWizard(true);
    }
  }, []);
  
  return { needsSetup, showWizard, openWizard: () => setShowWizard(true), closeWizard: () => setShowWizard(false) };
}

export default SetupWizard;
