"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { useAuth } from "@/components/auth-context";
import { EmptyState } from "@/components/empty-state";
import { Panel } from "@/components/panel";
import { apiFetch, appURL } from "@/lib/api";
import type { Estimate, Invoice, ProjectDetail, ProjectMessage } from "@/lib/types";

type Props = {
  role: "homeowner" | "contractor";
  projectID: string;
};

function moneyInputToCents(value: FormDataEntryValue | null) {
  const raw = typeof value === "string" ? value.trim() : "";
  if (raw === "") {
    return 0;
  }

  const parsed = Number(raw);
  if (!Number.isFinite(parsed) || parsed < 0) {
    return Number.NaN;
  }

  return Math.round(parsed * 100);
}

function datetimeLocalToISOString(value: FormDataEntryValue | null) {
  const raw = typeof value === "string" ? value.trim() : "";
  if (raw === "") {
    return "";
  }

  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) {
    return "";
  }

  return parsed.toISOString();
}

function formatMoney(cents: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(cents / 100);
}

function formatTimestamp(value?: string) {
  if (!value) {
    return "";
  }
  return new Date(value).toLocaleString();
}

function latestPendingEstimate(estimates: Estimate[]) {
  return estimates.find((estimate) => estimate.status === "sent") || null;
}

function nextUpcomingAppointment(project: ProjectDetail) {
  const upcoming = [...project.appointments].sort(
    (a, b) => new Date(a.starts_at).getTime() - new Date(b.starts_at).getTime(),
  );
  return upcoming[0] || null;
}

function totalOutstandingBalance(invoices: Invoice[]) {
  return invoices.reduce((sum, invoice) => sum + invoice.outstanding_amount_cents, 0);
}

function totalPaidAmount(invoices: Invoice[]) {
  return invoices.reduce((sum, invoice) => sum + invoice.amount_paid_cents, 0);
}

function authorLabel(message: ProjectMessage) {
  if (message.author_role === "homeowner") {
    return "Homeowner";
  }
  return "Contractor";
}

