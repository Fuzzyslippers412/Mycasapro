"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { useAuth } from "@/components/auth-context";
import { SiteShell } from "@/components/site-shell";
import { apiError, apiFetch, appURL } from "@/lib/api";
import type { GuestEstimate, HomeownerDashboard, Property, WorkRequest, WorkRequestInvite } from "@/lib/types";

const maxAttachmentBytes = 10 * 1024 * 1024;
const allowedAttachmentTypes = new Set(["image/jpeg", "image/png", "image/webp", "image/heic", "image/heif", "application/pdf"]);
const allowedAttachmentExtensions = new Set(["jpg", "jpeg", "png", "webp", "heic", "heif", "pdf"]);

function emptyDashboard(homeownerID: string): HomeownerDashboard {
  return {
    homeowner_user_id: homeownerID,
    summary: {
      property_count: 0,
      open_repair_count: 0,
      pending_approval_count: 0,
      scheduled_visit_count: 0,
      active_project_count: 0,
      outstanding_invoice_count: 0,
      requests_by_status: {},
    },
    properties: [],
    work_requests: [],
    active_projects: [],
  };
}

export function HomeownerDashboardView() {
  const { user } = useAuth();
  const [dashboard, setDashboard] = useState<HomeownerDashboard>(() => emptyDashboard(user.id));
  const [loading, setLoading] = useState(true);
  const [savingProperty, setSavingProperty] = useState(false);
  const [savingRequest, setSavingRequest] = useState(false);
  const [requestOpen, setRequestOpen] = useState(false);
  const [sharingRequest, setSharingRequest] = useState<WorkRequest | null>(null);
  const [shareResult, setShareResult] = useState<{ invite: WorkRequestInvite; share_url: string } | null>(null);
  const [invites, setInvites] = useState<WorkRequestInvite[]>([]);
  const [loadingInvites, setLoadingInvites] = useState(false);
  const [creatingInvite, setCreatingInvite] = useState(false);
  const [copiedInvite, setCopiedInvite] = useState(false);
  const [estimateRequest, setEstimateRequest] = useState<WorkRequest | null>(null);
  const [guestEstimates, setGuestEstimates] = useState<GuestEstimate[]>([]);
  const [loadingEstimates, setLoadingEstimates] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function loadDashboard() {
    setLoading(true);
    setError(null);
    try {
      const response = await apiFetch(`/api/v1/homeowners/${user.id}/dashboard`);
      if (!response.ok) throw new Error(await apiError(response, "Unable to load your home"));
      setDashboard((await response.json()) as HomeownerDashboard);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load your home");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadDashboard();
  }, [user.id]);

  const currentProperty = dashboard.properties[0];
  const propertyByID = useMemo(
    () => new Map(dashboard.properties.map((property) => [property.id, property])),
    [dashboard.properties],
  );

  async function handleCreateProperty(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    setSavingProperty(true);
    setError(null);
    try {
      const response = await apiFetch(`/api/v1/homeowners/${user.id}/properties`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          label: formData.get("label"),
          address_line_1: formData.get("address_line_1"),
          address_line_2: formData.get("address_line_2"),
          city: formData.get("city"),
          region: formData.get("region"),
          postal_code: formData.get("postal_code"),
          country_code: formData.get("country_code"),
        }),
      });
      if (!response.ok) throw new Error(await apiError(response, "Unable to save this property"));
      form.reset();
      await loadDashboard();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save this property");
    } finally {
      setSavingProperty(false);
    }
  }

  async function handleCreateWorkRequest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    const attachments = formData.getAll("attachments").filter((value): value is File => value instanceof File && value.size > 0);
    if (attachments.length > 5) {
      setError("Choose no more than five photos or documents.");
      return;
    }
    const invalidAttachment = attachments.find((file) => file.size > maxAttachmentBytes || !isAllowedAttachment(file));
    if (invalidAttachment) {
      setError(`${invalidAttachment.name} must be a JPEG, PNG, WebP, HEIC, or PDF no larger than 10 MB.`);
      return;
    }
    setSavingRequest(true);
    setError(null);
    setNotice(null);
    try {
      const response = await apiFetch(`/api/v1/homeowners/${user.id}/work-requests`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          property_id: formData.get("property_id"),
          title: formData.get("title"),
          category: formData.get("category"),
          area: formData.get("area"),
          urgency: formData.get("urgency"),
          description: formData.get("description"),
          preferred_timing: formData.get("preferred_timing"),
        }),
      });
      if (!response.ok) throw new Error(await apiError(response, "Unable to report this issue"));
      const workRequest = (await response.json()) as WorkRequest;
      for (const file of attachments) {
        const uploadBody = new FormData();
        uploadBody.append("file", file);
        const uploadResponse = await apiFetch(`/api/v1/homeowners/${user.id}/work-requests/${workRequest.id}/attachments`, {
          method: "POST",
          body: uploadBody,
        });
        if (!uploadResponse.ok) {
          throw new AttachmentUploadError(await apiError(uploadResponse, `Unable to attach ${file.name}`));
        }
      }
      form.reset();
      setRequestOpen(false);
      await loadDashboard();
    } catch (err) {
      if (err instanceof AttachmentUploadError) {
        form.reset();
        setRequestOpen(false);
        await loadDashboard();
        setNotice(`The repair request was saved, but a file could not be attached. ${err.message}`);
      } else {
        setError(err instanceof Error ? err.message : "Unable to report this issue");
      }
    } finally {
      setSavingRequest(false);
    }
  }

  async function openShareRequest(request: WorkRequest) {
    setSharingRequest(request);
    setShareResult(null);
    setCopiedInvite(false);
    setInvites([]);
    setLoadingInvites(true);
    setError(null);
    try {
      const response = await apiFetch(`/api/v1/homeowners/${user.id}/work-requests/${request.id}/invites`);
      if (!response.ok) throw new Error(await apiError(response, "Unable to load share links"));
      const payload = (await response.json()) as { invites: WorkRequestInvite[] };
      setInvites(payload.invites);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load share links");
    } finally {
      setLoadingInvites(false);
    }
  }

  async function createShareLink() {
    if (!sharingRequest) return;
    setCreatingInvite(true);
    setCopiedInvite(false);
    setError(null);
    try {
      const response = await apiFetch(`/api/v1/homeowners/${user.id}/work-requests/${sharingRequest.id}/invites`, { method: "POST" });
      if (!response.ok) throw new Error(await apiError(response, "Unable to create a share link"));
      const result = (await response.json()) as { invite: WorkRequestInvite; share_url: string };
      setShareResult(result);
      setInvites((current) => [result.invite, ...current]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create a share link");
    } finally {
      setCreatingInvite(false);
    }
  }

  async function copyShareLink() {
    if (!shareResult) return;
    try {
      await navigator.clipboard.writeText(shareResult.share_url);
      setCopiedInvite(true);
    } catch {
      setCopiedInvite(false);
    }
  }

  async function revokeInvite(inviteID: string) {
    if (!sharingRequest) return;
    setError(null);
    try {
      const response = await apiFetch(`/api/v1/homeowners/${user.id}/work-requests/${sharingRequest.id}/invites/${inviteID}/revoke`, { method: "POST" });
      if (!response.ok) throw new Error(await apiError(response, "Unable to revoke this link"));
      const revoked = (await response.json()) as WorkRequestInvite;
      setInvites((current) => current.map((invite) => invite.id === revoked.id ? revoked : invite));
      if (shareResult?.invite.id === revoked.id) setShareResult(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to revoke this link");
    }
  }

  async function openGuestEstimates(request: WorkRequest) {
    setEstimateRequest(request);
    setGuestEstimates([]);
    setLoadingEstimates(true);
    setError(null);
    try {
      const response = await apiFetch(`/api/v1/homeowners/${user.id}/work-requests/${request.id}/guest-estimates`);
      if (!response.ok) throw new Error(await apiError(response, "Unable to load estimates"));
      const payload = (await response.json()) as { estimates: GuestEstimate[] };
      setGuestEstimates(payload.estimates);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load estimates");
    } finally {
      setLoadingEstimates(false);
    }
  }

  if (loading) {
    return (
      <SiteShell role="homeowner" title={`Welcome, ${firstName(user.display_name)}`} description="Loading your home record...">
        <DashboardSkeleton />
      </SiteShell>
    );
  }

  if (dashboard.properties.length === 0) {
    return (
      <SiteShell role="homeowner" title={`Welcome, ${firstName(user.display_name)}`} description="Let’s set up the first real record for your home.">
        <section className="onboarding-layout">
          <div className="onboarding-intro">
            <p className="kicker">Your first home</p>
            <h2>Add your home</h2>
            <p>This address becomes its own private record for repairs, visits, documents, and the people you trust to care for it.</p>
            <ul className="plain-check-list">
              <li>Nothing is shared until you choose to request work.</li>
              <li>Every future repair stays with this home.</li>
              <li>You can add another property at any time.</li>
            </ul>
          </div>
          <form className="form-card" onSubmit={handleCreateProperty}>
            <div className="form-heading">
              <p className="kicker">Property details</p>
              <h3>Where do you need work managed?</h3>
            </div>
            {error ? <div className="form-error" role="alert">{error}</div> : null}
            <label className="field full-field"><span>Property name</span><input name="label" required /><small>Use a name you will recognize, such as Home or Rental.</small></label>
            <label className="field full-field"><span>Street address</span><input name="address_line_1" autoComplete="address-line1" required /></label>
            <label className="field full-field"><span>Apartment, suite, or unit <em>Optional</em></span><input name="address_line_2" autoComplete="address-line2" /></label>
            <div className="form-row three-columns">
              <label className="field"><span>City</span><input name="city" autoComplete="address-level2" required /></label>
              <label className="field"><span>State or region</span><input name="region" autoComplete="address-level1" required /></label>
              <label className="field"><span>Postal code</span><input name="postal_code" autoComplete="postal-code" required /></label>
            </div>
            <label className="field full-field"><span>Country</span><select name="country_code" defaultValue="US"><option value="US">United States</option><option value="CA">Canada</option><option value="GB">United Kingdom</option><option value="NG">Nigeria</option><option value="GH">Ghana</option><option value="KE">Kenya</option><option value="ZA">South Africa</option><option value="OTHER">Other</option></select></label>
            <button className="primary-button" type="submit" disabled={savingProperty}>{savingProperty ? "Saving your home..." : "Save and continue"}</button>
          </form>
        </section>
      </SiteShell>
    );
  }

  const attentionCount = dashboard.summary.pending_approval_count + dashboard.summary.outstanding_invoice_count;

  return (
    <SiteShell
      role="homeowner"
      title={currentProperty?.label || `Welcome back, ${firstName(user.display_name)}`}
      description={currentProperty ? formatAddress(currentProperty) : undefined}
      action={<button className="primary-button" type="button" onClick={() => setRequestOpen(true)}>Report an issue</button>}
    >
      {error ? <div className="form-error page-error" role="alert">{error}<button type="button" onClick={() => void loadDashboard()}>Try again</button></div> : null}
      {notice ? <div className="form-notice page-error" role="status"><span>{notice}</span><button type="button" onClick={() => setNotice(null)}>Dismiss</button></div> : null}

      <section className="dashboard-layout" id="overview">
        <div className="dashboard-primary">
          <section className="section-card attention-card">
            <div className="section-heading-row">
              <div><p className="kicker">Priority</p><h2>Needs your attention</h2></div>
              {attentionCount > 0 ? <span className="count-badge">{attentionCount}</span> : null}
            </div>
            {attentionCount === 0 ? (
              <div className="clear-state"><span className="clear-state-icon">✓</span><div><strong>You’re all caught up</strong><p>No estimates or invoices need a decision right now.</p></div></div>
            ) : (
              <div className="action-list">
                {dashboard.summary.pending_approval_count > 0 ? <ActionRow tone="warning" title={`${dashboard.summary.pending_approval_count} estimate${dashboard.summary.pending_approval_count === 1 ? "" : "s"} waiting`} detail="Review the scope and price before work moves forward." /> : null}
                {dashboard.summary.outstanding_invoice_count > 0 ? <ActionRow tone="urgent" title={`${dashboard.summary.outstanding_invoice_count} invoice${dashboard.summary.outstanding_invoice_count === 1 ? "" : "s"} outstanding`} detail="Open the related project to review the payment record." /> : null}
              </div>
            )}
          </section>

          <section className="section-card" id="repairs">
            <div className="section-heading-row">
              <div><p className="kicker">Work in motion</p><h2>Active repairs</h2></div>
              <span className="section-count">{dashboard.summary.open_repair_count} open</span>
            </div>
            {dashboard.active_projects.length === 0 && dashboard.work_requests.length === 0 ? (
              <CompactEmpty title="No repairs reported" body="When something needs attention, report it here and the full record starts immediately." action={<button className="secondary-button" type="button" onClick={() => setRequestOpen(true)}>Report the first issue</button>} />
            ) : (
              <div className="repair-list">
                {dashboard.active_projects.map((item) => (
                  <Link className="repair-row" href={`/homeowner/projects/${item.project.id}`} key={item.project.id}>
                    <span className="repair-marker" data-tone="active" />
                    <span className="repair-copy"><strong>{item.project.title}</strong><small>{item.property.label} · Contractor project</small></span>
                    <StatusBadge status={item.project.status} />
                    <span className="row-arrow">→</span>
                  </Link>
                ))}
                {dashboard.work_requests.filter((request) => request.status !== "converted").map((request) => (
                  <RepairRequestRow
                    key={request.id}
                    request={request}
                    property={propertyByID.get(request.property_id)}
                    homeownerID={user.id}
                    onShare={() => void openShareRequest(request)}
                    onViewEstimates={() => void openGuestEstimates(request)}
                  />
                ))}
              </div>
            )}
          </section>
        </div>

        <aside className="dashboard-secondary">
          <section className="section-card compact-section" id="calendar">
            <p className="kicker">Schedule</p><h2>Next at your home</h2>
            {dashboard.summary.scheduled_visit_count > 0 ? <div className="summary-number"><strong>{dashboard.summary.scheduled_visit_count}</strong><span>scheduled visit{dashboard.summary.scheduled_visit_count === 1 ? "" : "s"}</span></div> : <CompactEmpty title="Nothing scheduled" body="Confirmed contractor visits will appear here." />}
          </section>

          <section className="section-card compact-section" id="payments">
            <p className="kicker">Money</p><h2>Payment status</h2>
            {dashboard.summary.outstanding_invoice_count > 0 ? <div className="summary-number"><strong>{dashboard.summary.outstanding_invoice_count}</strong><span>invoice{dashboard.summary.outstanding_invoice_count === 1 ? "" : "s"} still open</span></div> : <div className="clear-inline"><span>✓</span><p>No outstanding invoices</p></div>}
          </section>

          <section className="section-card home-card" id="home-record">
            <p className="kicker">Property record</p>
            <h2>{currentProperty?.label}</h2>
            <p>{currentProperty ? formatAddress(currentProperty) : ""}</p>
            <dl className="home-facts"><div><dt>Open repairs</dt><dd>{dashboard.summary.open_repair_count}</dd></div><div><dt>Projects</dt><dd>{dashboard.summary.active_project_count}</dd></div></dl>
          </section>
        </aside>
      </section>

      {requestOpen ? (
        <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setRequestOpen(false); }}>
          <section className="modal-sheet" role="dialog" aria-modal="true" aria-labelledby="new-request-title">
            <div className="modal-header"><div><p className="kicker">New repair</p><h2 id="new-request-title">What needs attention?</h2></div><button className="icon-button" type="button" onClick={() => setRequestOpen(false)} aria-label="Close">×</button></div>
            <form className="modal-form" onSubmit={handleCreateWorkRequest}>
              <label className="field full-field"><span>Property</span><select name="property_id" defaultValue={currentProperty?.id} required>{dashboard.properties.map((property) => <option key={property.id} value={property.id}>{property.label}</option>)}</select></label>
              <label className="field full-field"><span>Issue title</span><input name="title" required /></label>
              <div className="form-row two-columns">
                <label className="field"><span>Category</span><select name="category" defaultValue="" required><option value="" disabled>Select a category</option><option value="plumbing">Plumbing</option><option value="electrical">Electrical</option><option value="heating-cooling">Heating and cooling</option><option value="appliance">Appliance</option><option value="roof-exterior">Roof or exterior</option><option value="general">General repair</option></select></label>
                <label className="field"><span>Room or area</span><input name="area" required /></label>
              </div>
              <label className="field full-field"><span>What did you notice?</span><textarea name="description" rows={5} required /></label>
              <label className="field full-field file-picker"><span>Photos or documents <em>Optional</em></span><input name="attachments" type="file" accept="image/jpeg,image/png,image/webp,image/heic,image/heif,application/pdf,.heic,.heif" multiple /><small>Add up to five JPEG, PNG, WebP, HEIC, or PDF files. Each file can be up to 10 MB.</small></label>
              <div className="form-row two-columns">
                <label className="field"><span>Urgency</span><select name="urgency" defaultValue="medium" required><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="urgent">Urgent</option></select></label>
                <label className="field"><span>Preferred timing <em>Optional</em></span><input name="preferred_timing" /></label>
              </div>
              <div className="modal-actions"><button className="text-button" type="button" onClick={() => setRequestOpen(false)}>Cancel</button><button className="primary-button" type="submit" disabled={savingRequest}>{savingRequest ? "Submitting..." : "Submit repair request"}</button></div>
            </form>
          </section>
        </div>
      ) : null}

      {sharingRequest ? (
        <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setSharingRequest(null); }}>
          <section className="modal-sheet share-sheet" role="dialog" aria-modal="true" aria-labelledby="share-request-title">
            <div className="modal-header">
              <div><p className="kicker">Private invitation</p><h2 id="share-request-title">Share “{sharingRequest.title}”</h2></div>
              <button className="icon-button" type="button" onClick={() => setSharingRequest(null)} aria-label="Close">×</button>
            </div>
            <div className="share-modal-body">
              <div className="share-scope-note">
                <strong>The contractor does not need a MyCasaPro account.</strong>
                <p>They will see the issue, room, timing, photos, and approximate location—not your street address or account details. The link expires after seven days.</p>
              </div>
              {shareResult ? (
                <div className="share-link-panel">
                  <label className="field full-field"><span>New private estimate link</span><input value={shareResult.share_url} readOnly onFocus={(event) => event.currentTarget.select()} /></label>
                  <div className="share-link-actions">
                    <button className="primary-button" type="button" onClick={() => void copyShareLink()}>{copiedInvite ? "Copied" : "Copy link"}</button>
                    <a className="secondary-button" href={shareResult.share_url} target="_blank" rel="noreferrer">Preview</a>
                  </div>
                </div>
              ) : (
                <button className="primary-button" type="button" disabled={creatingInvite} onClick={() => void createShareLink()}>{creatingInvite ? "Creating secure link..." : "Create private link"}</button>
              )}
              <section className="invite-register" aria-labelledby="invite-register-title">
                <div className="invite-register-heading"><h3 id="invite-register-title">Invitation history</h3><span>{invites.length}</span></div>
                {loadingInvites ? <p className="muted-copy">Loading invitation history...</p> : null}
                {!loadingInvites && invites.length === 0 ? <p className="muted-copy">No links have been issued for this repair.</p> : null}
                {invites.map((invite) => {
                  const inactive = Boolean(invite.revoked_at) || new Date(invite.expires_at).getTime() <= Date.now();
                  return (
                    <div className="invite-register-row" key={invite.id}>
                      <div><strong>{inactive ? (invite.revoked_at ? "Revoked" : "Expired") : "Active link"}</strong><small>Created {formatShortDate(invite.created_at)} · expires {formatDateTime(invite.expires_at)}</small></div>
                      {!inactive ? <button className="text-button danger-text" type="button" onClick={() => void revokeInvite(invite.id)}>Revoke</button> : null}
                    </div>
                  );
                })}
              </section>
            </div>
          </section>
        </div>
      ) : null}

      {estimateRequest ? (
        <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setEstimateRequest(null); }}>
          <section className="modal-sheet estimate-review-sheet" role="dialog" aria-modal="true" aria-labelledby="guest-estimates-title">
            <div className="modal-header">
              <div><p className="kicker">Contractor responses</p><h2 id="guest-estimates-title">Estimates for “{estimateRequest.title}”</h2></div>
              <button className="icon-button" type="button" onClick={() => setEstimateRequest(null)} aria-label="Close">×</button>
            </div>
            <div className="estimate-review-body">
              {loadingEstimates ? <p className="muted-copy">Loading estimates...</p> : null}
              {!loadingEstimates && guestEstimates.length === 0 ? <CompactEmpty title="No estimates received" body="Share a private link with a contractor and their response will appear here." /> : null}
              {guestEstimates.map((estimate) => (
                <article className="guest-estimate-record" key={estimate.id}>
                  <header><div><p className="kicker">Received {formatDateTime(estimate.created_at)}</p><h3>{estimate.business_name || estimate.contractor_name}</h3><p>{estimate.business_name ? `${estimate.contractor_name} · ` : ""}<a href={`mailto:${estimate.email}`}>{estimate.email}</a></p></div><strong>{formatMoney(estimate.total_amount_cents)}</strong></header>
                  <p className="estimate-summary">{estimate.summary}</p>
                  <dl className="estimate-lines">{estimate.line_items.map((item) => <div key={item.id}><dt>{item.label}</dt><dd>{formatMoney(item.amount_cents)}</dd></div>)}</dl>
                  {estimate.available_timing ? <p className="estimate-detail"><strong>Availability</strong>{estimate.available_timing}</p> : null}
                  {estimate.notes ? <p className="estimate-detail"><strong>Notes</strong>{estimate.notes}</p> : null}
                </article>
              ))}
            </div>
          </section>
        </div>
      ) : null}
    </SiteShell>
  );
}

