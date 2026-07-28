import { AuthGate } from "@/components/auth-context";
import { HomeownerDashboardView } from "@/components/homeowner-dashboard";

export default function HomeownerPage() {
  return (
    <AuthGate requiredRole="homeowner">
      <HomeownerDashboardView />
    </AuthGate>
  );
}