export function ProjectWorkspaceView({ role, projectID }: Props) {
  const { user } = useAuth();
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [savingEstimate, setSavingEstimate] = useState(false);
  const [savingAppointment, setSavingAppointment] = useState(false);
  const [savingInvoice, setSavingInvoice] = useState(false);
  const [savingMessage, setSavingMessage] = useState(false);
  const [payingInvoiceID, setPayingInvoiceID] = useState<string | null>(null);
  const [decisioningEstimateID, setDecisioningEstimateID] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const viewerID = user.id;
  const endpoint =
    role === "homeowner"
      ? `/api/v1/homeowners/${viewerID}/projects/${projectID}`
      : `/api/v1/contractors/${viewerID}/projects/${projectID}`;

  const loadProject = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const response = await apiFetch(endpoint, {
        headers: {
          Accept: "application/json",
        },
      });
      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { message?: string } | null;
        throw new Error(payload?.message || `project request failed with ${response.status}`);
      }
      setProject((await response.json()) as ProjectDetail);
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : "Unable to load project");
    } finally {
      setLoading(false);
    }
  }, [endpoint]);

  useEffect(() => {
    void loadProject();
  }, [loadProject]);

  async function handleCreateEstimate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!project) {
      return;
    }

    const form = event.currentTarget;
    const formData = new FormData(form);
    const laborCents = moneyInputToCents(formData.get("labor_amount"));
    const materialsCents = moneyInputToCents(formData.get("materials_amount"));
    const additionalCents = moneyInputToCents(formData.get("additional_amount"));
    const depositCents = moneyInputToCents(formData.get("deposit_amount"));
    const additionalLabel = String(formData.get("additional_label") || "").trim();

    if ([laborCents, materialsCents, additionalCents, depositCents].some((value) => Number.isNaN(value))) {
      setActionError("Money fields must contain valid positive numbers.");
      return;
    }

    if (additionalLabel && additionalCents <= 0) {
      setActionError("If you add an extra line item label, give it a dollar amount too.");
      return;
    }

    const lineItems = [
      laborCents > 0 ? { label: "Labor", amount_cents: laborCents } : null,
      materialsCents > 0 ? { label: "Materials", amount_cents: materialsCents } : null,
      additionalLabel && additionalCents > 0 ? { label: additionalLabel, amount_cents: additionalCents } : null,
    ].filter((item): item is { label: string; amount_cents: number } => item !== null);

    if (lineItems.length === 0) {
      setActionError("Add at least one priced line item before sending the estimate.");
      return;
    }

    setSavingEstimate(true);
    setActionError(null);
    try {
      const response = await apiFetch(`/api/v1/contractors/${user.id}/projects/${project.item.project.id}/estimates`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          summary: formData.get("summary"),
          notes: formData.get("notes"),
          deposit_amount_cents: depositCents,
          line_items: lineItems,
        }),
      });
      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { message?: string } | null;
        throw new Error(payload?.message || `estimate create failed with ${response.status}`);
      }
      form.reset();
      await loadProject();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Unable to send estimate");
    } finally {
      setSavingEstimate(false);
    }
  }

  async function handleEstimateDecision(estimateID: string, decision: "approve" | "reject") {
    if (!project) {
      return;
    }

    setDecisioningEstimateID(estimateID);
    setActionError(null);
    try {
      const response = await apiFetch(
        `/api/v1/homeowners/${user.id}/projects/${project.item.project.id}/estimates/${estimateID}/${decision}`,
        {
          method: "POST",
          headers: {
            Accept: "application/json",
          },
        },
      );
      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { message?: string } | null;
        throw new Error(payload?.message || `estimate ${decision} failed with ${response.status}`);
      }
      await loadProject();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Unable to update estimate");
    } finally {
      setDecisioningEstimateID(null);
    }
  }

  async function handleCreateAppointment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!project) {
      return;
    }

    const form = event.currentTarget;
    const formData = new FormData(form);
    const startsAt = datetimeLocalToISOString(formData.get("starts_at"));
    const endsAt = datetimeLocalToISOString(formData.get("ends_at"));

    if (!startsAt || !endsAt) {
      setActionError("Enter a valid visit start and end time.");
      return;
    }

    setSavingAppointment(true);
    setActionError(null);
    try {
      const response = await apiFetch(
        `/api/v1/contractors/${user.id}/projects/${project.item.project.id}/appointments`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify({
            title: formData.get("title"),
            notes: formData.get("notes"),
            starts_at: startsAt,
            ends_at: endsAt,
          }),
        },
      );
      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { message?: string } | null;
        throw new Error(payload?.message || `appointment create failed with ${response.status}`);
      }
      form.reset();
      await loadProject();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Unable to schedule visit");
    } finally {
      setSavingAppointment(false);
    }
  }

  async function handleCreateInvoice(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!project) {
      return;
    }

    const form = event.currentTarget;
    const formData = new FormData(form);
    const amountCents = moneyInputToCents(formData.get("amount"));
    const dueAt = datetimeLocalToISOString(formData.get("due_at"));

    if (Number.isNaN(amountCents) || amountCents <= 0) {
      setActionError("Invoice amount must be a valid positive number.");
      return;
    }
    if (!dueAt) {
      setActionError("Choose a valid invoice due date.");
      return;
    }

    setSavingInvoice(true);
    setActionError(null);
    try {
      const response = await apiFetch(`/api/v1/contractors/${user.id}/projects/${project.item.project.id}/invoices`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          summary: formData.get("summary"),
          notes: formData.get("notes"),
          amount_cents: amountCents,
          due_at: dueAt,
        }),
      });
      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { message?: string } | null;
        throw new Error(payload?.message || `invoice create failed with ${response.status}`);
      }
      form.reset();
      await loadProject();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Unable to create invoice");
    } finally {
      setSavingInvoice(false);
    }
  }

  async function handleRecordInvoicePayment(event: FormEvent<HTMLFormElement>, invoiceID: string) {
    event.preventDefault();
    if (!project) {
      return;
    }

    const form = event.currentTarget;
    const formData = new FormData(form);
    const amountCents = moneyInputToCents(formData.get("amount"));

    if (Number.isNaN(amountCents) || amountCents <= 0) {
      setActionError("Payment amount must be a valid positive number.");
      return;
    }

    setPayingInvoiceID(invoiceID);
    setActionError(null);
    try {
      const response = await apiFetch(
        `/api/v1/homeowners/${user.id}/projects/${project.item.project.id}/invoices/${invoiceID}/payments`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify({
            amount_cents: amountCents,
            note: formData.get("note"),
          }),
        },
      );
      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { message?: string } | null;
        throw new Error(payload?.message || `payment failed with ${response.status}`);
      }
      form.reset();
      await loadProject();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Unable to record payment");
    } finally {
      setPayingInvoiceID(null);
    }
  }

  async function handleCreateMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!project) {
      return;
    }

    const form = event.currentTarget;
    const formData = new FormData(form);
    const body = String(formData.get("body") || "").trim();
    const visibility = role === "contractor" ? String(formData.get("visibility") || "shared") : "shared";

    if (!body) {
      setActionError("Message body is required.");
      return;
    }

    setSavingMessage(true);
    setActionError(null);
    try {
      const endpoint =
        role === "homeowner"
          ? `/api/v1/homeowners/${user.id}/projects/${project.item.project.id}/messages`
          : `/api/v1/contractors/${user.id}/projects/${project.item.project.id}/messages`;

      const response = await apiFetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          body,
          visibility,
        }),
      });
      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { message?: string } | null;
        throw new Error(payload?.message || `message create failed with ${response.status}`);
      }
      form.reset();
      await loadProject();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Unable to send message");
    } finally {
      setSavingMessage(false);
    }
  }

  if (loading) {
    return (
      <Panel title="Loading project" description="Pulling the latest workspace state from the backend.">
        <p className="metric-caption">Just a moment...</p>
      </Panel>
    );
  }

  if (loadError || !project) {
    return (
      <Panel title="Project unavailable" description="The shared workspace could not be loaded right now.">
        <EmptyState
          title="Project not ready"
          body={loadError || "This project could not be found for the current viewer."}
          cta="Go back and refresh the dashboard"
        />
      </Panel>
    );
  }

  const backHref = role === "homeowner" ? "/homeowner" : "/contractor";
  const pendingEstimate = latestPendingEstimate(project.estimates);
  const upcomingAppointment = nextUpcomingAppointment(project);
  const outstandingBalance = totalOutstandingBalance(project.invoices);
  const paidToDate = totalPaidAmount(project.invoices);

  return (
    <div className="dashboard-stack">
      {actionError ? <div className="error-banner">Action issue: {actionError}</div> : null}

      <Panel
        title={project.item.project.title}
        description={`${project.item.property.label} · ${project.item.property.city}, ${project.item.property.region}`}
      >
        <div className="project-header-row">
          <span className={`status-pill status-${project.item.project.status}`}>{project.item.project.status}</span>
          <Link className="button button-secondary" href={backHref}>
            Back to dashboard
          </Link>
        </div>
      </Panel>

      <section className="stats-grid project-stats-grid">
        <Panel title="Latest estimate" description="What the current approved or pending scope is worth.">
          <p className="metric-value">
            {project.estimates[0] ? formatMoney(project.estimates[0].total_amount_cents) : "--"}
          </p>
          <p className="metric-caption">
            {project.estimates[0]
              ? `${project.estimates[0].summary} · ${project.estimates[0].status.replaceAll("_", " ")}`
              : "No estimate sent yet."}
          </p>
        </Panel>

        <Panel title="Next visit" description="The next scheduled time someone is expected on site.">
          <p className="metric-value">{upcomingAppointment ? formatTimestamp(upcomingAppointment.starts_at) : "--"}</p>
          <p className="metric-caption">
            {upcomingAppointment ? upcomingAppointment.title : "No appointment scheduled yet."}
          </p>
        </Panel>

        <Panel title="Outstanding balance" description="What is still open and waiting to be paid.">
          <p className="metric-value">{formatMoney(outstandingBalance)}</p>
          <p className="metric-caption">
            {outstandingBalance > 0
              ? `${project.invoices.filter((invoice) => invoice.outstanding_amount_cents > 0).length} invoice(s) still open`
              : "All invoices are fully paid."}
          </p>
        </Panel>

        <Panel title="Paid to date" description="Everything already recorded against this project.">
          <p className="metric-value">{formatMoney(paidToDate)}</p>
          <p className="metric-caption">
            {project.invoices.length > 0 ? `${project.invoices.length} invoice(s) issued so far` : "No billing activity yet."}
          </p>
        </Panel>
      </section>

      <section className="feature-grid two-up">
        <Panel title="Scope origin" description="How this project started.">
          {project.item.work_request ? (
            <div className="card-list">
              <article className="mini-card">
                <h3>{project.item.work_request.title}</h3>
                <p>
                  {project.item.work_request.category} · {project.item.work_request.area} · {project.item.work_request.urgency}
                </p>
                <p>{project.item.work_request.description}</p>
                {project.item.work_request.preferred_timing ? (
                  <p>Preferred timing: {project.item.work_request.preferred_timing}</p>
                ) : null}
                {project.item.work_request.attachments?.length ? (
                  <div className="job-evidence" aria-label="Repair attachments">
                    <strong>Photos and documents</strong>
                    <div className="attachment-links">
                      {project.item.work_request.attachments.map((attachment) => (
                        <a key={attachment.id} href={`${appURL}/api/v1/${role === "homeowner" ? "homeowners" : "contractors"}/${user.id}/work-requests/${project.item.work_request!.id}/attachments/${attachment.id}`} target="_blank" rel="noreferrer">
                          {attachment.content_type.startsWith("image/") ? "Photo" : "PDF"}: {attachment.file_name}
                        </a>
                      ))}
                    </div>
                  </div>
                ) : null}
              </article>
            </div>
          ) : (
            <EmptyState
              title="No linked request"
              body="This project does not currently have the original homeowner request attached."
            />
          )}
        </Panel>

        <Panel title="Property context" description="The home and address this work belongs to.">
          <div className="card-list">
            <article className="mini-card">
              <h3>{project.item.property.label}</h3>
              <p>
                {project.item.property.address_line_1}
                <br />
                {project.item.property.city}, {project.item.property.region} {project.item.property.postal_code}
              </p>
            </article>
          </div>
        </Panel>
      </section>

      <section className="feature-grid two-up">
        <Panel
          title="Estimate workspace"
          description="Shared pricing, deposit terms, and approval history stay attached to the job."
        >
          {project.estimates.length === 0 ? (
            <EmptyState
              title="No estimate yet"
              body={
                role === "contractor"
                  ? "Send the first structured estimate so the homeowner can approve work without calls or side-texts."
                  : "Once the contractor sends pricing, it will show up here with line items and approval controls."
              }
            />
          ) : (
            <div className="card-list">
              {project.estimates.map((estimate) => (
                <article className="mini-card" key={estimate.id}>
                  <div className="mini-card-topline">
                    <h3>{estimate.summary}</h3>
                    <span className={`status-pill status-${estimate.status}`}>{estimate.status}</span>
                  </div>
                  <p>
                    Total {formatMoney(estimate.total_amount_cents)}
                    {estimate.deposit_amount_cents > 0 ? ` · Deposit ${formatMoney(estimate.deposit_amount_cents)}` : ""}
                  </p>
                  <ul className="estimate-line-list">
                    {estimate.line_items.map((item) => (
                      <li key={item.id}>
                        <span>{item.label}</span>
                        <strong>{formatMoney(item.amount_cents)}</strong>
                      </li>
                    ))}
                  </ul>
                  {estimate.notes ? <p>{estimate.notes}</p> : null}
                  <p>
                    Sent {formatTimestamp(estimate.sent_at || estimate.created_at)}
                    {estimate.decided_at ? ` · Decision ${formatTimestamp(estimate.decided_at)}` : ""}
                  </p>
                  {role === "homeowner" && estimate.status === "sent" ? (
                    <div className="inline-actions">
                      <button
                        className="button button-primary"
                        type="button"
                        disabled={decisioningEstimateID === estimate.id}
                        onClick={() => void handleEstimateDecision(estimate.id, "approve")}
                      >
                        {decisioningEstimateID === estimate.id ? "Saving..." : "Approve estimate"}
                      </button>
                      <button
                        className="button button-secondary"
                        type="button"
                        disabled={decisioningEstimateID === estimate.id}
                        onClick={() => void handleEstimateDecision(estimate.id, "reject")}
                      >
                        Decline estimate
                      </button>
                    </div>
                  ) : null}
                </article>
              ))}
            </div>
          )}
        </Panel>

        {role === "contractor" ? (
          <Panel title="Send estimate" description="Give the homeowner a clean, structured price they can act on immediately.">
            <form className="stack-form" onSubmit={handleCreateEstimate}>
              <input name="summary" placeholder="Estimate summary" required />
              <div className="compact-grid">
                <input name="labor_amount" type="number" min="0" step="0.01" placeholder="Labor ($)" />
                <input name="materials_amount" type="number" min="0" step="0.01" placeholder="Materials ($)" />
              </div>
              <div className="compact-grid">
                <input name="additional_label" placeholder="Optional extra item label" />
                <input name="additional_amount" type="number" min="0" step="0.01" placeholder="Optional extra ($)" />
              </div>
              <input name="deposit_amount" type="number" min="0" step="0.01" placeholder="Deposit requested ($)" />
              <textarea name="notes" rows={5} placeholder="Scope notes, exclusions, or schedule assumptions" />
              <button className="button button-primary" type="submit" disabled={savingEstimate}>
                {savingEstimate ? "Sending estimate..." : "Send estimate"}
              </button>
            </form>
          </Panel>
        ) : (
          <Panel
            title="Homeowner next step"
            description="This panel keeps the decision simple when pricing lands."
          >
            {pendingEstimate ? (
              <div className="card-list">
                <article className="mini-card">
                  <h3>Review the latest estimate</h3>
                  <p>
                    {pendingEstimate.summary} is waiting for your decision at{" "}
                    {formatMoney(pendingEstimate.total_amount_cents)}.
                  </p>
                  <p>
                    Approval keeps the project moving. Declining it sends the contractor back for a revision without
                    losing the full project history.
                  </p>
                </article>
              </div>
            ) : (
              <EmptyState
                title="No decision pending"
                body="Once the contractor sends or revises pricing, you will be able to approve or decline it here."
              />
            )}
          </Panel>
        )}
      </section>

      <section className="feature-grid two-up">
        <Panel title="Visits and schedule" description="Everyone can see when the next on-site touchpoint is happening.">
          {project.appointments.length === 0 ? (
            <EmptyState
              title="No visits scheduled yet"
              body="Once the contractor locks in a walkthrough or repair visit, it will appear here with the full time window."
            />
          ) : (
            <div className="card-list">
              {project.appointments.map((appointment) => (
                <article className="mini-card" key={appointment.id}>
                  <div className="mini-card-topline">
                    <h3>{appointment.title}</h3>
                    <span className={`status-pill status-${appointment.status}`}>{appointment.status}</span>
                  </div>
                  <p>
                    {formatTimestamp(appointment.starts_at)} - {formatTimestamp(appointment.ends_at)}
                  </p>
                  {appointment.notes ? <p>{appointment.notes}</p> : null}
                </article>
              ))}
            </div>
          )}
        </Panel>

        {role === "contractor" ? (
          <Panel title="Schedule site visit" description="Turn approved scope into a concrete on-site time the homeowner can trust.">
            <form className="stack-form" onSubmit={handleCreateAppointment}>
              <input name="title" placeholder="Visit title" required />
              <div className="compact-grid">
                <input name="starts_at" type="datetime-local" required />
                <input name="ends_at" type="datetime-local" required />
              </div>
              <textarea name="notes" rows={4} placeholder="Arrival notes, access details, or prep instructions" />
              <button className="button button-primary" type="submit" disabled={savingAppointment}>
                {savingAppointment ? "Scheduling visit..." : "Schedule visit"}
              </button>
            </form>
          </Panel>
        ) : (
          <Panel title="Homeowner view" description="The visit plan stays anchored to the project instead of text messages.">
            {project.appointments.length > 0 ? (
              <div className="card-list">
                <article className="mini-card">
                  <h3>Next scheduled touchpoint</h3>
                  <p>
                    {project.appointments[0].title} is currently set for {formatTimestamp(project.appointments[0].starts_at)}.
                  </p>
                  <p>Need to reschedule? Keep the conversation on this project so the history stays clear for both sides.</p>
                </article>
              </div>
            ) : (
              <EmptyState
                title="Waiting on a scheduled visit"
                body="After you approve scope, the contractor can place the first site visit right here."
              />
            )}
          </Panel>
        )}
      </section>

      <section className="feature-grid two-up">
        <Panel title="Invoices and payments" description="A readable money trail for every bill, deposit, and payment.">
          {project.invoices.length === 0 ? (
            <EmptyState
              title="No invoices yet"
              body={
                role === "contractor"
                  ? "Create the first invoice once scope is approved or a deposit is needed."
                  : "Invoices will show up here with due dates, balances, and payment history."
              }
            />
          ) : (
            <div className="card-list">
              {project.invoices.map((invoice) => (
                <article className="mini-card" key={invoice.id}>
                  <div className="mini-card-topline">
                    <h3>{invoice.summary}</h3>
                    <span className={`status-pill status-${invoice.status}`}>{invoice.status.replaceAll("_", " ")}</span>
                  </div>
                  <div className="invoice-amount-row">
                    <div>
                      <p className="ledger-label">Invoice total</p>
                      <p className="ledger-value">{formatMoney(invoice.amount_cents)}</p>
                    </div>
                    <div>
                      <p className="ledger-label">Outstanding</p>
                      <p className="ledger-value">{formatMoney(invoice.outstanding_amount_cents)}</p>
                    </div>
                  </div>
                  <p>Due {formatTimestamp(invoice.due_at)}</p>
                  {invoice.notes ? <p>{invoice.notes}</p> : null}
                  {invoice.payments.length > 0 ? (
                    <div className="payment-list">
                      {invoice.payments.map((payment) => (
                        <article className="payment-item" key={payment.id}>
                          <div className="payment-item-topline">
                            <strong>{formatMoney(payment.amount_cents)}</strong>
                            <span>{formatTimestamp(payment.paid_at)}</span>
                          </div>
                          {payment.note ? <p>{payment.note}</p> : null}
                        </article>
                      ))}
                    </div>
                  ) : (
                    <p className="metric-caption">No payments recorded yet.</p>
                  )}

                  {role === "homeowner" && invoice.outstanding_amount_cents > 0 ? (
                    <form className="stack-form compact-form" onSubmit={(event) => void handleRecordInvoicePayment(event, invoice.id)}>
                      <div className="compact-grid">
                        <input
                          name="amount"
                          type="number"
                          min="0"
                          step="0.01"
                          defaultValue={(invoice.outstanding_amount_cents / 100).toFixed(2)}
                          required
                        />
                        <input name="note" placeholder="Payment note (optional)" />
                      </div>
                      <button className="button button-primary" type="submit" disabled={payingInvoiceID === invoice.id}>
                        {payingInvoiceID === invoice.id ? "Recording payment..." : "Record payment"}
                      </button>
                    </form>
                  ) : null}
                </article>
              ))}
            </div>
          )}
        </Panel>

        {role === "contractor" ? (
          <Panel title="Create invoice" description="Send a clear bill with due date and amount straight into the shared ledger.">
            <form className="stack-form" onSubmit={handleCreateInvoice}>
              <input name="summary" placeholder="Invoice summary" required />
              <div className="compact-grid">
                <input name="amount" type="number" min="0" step="0.01" placeholder="Amount ($)" required />
                <input name="due_at" type="datetime-local" required />
              </div>
              <textarea name="notes" rows={4} placeholder="Invoice notes, payment instructions, or scope reference" />
              <button className="button button-primary" type="submit" disabled={savingInvoice}>
                {savingInvoice ? "Sending invoice..." : "Send invoice"}
              </button>
            </form>
          </Panel>
        ) : (
          <Panel title="Payment clarity" description="Homeowners always see what is due, what is paid, and what changed.">
            {project.invoices.some((invoice) => invoice.outstanding_amount_cents > 0) ? (
              <div className="card-list">
                <article className="mini-card">
                  <h3>Open balance on the project</h3>
                  <p>{formatMoney(outstandingBalance)} is still open across your current invoices.</p>
                  <p>Recording payment here updates the shared record immediately for both homeowner and contractor.</p>
                </article>
              </div>
            ) : (
              <EmptyState
                title="No money due right now"
                body="When the contractor sends a bill, this panel turns into a simple payment cockpit instead of a back-and-forth text thread."
              />
            )}
          </Panel>
        )}
      </section>

      <section className="feature-grid two-up">
        <Panel title="Project conversation" description="Keep every decision, update, and access note attached to the job.">
          {project.messages.length === 0 ? (
            <EmptyState
              title="No messages yet"
              body={
                role === "contractor"
                  ? "Start the thread with arrival expectations, questions, or an internal prep note for your team."
                  : "Ask clarifying questions or confirm access details here so nothing gets lost in text messages."
              }
            />
          ) : (
            <div className="message-feed">
              {project.messages.map((message) => (
                <article
                  className={`message-card ${message.author_role === "homeowner" ? "message-homeowner" : "message-contractor"} ${
                    message.visibility === "internal" ? "message-internal" : ""
                  }`}
                  key={message.id}
                >
                  <div className="message-meta">
                    <div className="message-meta-left">
                      <strong>{authorLabel(message)}</strong>
                      <span className={`message-visibility message-visibility-${message.visibility}`}>
                        {message.visibility === "internal" ? "Internal note" : "Shared"}
                      </span>
                    </div>
                    <span>{formatTimestamp(message.created_at)}</span>
                  </div>
                  <p>{message.body}</p>
                </article>
              ))}
            </div>
          )}
        </Panel>

        <Panel
          title={role === "contractor" ? "Send update or note" : "Send message"}
          description={
            role === "contractor"
              ? "Shared updates stay visible to the homeowner. Internal notes stay on the contractor side only."
              : "Use this thread for access, questions, confirmations, and anything tied to the repair."
          }
        >
          <form className="stack-form" onSubmit={handleCreateMessage}>
            {role === "contractor" ? (
              <select name="visibility" defaultValue="shared">
                <option value="shared">Shared with homeowner</option>
                <option value="internal">Internal contractor note</option>
              </select>
            ) : null}
            <textarea name="body" rows={5} placeholder="Write a project update or question" required />
            <button className="button button-primary" type="submit" disabled={savingMessage}>
              {savingMessage ? "Sending..." : role === "contractor" ? "Post update" : "Send message"}
            </button>
          </form>
        </Panel>
      </section>

      <Panel title="Shared timeline" description="A durable record of how this job moved from request to active project.">
        {project.timeline.length === 0 ? (
          <EmptyState
            title="Timeline is empty"
            body="Timeline events will appear here as the estimate, schedule, updates, and payments are added."
          />
        ) : (
          <div className="timeline-list">
            {project.timeline.map((event) => (
              <article className="timeline-item" key={event.id}>
                <p className="eyebrow">{event.event_type.replaceAll("_", " ")}</p>
                <h3>{event.title}</h3>
                <p>{event.description}</p>
                <p className="timeline-time">{new Date(event.created_at).toLocaleString()}</p>
              </article>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
