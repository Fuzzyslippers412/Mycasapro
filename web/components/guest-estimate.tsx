"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { apiError, apiFetch, appURL } from "@/lib/api";
import type { GuestEstimate, PublicInviteTask } from "@/lib/types";

type EstimateLine = { id: number; label: string; amount: string };

export function GuestEstimateView({ token }: { token: string }) {
  const [task, setTask] = useState<PublicInviteTask | null>(null);
  const [loading, setLoading] = useState(true);
  const [unavailable, setUnavailable] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState<GuestEstimate | null>(null);
  const [lines, setLines] = useState<EstimateLine[]>([{ id: 1, label: "Labor and materials", amount: "" }]);
  const [nextLineID, setNextLineID] = useState(2);

  useEffect(() => {
    let cancelled = false;
    async function loadTask() {
      setLoading(true);
      setError(null);
      try {
        const response = await apiFetch(`/api/v1/invites/${encodeURIComponent(token)}`);
        if (!response.ok) {
          if (response.status === 404 || response.status === 410) setUnavailable(true);
          throw new Error(await apiError(response, "This private request is not available"));
        }
        const payload = (await response.json()) as PublicInviteTask;
        if (!cancelled) setTask(payload);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "This private request is not available");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void loadTask();
    return () => { cancelled = true; };
  }, [token]);

  const estimateTotal = useMemo(() => lines.reduce((total, line) => total + parseDollarAmount(line.amount), 0), [lines]);

  function updateLine(id: number, field: "label" | "amount", value: string) {
    setLines((current) => current.map((line) => line.id === id ? { ...line, [field]: value } : line));
  }

  function addLine() {
    if (lines.length >= 12) return;
    setLines((current) => [...current, { id: nextLineID, label: "", amount: "" }]);
    setNextLineID((current) => current + 1);
  }

  function removeLine(id: number) {
    if (lines.length === 1) return;
    setLines((current) => current.filter((line) => line.id !== id));
  }

  async function submitEstimate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    const lineItems = lines.map((line) => ({ label: line.label.trim(), amount_cents: parseDollarAmount(line.amount) }));
    if (lineItems.some((line) => !line.label || line.amount_cents < 0)) {
      setError("Add a description and a valid amount for every estimate line.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const response = await apiFetch(`/api/v1/invites/${encodeURIComponent(token)}/estimates`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contractor_name: formData.get("contractor_name"),
          business_name: formData.get("business_name"),
          email: formData.get("email"),
          summary: formData.get("summary"),
          available_timing: formData.get("available_timing"),
          notes: formData.get("notes"),
          line_items: lineItems,
        }),
      });
      if (!response.ok) {
        if (response.status === 404 || response.status === 410) setUnavailable(true);
        throw new Error(await apiError(response, "Unable to send this estimate"));
      }
      setSubmitted((await response.json()) as GuestEstimate);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to send this estimate");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) return <GuestPageFrame><div className="guest-loading"><p className="kicker">Private request</p><h1>Opening the home record...</h1></div></GuestPageFrame>;

  if (unavailable || !task) {
    return <GuestPageFrame><section className="guest-unavailable"><p className="kicker">Link unavailable</p><h1>This repair invitation is closed.</h1><p>{error || "The link may have expired or been revoked."} Ask the homeowner to send a new private link if they still need your estimate.</p></section></GuestPageFrame>;
  }

  if (submitted) {
    return <GuestPageFrame><section className="guest-success"><p className="kicker">Estimate delivered</p><h1>Your estimate is with the homeowner.</h1><p>MyCasaPro recorded your {formatMoney(submitted.total_amount_cents)} estimate for “{task.work_request.title}.” The homeowner can review your scope, pricing, and contact details now.</p><dl><div><dt>Submitted by</dt><dd>{submitted.business_name || submitted.contractor_name}</dd></div><div><dt>Contact</dt><dd>{submitted.email}</dd></div><div><dt>Estimate total</dt><dd>{formatMoney(submitted.total_amount_cents)}</dd></div></dl><p className="guest-fine-print">You do not need to create an account. Keep this page for your records.</p></section></GuestPageFrame>;
  }

  return (
    <GuestPageFrame>
      <main className="guest-estimate-layout">
        <section className="guest-task-column">
          <p className="kicker">Private estimate request</p>
          <h1>{task.work_request.title}</h1>
          <p className="guest-location">{task.property.label} · {task.property.city}, {task.property.region}</p>
          <div className="guest-task-meta"><span>{humanize(task.work_request.category)}</span><span>{task.work_request.area}</span><span data-urgency={task.work_request.urgency}>{humanize(task.work_request.urgency)} priority</span></div>
          <section className="guest-task-section"><h2>What the homeowner noticed</h2><p>{task.work_request.description}</p></section>
          {task.work_request.preferred_timing ? <section className="guest-task-section"><h2>Preferred timing</h2><p>{task.work_request.preferred_timing}</p></section> : null}
          <section className="guest-task-section">
            <h2>Photos and documents</h2>
            {task.work_request.attachments.length === 0 ? <p className="muted-copy">No files were included.</p> : <div className="guest-attachments">{task.work_request.attachments.map((attachment) => <a key={attachment.id} href={`${appURL}${attachment.content_path}`} target="_blank" rel="noreferrer"><span>{attachment.content_type.startsWith("image/") ? "Photo" : "Document"}</span><strong>{attachment.file_name}</strong><small>{formatFileSize(attachment.size_bytes)}</small></a>)}</div>}
          </section>
          <p className="guest-privacy-note">For privacy, this page shows only the approximate property location. Coordinate the exact address and visit details directly with the homeowner.</p>
        </section>

        <section className="guest-form-column">
          <div className="guest-form-heading"><p className="kicker">Your response</p><h2>Prepare an estimate</h2><p>Give the homeowner a clear scope and price they can review without phone tag.</p></div>
          <form className="guest-estimate-form" onSubmit={submitEstimate}>
            {error ? <div className="form-error" role="alert">{error}</div> : null}
            <div className="form-row two-columns"><label className="field"><span>Your name</span><input name="contractor_name" autoComplete="name" required /></label><label className="field"><span>Business name <em>Optional</em></span><input name="business_name" autoComplete="organization" /></label></div>
            <label className="field full-field"><span>Email</span><input name="email" type="email" autoComplete="email" required /><small>The homeowner will use this to follow up about your estimate.</small></label>
            <label className="field full-field"><span>Scope of work</span><textarea name="summary" rows={5} placeholder="Explain what you will repair, replace, or inspect." required /></label>
            <fieldset className="estimate-builder"><legend>Price breakdown</legend>{lines.map((line, index) => <div className="estimate-builder-row" key={line.id}><label><span>{index === 0 ? "Item" : `Item ${index + 1}`}</span><input value={line.label} onChange={(event) => updateLine(line.id, "label", event.target.value)} required /></label><label><span>Amount</span><span className="money-input"><b>$</b><input value={line.amount} onChange={(event) => updateLine(line.id, "amount", event.target.value)} inputMode="decimal" pattern="[0-9]*[.]?[0-9]{0,2}" placeholder="0.00" required /></span></label>{lines.length > 1 ? <button type="button" onClick={() => removeLine(line.id)} aria-label={`Remove item ${index + 1}`}>×</button> : <span />}</div>)}<div className="estimate-builder-footer"><button type="button" onClick={addLine} disabled={lines.length >= 12}>+ Add line</button><p><span>Estimate total</span><strong>{formatMoney(estimateTotal)}</strong></p></div></fieldset>
            <label className="field full-field"><span>Availability <em>Optional</em></span><input name="available_timing" placeholder="For example, Tuesday afternoon or within 7 days" /></label>
            <label className="field full-field"><span>Notes or terms <em>Optional</em></span><textarea name="notes" rows={3} placeholder="Warranty, exclusions, payment terms, or questions." /></label>
            <div className="guest-submit"><p>By sending this estimate, you confirm the information is accurate and may be shared with the homeowner.</p><button className="primary-button" type="submit" disabled={submitting}>{submitting ? "Sending estimate..." : `Send ${formatMoney(estimateTotal)} estimate`}</button></div>
          </form>
        </section>
      </main>
    </GuestPageFrame>
  );
}

function GuestPageFrame({ children }: { children: React.ReactNode }) {
  return <div className="guest-page"><header className="guest-header"><a className="auth-brand" href="/"><span className="brand-name">MyCasa</span><span className="brand-pro">Pro</span></a><p>Home repair, clearly documented</p></header>{children}</div>;
}

function parseDollarAmount(value: string) {
  const amount = Number(value);
  return Number.isFinite(amount) && amount >= 0 ? Math.round(amount * 100) : -1;
}

function humanize(value: string) {
  return value.replaceAll("-", " ").replaceAll("_", " ");
}

function formatMoney(value: number) {
  return new Intl.NumberFormat(undefined, { style: "currency", currency: "USD" }).format(value / 100);
}

function formatFileSize(value: number) {
  if (value < 1024 * 1024) return `${Math.max(1, Math.round(value / 1024))} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}
