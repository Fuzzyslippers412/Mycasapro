import { AuthGate } from "@/components/auth-context";
import { ProjectWorkspaceView } from "@/components/project-workspace";
import { SiteShell } from "@/components/site-shell";

export default async function HomeownerProjectPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;

  return (
    <AuthGate requiredRole="homeowner">
      <SiteShell role="homeowner" title="Repair workspace" description="Scope, schedule, updates, and money in one shared record.">
        <ProjectWorkspaceView role="homeowner" projectID={projectId} />
      </SiteShell>
    </AuthGate>
  );
}
