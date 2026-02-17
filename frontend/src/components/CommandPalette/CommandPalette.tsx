"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getApiBaseUrl } from "@/lib/api";
import { Spotlight, spotlight, SpotlightActionData } from "@mantine/spotlight";
import {
  IconDashboard,
  IconInbox,
  IconTool,
  IconCoin,
  IconUsers,
  IconFolders,
  IconShield,
  IconList,
  IconSettings,
  IconRefresh,
  IconCheck,
  IconFileExport,
  IconChartBar,
} from "@tabler/icons-react";

interface CommandPaletteProps {
  opened: boolean;
  onClose: () => void;
}

export function CommandPalette({ opened, onClose }: CommandPaletteProps) {
  const router = useRouter();
  const API_URL = getApiBaseUrl();

  // Sync external opened state with spotlight store
  useEffect(() => {
    if (opened) {
      spotlight.open();
    } else {
      spotlight.close();
    }
  }, [opened]);

  const navActions: SpotlightActionData[] = [
    {
      id: "nav-dashboard",
      label: "Go to Dashboard",
      description: "View system overview",
      onClick: () => { router.push("/"); onClose(); },
      leftSection: <IconDashboard size={20} />,
      keywords: ["home", "overview"],
    },
    {
      id: "nav-system",
      label: "Go to System Monitor",
      description: "View agent processes",
      onClick: () => { router.push("/system"); onClose(); },
      leftSection: <IconChartBar size={20} />,
      keywords: ["agents", "processes", "htop"],
    },
    {
      id: "nav-inbox",
      label: "Go to Inbox",
      description: "View messages",
      onClick: () => { router.push("/inbox"); onClose(); },
      leftSection: <IconInbox size={20} />,
      keywords: ["messages", "mail", "whatsapp"],
    },
    {
      id: "nav-maintenance",
      label: "Go to Maintenance",
      description: "View tasks",
      onClick: () => { router.push("/maintenance"); onClose(); },
      leftSection: <IconTool size={20} />,
      keywords: ["tasks", "repairs"],
    },
    {
      id: "nav-finance",
      label: "Go to Finance",
      description: "View spending and budgets",
      onClick: () => { router.push("/finance"); onClose(); },
      leftSection: <IconCoin size={20} />,
      keywords: ["money", "budget", "bills"],
    },
    {
      id: "nav-contractors",
      label: "Go to Contractors",
      description: "View vendor jobs",
      onClick: () => { router.push("/contractors"); onClose(); },
      leftSection: <IconUsers size={20} />,
      keywords: ["vendors", "jobs"],
    },
    {
      id: "nav-projects",
      label: "Go to Projects",
      description: "View home projects",
      onClick: () => { router.push("/projects"); onClose(); },
      leftSection: <IconFolders size={20} />,
      keywords: ["renovations"],
    },
    {
      id: "nav-security",
      label: "Go to Security",
      description: "View security dashboard",
      onClick: () => { router.push("/security"); onClose(); },
      leftSection: <IconShield size={20} />,
      keywords: ["safety", "incidents"],
    },
    {
      id: "nav-logs",
      label: "Go to Logs",
      description: "View system logs",
      onClick: () => { router.push("/logs"); onClose(); },
      leftSection: <IconList size={20} />,
      keywords: ["audit", "history"],
    },
    {
      id: "nav-settings",
      label: "Go to Settings",
      description: "Configure system",
      onClick: () => { router.push("/settings"); onClose(); },
      leftSection: <IconSettings size={20} />,
      keywords: ["config", "preferences"],
    },
  ];

  const systemActions: SpotlightActionData[] = [
    {
      id: "system-check",
      label: "Run System Check",
      description: "Check system health",
      onClick: async () => {
        await fetch(`${API_URL}/status`);
        onClose();
      },
      leftSection: <IconRefresh size={20} />,
      keywords: ["health", "status"],
    },
    {
      id: "backup-export",
      label: "Export Backup",
      description: "Create system backup",
      onClick: async () => {
        await fetch(`${API_URL}/backup/export`, { method: "POST" });
        onClose();
      },
      leftSection: <IconFileExport size={20} />,
      keywords: ["save", "snapshot"],
    },
    {
      id: "inbox-sync",
      label: "Sync Inbox",
      description: "Fetch new messages",
      onClick: async () => {
        await fetch(`${API_URL}/inbox/sync`, { method: "POST" });
        onClose();
      },
      leftSection: <IconRefresh size={20} />,
      keywords: ["mail", "messages", "refresh"],
    },
    {
      id: "approve-all",
      label: "View Pending Approvals",
      description: "See all approval requests",
      onClick: () => {
        router.push("/approvals");
        onClose();
      },
      leftSection: <IconCheck size={20} />,
      keywords: ["pending", "requests"],
    },
  ];

  return (
    <Spotlight
      actions={[...navActions, ...systemActions]}
      searchProps={{
        leftSection: <IconDashboard size={20} />,
        placeholder: "Search commands...",
      }}
      nothingFound="No commands found"
      highlightQuery
      onSpotlightClose={onClose}
      shortcut={["mod + K"]}
    />
  );
}
