"use client";

import { useEffect, useMemo, useState } from "react";

type Dashboard = {
  total_requests: number;
  admitted: number;
  held: number;
  escalated: number;
  refused: number;
  pending_review: number;
  recent_requests: RequestSummary[];
};

type RequestSummary = {
  request_id: string;
  workflow_id: string;
  customer_id: string;
  requested_action: string;
  lifecycle_status: string;
  risk_level: string;
  approval_required: boolean;
};

type Decision = {
  request_id: string;
  workflow_id: string;
  outcome: string;
  protected_effect_status: string;
  no_bind_status: boolean;
  reason_codes: string[];
  receipt_id: string;
  replay_token: string;
  customer_visible_summary: string;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

const emptyDashboard: Dashboard = {
  total_requests: 0,
  admitted: 0,
  held: 0,
  escalated: 0,
  refused: 0,
  pending_review: 0,
  recent_requests: []
};

export default function Page() {
  const [dashboard, setDashboard] = useState<Dashboard>(emptyDashboard);
  const [decision, setDecision] = useState<Decision | null>(null);
  const [receipt, setReceipt] = useState<object | null>(null);
  const [replay, setReplay] = useState<object | null>(null);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    customer_id: "demo-customer",
    workflow_id: "vendor-onboarding",
    request_id: `REQ-${Date.now()}`,
    requested_action: "approve_vendor_for_low_risk_service",
    business_context: "Vendor has completed intake. Scope is limited. Evidence has been reviewed.",
    authority_present: true,
    scope_matched: true,
    evidence_present: true,
    evidence_fresh: true,
    risk_level: "low",
    approval_required: false
  });

  async function refreshDashboard() {
    try {
      const res = await fetch(`${API_BASE}/ops/dashboard`);
      if (res.ok) setDashboard(await res.json());
    } catch {
      setDashboard(emptyDashboard);
    }
  }

  async function seedDemo() {
    await fetch(`${API_BASE}/ops/customers`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: "demo-customer", name: "Demo Customer", industry: "operations" })
    });
    await fetch(`${API_BASE}/ops/workflows`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: "vendor-onboarding", customer_id: "demo-customer", name: "Vendor Onboarding", description: "Vendor review workflow." })
    });
    await refreshDashboard();
  }

  useEffect(() => {
    refreshDashboard();
  }, []);

  async function submitRequest() {
    setLoading(true);
    setReceipt(null);
    setReplay(null);
    try {
      const res = await fetch(`${API_BASE}/ops/requests/evaluate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...form, metadata: { source: "frontend-dashboard" } })
      });
      const data = await res.json();
      setDecision(data);
      await refreshDashboard();
    } finally {
      setLoading(false);
    }
  }

  async function review(decisionType: string) {
    if (!decision) return;
    await fetch(`${API_BASE}/ops/requests/${decision.request_id}/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ actor: "ops-reviewer", decision: decisionType, notes: `Dashboard review: ${decisionType}` })
    });
    await refreshDashboard();
  }

  async function loadReceipt() {
    if (!decision) return;
    const res = await fetch(`${API_BASE}/requests/${decision.request_id}/receipt`);
    if (res.ok) setReceipt(await res.json());
  }

  async function runReplay(type: "same-condition" | "changed-condition") {
    if (!decision) return;
    const res = await fetch(`${API_BASE}/replay/${decision.request_id}/${type}`, { method: "POST" });
    if (res.ok) setReplay(await res.json());
  }

  const outcomeClass = useMemo(() => decision?.outcome.toLowerCase() || "hold", [decision]);

  return (
    <main className="page">
      <section className="header">
        <div>
          <div className="eyebrow">Forward Deployed Customer Operations</div>
          <h1>Mission Control Runtime</h1>
          <p className="subtitle">
            A working customer operations platform for workflow intake, evidence checks, review routing,
            governed execution status, receipts, replay, and operational visibility.
          </p>
        </div>
        <button className="button" onClick={seedDemo}>Seed Demo Customer</button>
      </section>

      <section className="grid">
        <Metric title="Total Requests" value={dashboard.total_requests} />
        <Metric title="Admitted" value={dashboard.admitted} />
        <Metric title="Pending Review" value={dashboard.pending_review} />
        <Metric title="Refused" value={dashboard.refused} />
      </section>

      <section className="two-col">
        <div className="card">
          <div className="panel-title"><h2>Submit Customer Request</h2></div>
          <div className="form">
            <input className="input" value={form.request_id} onChange={e => setForm({ ...form, request_id: e.target.value })} placeholder="Request ID" />
            <input className="input" value={form.workflow_id} onChange={e => setForm({ ...form, workflow_id: e.target.value })} placeholder="Workflow ID" />
            <input className="input" value={form.requested_action} onChange={e => setForm({ ...form, requested_action: e.target.value })} placeholder="Requested action" />
            <textarea className="textarea" value={form.business_context} onChange={e => setForm({ ...form, business_context: e.target.value })} />
            <select className="select" value={form.risk_level} onChange={e => setForm({ ...form, risk_level: e.target.value })}>
              <option value="low">low risk</option>
              <option value="medium">medium risk</option>
              <option value="high">high risk</option>
              <option value="critical">critical risk</option>
            </select>
            <div className="checks">
              <Check label="Authority present" checked={form.authority_present} onChange={v => setForm({ ...form, authority_present: v })} />
              <Check label="Scope matched" checked={form.scope_matched} onChange={v => setForm({ ...form, scope_matched: v })} />
              <Check label="Evidence present" checked={form.evidence_present} onChange={v => setForm({ ...form, evidence_present: v })} />
              <Check label="Evidence fresh" checked={form.evidence_fresh} onChange={v => setForm({ ...form, evidence_fresh: v })} />
              <Check label="Approval required" checked={form.approval_required} onChange={v => setForm({ ...form, approval_required: v })} />
            </div>
            <button className="button" onClick={submitRequest} disabled={loading}>{loading ? "Evaluating..." : "Evaluate Request"}</button>
          </div>
        </div>

        <div className="card">
          <div className="panel-title"><h2>Decision + Review</h2></div>
          {decision ? (
            <>
              <p><span className={`badge ${outcomeClass}`}>{decision.outcome}</span></p>
              <p className="subtitle">{decision.customer_visible_summary}</p>
              <p><strong>Effect status:</strong> {decision.protected_effect_status}</p>
              <p><strong>No-bind:</strong> {String(decision.no_bind_status)}</p>
              <div className="receipt">{decision.reason_codes.join("\n")}</div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 12 }}>
                <button className="button" onClick={() => review("approve")}>Approve</button>
                <button className="button" onClick={() => review("hold")}>Hold</button>
                <button className="button" onClick={() => review("escalate")}>Escalate</button>
                <button className="button" onClick={() => review("refuse")}>Refuse</button>
              </div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 12 }}>
                <button className="button" onClick={loadReceipt}>Load Receipt</button>
                <button className="button" onClick={() => runReplay("same-condition")}>Same Replay</button>
                <button className="button" onClick={() => runReplay("changed-condition")}>Changed Replay</button>
              </div>
            </>
          ) : <p className="subtitle">Submit a customer request to see the runtime decision.</p>}
        </div>
      </section>

      <section className="two-col" style={{ marginTop: 18 }}>
        <div className="card">
          <div className="panel-title"><h2>Recent Requests</h2></div>
          <table className="table">
            <thead><tr><th>Request</th><th>Workflow</th><th>Status</th><th>Risk</th></tr></thead>
            <tbody>
              {dashboard.recent_requests.map(r => (
                <tr key={r.request_id}>
                  <td>{r.request_id}</td>
                  <td>{r.workflow_id}</td>
                  <td>{r.lifecycle_status}</td>
                  <td>{r.risk_level}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="card">
          <div className="panel-title"><h2>Receipt / Replay Output</h2></div>
          <div className="receipt">{JSON.stringify(replay || receipt || { status: "No receipt or replay loaded yet." }, null, 2)}</div>
        </div>
      </section>
    </main>
  );
}

function Metric({ title, value }: { title: string; value: number }) {
  return <div className="card"><h3>{title}</h3><div className="metric">{value}</div></div>;
}

function Check({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return <label className="check"><input type="checkbox" checked={checked} onChange={e => onChange(e.target.checked)} />{label}</label>;
}
