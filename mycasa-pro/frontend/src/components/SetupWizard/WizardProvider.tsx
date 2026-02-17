"use client";

import { useEffect, useState, createContext, useContext, ReactNode } from "react";
import { getApiBaseUrl } from "@/lib/api";
import { SetupWizard } from "./SetupWizard";

interface WizardContextType {
  showWizard: boolean;
  openWizard: () => void;
  closeWizard: () => void;
  isSetupComplete: boolean;
  wasSkipped: boolean;
}

const WizardContext = createContext<WizardContextType>({
  showWizard: false,
  openWizard: () => {},
  closeWizard: () => {},
  isSetupComplete: false,
  wasSkipped: false,
});

export function useWizard() {
  return useContext(WizardContext);
}

export function WizardProvider({ children }: { children: ReactNode }) {
  const API_URL = getApiBaseUrl();
  const [showWizard, setShowWizard] = useState(false);
  const [isSetupComplete, setIsSetupComplete] = useState(true); // Default true to prevent flash
  const [wasSkipped, setWasSkipped] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    
    // Check localStorage on mount
    const setupComplete = localStorage.getItem("mycasa_setup_complete");
    const setupSkipped = localStorage.getItem("mycasa_setup_skipped");
    
    if (!setupComplete) {
      setIsSetupComplete(false);
      // Auto-show wizard after a brief delay for first-time users
      const timer = setTimeout(() => {
        setShowWizard(true);
      }, 500);
      return () => clearTimeout(timer);
    } else {
      setIsSetupComplete(true);
      // Only show as skipped if explicitly skipped AND not later completed
      // If setup is complete, the skipped flag should have been cleared
      setWasSkipped(setupSkipped === "true");
    }
    
    // Also check with backend to sync state
    const checkBackend = async () => {
      try {
        const res = await fetch(`${API_URL}/api/settings/wizard/status`);
        if (res.ok) {
          const data = await res.json();
          if (data.completed) {
            localStorage.setItem("mycasa_setup_complete", "true");
            if (!data.skipped) {
              localStorage.removeItem("mycasa_setup_skipped");
            }
            setIsSetupComplete(true);
            setWasSkipped(data.skipped || false);
          }
        }
      } catch (e) {
        // Backend offline, rely on localStorage
      }
    };
    checkBackend();
  }, []);

  const openWizard = () => setShowWizard(true);
  const closeWizard = () => setShowWizard(false);

  const handleComplete = () => {
    setShowWizard(false);
    setIsSetupComplete(true);
    setWasSkipped(false);
    // Clear skipped flag in localStorage
    localStorage.removeItem("mycasa_setup_skipped");
    localStorage.setItem("mycasa_setup_complete", "true");
    // Reload to apply settings
    window.location.reload();
  };

  // Don't render wizard until mounted (prevents hydration mismatch)
  if (!mounted) {
    return <>{children}</>;
  }

  return (
    <WizardContext.Provider value={{ showWizard, openWizard, closeWizard, isSetupComplete, wasSkipped }}>
      {children}
      <SetupWizard
        opened={showWizard}
        onClose={closeWizard}
        onComplete={handleComplete}
        canSkip={true}
      />
    </WizardContext.Provider>
  );
}

export default WizardProvider;
