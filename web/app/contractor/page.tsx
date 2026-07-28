import { AuthGate } from "@/components/auth-context";
import { ContractorDashboardView } from "@/components/contractor-dashboard";

export default function ContractorPage() {
  return (
    <AuthGate requiredRole="contractor">
      <ContractorDashboardView />
    </AuthGate>
  );
}
