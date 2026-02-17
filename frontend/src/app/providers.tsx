"use client";

import { ReactNode } from "react";
import { Notifications } from "@mantine/notifications";
import { AuthProvider } from "@/contexts/AuthContext";
import { AgentProvider } from "@/lib/AgentContext";

interface ProvidersProps {
  children: ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  return (
    <AuthProvider>
      <AgentProvider>
        <Notifications position="top-right" />
        {children}
      </AgentProvider>
    </AuthProvider>
  );
}
