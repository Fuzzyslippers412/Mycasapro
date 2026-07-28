import { AuthGate } from "@/components/auth-context";
import { ProjectWorkspaceView } from "@/components/project-workspace";
import { SiteShell } from "@/components/site-shell";

export default async function ContractorProjectPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;

  return (
    <AuthGate requiredRole="contractor">
      <SiteShell role="contractor" title="Live job workspace" description="Scope, schedule, field updates, and invoicing in one record.">
        <ProjectWorkspaceView role="contractor" projectID={projectId} />
      </SiteShell>
    </AuthGate>
  );
}