function DashboardSkeleton() {
  return <div className="dashboard-layout"><div className="dashboard-primary"><div className="section-card skeleton-card"><div className="skeleton skeleton-line short" /><div className="skeleton skeleton-title" /><div className="skeleton skeleton-block" /></div><div className="section-card skeleton-card"><div className="skeleton skeleton-title" /><div className="skeleton skeleton-block tall" /></div></div><div className="dashboard-secondary"><div className="section-card skeleton-card"><div className="skeleton skeleton-line" /><div className="skeleton skeleton-block" /></div></div></div>;
}

function ActionRow({ tone, title, detail }: { tone: string; title: string; detail: string }) {
  return <div className="action-row"><span className="action-dot" data-tone={tone} /><div><strong>{title}</strong><p>{detail}</p></div><span className="row-arrow">→</span></div>;
}

function RepairRequestRow({ request, property, homeownerID, onShare, onViewEstimates }: { request: WorkRequest; property?: Property; homeownerID: string; onShare: () => void; onViewEstimates: () => void }) {
  return <article className="repair-row repair-request-row"><span className="repair-marker" data-tone={request.urgency === "urgent" || request.urgency === "high" ? "urgent" : "new"} /><span className="repair-copy"><strong>{request.title}</strong><small>{property?.label || "Property"} · {request.area} · {formatShortDate(request.created_at)}</small>{request.attachments?.length ? <span className="attachment-links">{request.attachments.slice(0, 3).map((attachment) => <a key={attachment.id} href={`${appURL}/api/v1/homeowners/${homeownerID}/work-requests/${request.id}/attachments/${attachment.id}`} target="_blank" rel="noreferrer">{attachment.content_type.startsWith("image/") ? "Photo" : "PDF"}: {attachment.file_name}</a>)}{request.attachments.length > 3 ? <em>+{request.attachments.length - 3} more</em> : null}</span> : null}</span><StatusBadge status={request.status} /><span className="repair-row-actions"><button type="button" onClick={onShare}>Share for estimate</button>{request.guest_estimate_count > 0 ? <button type="button" onClick={onViewEstimates}>Review {request.guest_estimate_count}</button> : null}</span></article>;
}

class AttachmentUploadError extends Error {}

function isAllowedAttachment(file: File) {
  const extension = file.name.split(".").pop()?.toLowerCase() || "";
  return allowedAttachmentTypes.has(file.type.toLowerCase()) || allowedAttachmentExtensions.has(extension);
}

function StatusBadge({ status }: { status: string }) {
  return <span className={`status-badge status-${status}`}>{status.replaceAll("_", " ")}</span>;
}

function CompactEmpty({ title, body, action }: { title: string; body: string; action?: React.ReactNode }) {
  return <div className="compact-empty"><strong>{title}</strong><p>{body}</p>{action}</div>;
}

function firstName(displayName: string) {
  return displayName.trim().split(/\s+/)[0] || "there";
}

function formatAddress(property: Property) {
  return `${property.address_line_1}, ${property.city}, ${property.region} ${property.postal_code}`;
}

function formatShortDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(new Date(value));
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" }).format(new Date(value));
}

function formatMoney(value: number) {
  return new Intl.NumberFormat(undefined, { style: "currency", currency: "USD" }).format(value / 100);
}
