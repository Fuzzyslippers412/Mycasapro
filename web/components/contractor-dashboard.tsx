"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useAuth } from "@/components/auth-context";
import { SiteShell } from "@/components/site-shell";
import { apiError, apiFetch, appURL } from "@/lib/api";
import type { ContractorDashboard } from "@/lib/types";

function emptyDashboard(contractorID: string): ContractorDashboard {
  return {
    contractor_user_id: contractorID,
    summary: { organization_count: 0, available_request_count: 0, active_project_count: 0, pending_quote_count: 0 },
    organizations: [],
    available_requests: [],
    active_projects: [],
  };
}

export function ContractorDashboardView() {
  const { user } = useAuth();
  const [dashboard, setDashboard] = useState<ContractorDashboard>(() => emptyDashboard(user.id));
  const [loading, setLoading] = useState(true);
  const [savingOrg, setSavingOrg] = useState(false);
  const [claimingRequestID, setClaimingRequestID] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadDashboard() {
    setLoading(true);
    setError(null);
    try {
      const response = await apiFetch(`/api/v1/contractors/${user.id}/dashboard`);
      if (!response.ok) throw new Error(await apiError(response, "Unable to load the contractor workspace"));
      setDashboard((await response.json()) as ContractorDashboard);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load the contractor workspace");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadDashboard();
  }, [user.id]);

  async function handleCreateOrganization(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    setSavingOrg(true);
    setError(null);
    try {
      const response = await apiFetch(`/api/v1/contractors/${user.id}/organizations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: formData.get("name") }),
      });
      if (!response.ok) throw new Error(await apiError(response, "Unable to create this company"));
      form.reset();
      await loadDashboard();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create this company");
    } finally {
      setSavingOrg(false);
    }
  }

  async function claimRequest(workRequestID: string) {
    const organization = dashboard.organizations[0];
    if (!organization) return;
    setClaimingRequestID(workRequestID);
    setError(null);
    try {
      const response = await apiFetch(`/api/v1/contractors/${user.id}/organizations/${organization.id}/projects`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ work_request_id: workRequestID }),
      });
      if (!response.ok) throw new Error(await apiError(response, "Unable to accept this request"));
      await loadDashboard();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to accept this request");
    } finally {
      setClaimingRequestID(null);
    }
  }

  if (loading) {
    return <SiteShell role="contractor" title={`Welcome, ${firstName(user.display_name)}`} description="Loading your work queue..."><div className="section-card skeleton-card"><div className="skeleton skeleton-title" /><div className="skeleton skeleton-block tall" /></div></SiteShell>;
  }

  if (dashboard.organizations.length === 0) {
    return (
      <SiteShell role="contractor" title={`Welcome, ${firstName(user.display_name)}`} description="Set up the company that will own estimates, jobs, and invoices.">
        <section className="onboarding-layout">
          <div className="onboarding-intro">
            <p className="kicker">Professional setup</p>
            <h2>Set up your work desk</h2>
            <p>Use the real business or working name your clients know. Your jobs, documents, and payment records will live here.</p>
            <ul className="plain-check-list"><li>Job records stay attached to the company.</li><li>Private field notes stay separate from homeowner updates.</li><li>You can invite team members later.</li></ul>
          </div>
          <form className="form-card compact-form-card" onSubmit={handleCreateOrganization}>
            <div className="form-heading"><p className="kicker">Company details</p><h3>What name should clients see?</h3></div>
            {error ? <div className="form-error" role="alert">{error}</div> : null}
            <label className="field full-field"><span>Business or team name</span><input name="name" required /></label>
            <button className="primary-button" type="submit" disabled={savingOrg}>{savingOrg ? "Creating workspace..." : "Create contractor workspace"}</button>
          </form>
        </section>
      </SiteShell>
    );
  }

  const organization = dashboard.organizations[0];
  return (
    <SiteShell role="contractor" title="Today’s work" description={organization.name}>
      {error ? <div className="form-error page-error" role="alert">{error}<button type="button" onClick={() => void loadDashboard()}>Try again</button></div> : null}
      <section className="operations-strip" id="today">
        <div><span>New requests</span><strong>{dashboard.summary.available_request_count}</strong></div>
        <div><span>Active jobs</span><strong>{dashboard.summary.active_project_count}</strong></div>
        <div><span>Quotes due</span><strong>{dashboard.summary.pending_quote_count}</strong></div>
      </section>

      <section className="contractor-grid">
        <section className="section-card" id="requests">
          <div className="section-heading-row"><div><p className="kicker">Inbox</p><h2>Requests to review</h2></div><span className="section-count">{dashboard.available_requests.length}</span></div>
          {dashboard.available_requests.length === 0 ? (
            <CompactEmpty title="Inbox clear" body="New homeowner requests will appear here when they are available." />
          ) : (
            <div className="job-list">
              {dashboard.available_requests.map((item) => (
                <article className="job-card" key={item.work_request.id}>
                  <div className="job-card-head"><div><span className={`urgency-tag urgency-${item.work_request.urgency}`}>{item.work_request.urgency}</span><h3>{item.work_request.title}</h3></div><span className="job-location">{item.property.city}, {item.property.region}</span></div>
                  <p>{item.work_request.description}</p>
                  <div className="job-meta"><span>{item.property.label}</span><span>{item.work_request.area}</span><span>{item.work_request.category}</span></div>
                  {item.work_request.attachments?.length ? <div className="job-evidence" aria-label="Homeowner attachments"><strong>Homeowner evidence</strong><div className="attachment-links">{item.work_request.attachments.map((attachment) => <a key={attachment.id} href={`${appURL}/api/v1/contractors/${user.id}/work-requests/${item.work_request.id}/attachments/${attachment.id}`} target="_blank" rel="noreferrer">{attachment.content_type.startsWith("image/") ? "Photo" : "PDF"}: {attachment.file_name}</a>)}</div></div> : null}
                  <button className="secondary-button" type="button" onClick={() => void claimRequest(item.work_request.id)} disabled={claimingRequestID === item.work_request.id}>{claimingRequestID === item.work_request.id ? "Accepting..." : "Accept into jobs"}</button>
                </article>
              ))}
            </div>
          )}
        </section>

        <section className="section-card" id="jobs">
          <div className="section-heading-row"><div><p className="kicker">Pipeline</p><h2>Active jobs</h2></div><span className="section-count">{dashboard.active_projects.length}</span></div>
          {dashboard.active_projects.length === 0 ? (
            <CompactEmpty title="No active jobs" body="Accepted requests move here with their property and homeowner context intact." />
          ) : (
            <div className="repair-list">
              {dashboard.active_projects.map((item) => (
                <Link className="repair-row" href={`/contractor/projects/${item.project.id}`} key={item.project.id}>
                  <span className="repair-marker" data-tone="active" /><span className="repair-copy"><strong>{item.project.title}</strong><small>{item.property.label} · {item.property.city}</small></span><span className={`status-badge status-${item.project.status}`}>{item.project.status.replaceAll("_", " ")}</span><span className="row-arrow">→</span>
                </Link>
              ))}
            </div>
          )}
        </section>
      </section>
    </SiteShell>
  );
}

function CompactEmpty({ title, body }: { title: string; body: string }) {
  return <div className="compact-empty"><strong>{title}</strong><p>{body}</p></div>;
}

function firstName(displayName: string) {
  return displayName.trim().split(/\s+/)[0] || "there";
}
