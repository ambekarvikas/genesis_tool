"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Report = {
  id: number;
  report_type: string;
  label: string | null;
  created_at: string;
  system_scores: Record<string, number>;
};

type Intervention = {
  id: number;
  system: string;
  interventions: string[];
  adherence: string;
  notes: string | null;
  created_at: string;
};

type Patient = { id: number; name: string; age: number; gender: string };

const SYSTEM_COLORS: Record<string, string> = {
  Energy: "bg-yellow-500",
  Detox: "bg-green-500",
  Brain: "bg-blue-500",
  Inflammation: "bg-red-500",
  Recovery: "bg-purple-500",
};

function ScoreBar({ system, score }: { system: string; score: number }) {
  const color = SYSTEM_COLORS[system] ?? "bg-gray-500";
  const pct = Math.min(100, Math.max(0, score));
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-gray-400">
        <span>{system}</span>
        <span className={score < 50 ? "text-red-400" : score >= 70 ? "text-green-400" : "text-yellow-400"}>
          {score}
        </span>
      </div>
      <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function PatientDetailPage() {
  const params = useParams();
  const patientId = Number(params.id);

  const [patient, setPatient] = useState<Patient | null>(null);
  const [reports, setReports] = useState<Report[]>([]);
  const [interventions, setInterventions] = useState<Intervention[]>([]);
  const [loading, setLoading] = useState(true);

  // upload form
  const fileRef = useRef<HTMLInputElement>(null);
  const [reportType, setReportType] = useState<"baseline" | "followup">("followup");
  const [reportLabel, setReportLabel] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // intervention form
  const [invSystem, setInvSystem] = useState("Detox");
  const [invItems, setInvItems] = useState("");
  const [invAdherence, setInvAdherence] = useState("good");
  const [invNotes, setInvNotes] = useState("");
  const [invReportId, setInvReportId] = useState<string>("");
  const [savingInv, setSavingInv] = useState(false);
  const [invMsg, setInvMsg] = useState<string | null>(null);

  const loadData = async () => {
    try {
      const [pRes, rRes] = await Promise.all([
        fetch(`${API}/patients`),
        fetch(`${API}/patient/${patientId}/reports`),
      ]);
      const patients: Patient[] = await pRes.json();
      const found = patients.find((p) => p.id === patientId) ?? null;
      setPatient(found);
      const rData = await rRes.json();
      setReports(rData.reports ?? []);
    } catch {
      // silently fail on load
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, [patientId]);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    setUploading(true); setUploadMsg(null); setUploadError(null);
    try {
      const form = new FormData();
      form.append("patient_id", String(patientId));
      form.append("file", file);
      form.append("report_type", reportType);
      if (reportLabel.trim()) form.append("label", reportLabel.trim());
      const res = await fetch(`${API}/analyze`, { method: "POST", body: form });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setUploadMsg(`Report #${data.report_id} saved (${data.report_type})`);
      if (fileRef.current) fileRef.current.value = "";
      setReportLabel("");
      await loadData();
    } catch (err: unknown) {
      setUploadError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleIntervention = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingInv(true); setInvMsg(null);
    try {
      const items = invItems.split(",").map((s) => s.trim()).filter(Boolean);
      const body: Record<string, unknown> = {
        patient_id: patientId,
        system: invSystem,
        interventions: items,
        adherence: invAdherence,
        notes: invNotes.trim() || null,
      };
      if (invReportId) body.report_id = parseInt(invReportId);
      const res = await fetch(`${API}/interventions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(await res.text());
      setInvItems(""); setInvNotes(""); setInvReportId("");
      setInvMsg("Intervention saved ✓");
      // refresh interventions list
      const all: Intervention[] = [];
      for (const sys of ["Energy", "Detox", "Brain", "Inflammation", "Recovery"]) {
        try {
          const r = await fetch(`${API}/patient/${patientId}/interventions/${sys}`);
          const d = await r.json();
          all.push(...(d.history ?? []).map((h: Record<string, unknown>) => ({
            ...h, system: sys,
            interventions: Array.isArray(h.interventions) ? h.interventions : [],
          })));
        } catch { /* skip */ }
      }
      setInterventions(all);
    } catch (err: unknown) {
      setInvMsg(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSavingInv(false);
    }
  };

  if (loading) return <main className="min-h-screen bg-gray-950 text-gray-400 p-6">Loading…</main>;

  return (
    <main className="min-h-screen bg-gray-950 text-gray-100 p-6">
      <div className="max-w-5xl mx-auto space-y-8">

        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">{patient?.name ?? `Patient ${patientId}`}</h1>
            <p className="text-gray-400 text-sm mt-1">
              {patient ? `${patient.age > 0 ? `${patient.age} y/o · ` : ""}${patient.gender}` : ""}
              &nbsp;&nbsp;·&nbsp;&nbsp;
              <span className="text-gray-500">{reports.length} report{reports.length !== 1 ? "s" : ""}</span>
            </p>
          </div>
          <div className="flex gap-3">
            {reports.length >= 2 && (
              <Link
                href={`/patients/${patientId}/compare`}
                className="px-4 py-2 bg-green-700 hover:bg-green-600 text-white text-sm font-medium rounded-lg transition-colors"
              >
                Compare Reports →
              </Link>
            )}
            <Link href="/patients" className="text-sm text-blue-400 hover:text-blue-300 py-2">
              ← All Patients
            </Link>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* Upload report */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
            <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">
              Upload Report
            </h2>
            <form onSubmit={handleUpload} className="space-y-3">
              <div className="flex gap-2">
                {(["baseline", "followup"] as const).map((t) => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => setReportType(t)}
                    className={`flex-1 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                      reportType === t
                        ? t === "baseline"
                          ? "bg-blue-700 text-white"
                          : "bg-purple-700 text-white"
                        : "bg-gray-800 text-gray-400 hover:text-white"
                    }`}
                  >
                    {t.charAt(0).toUpperCase() + t.slice(1)}
                  </button>
                ))}
              </div>
              <input
                value={reportLabel}
                onChange={(e) => setReportLabel(e.target.value)}
                placeholder="Label (e.g. 'After NAC protocol')"
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <input
                ref={fileRef}
                type="file"
                accept=".csv,.xlsx,.xls"
                required
                className="w-full text-sm text-gray-400 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-medium file:bg-gray-700 file:text-gray-200 hover:file:bg-gray-600"
              />
              <button
                type="submit"
                disabled={uploading}
                className="w-full py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-900 disabled:text-blue-400 text-white text-sm font-medium rounded-lg transition-colors"
              >
                {uploading ? "Analysing…" : "Upload & Analyse"}
              </button>
              {uploadMsg && <p className="text-green-400 text-xs">{uploadMsg}</p>}
              {uploadError && <p className="text-red-400 text-xs">{uploadError}</p>}
            </form>
          </div>

          {/* Log intervention */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
            <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">
              Log Intervention
            </h2>
            <form onSubmit={handleIntervention} className="space-y-3">
              <div className="flex gap-2">
                <div className="flex-1 flex flex-col gap-1">
                  <label className="text-xs text-gray-400">System</label>
                  <select
                    value={invSystem}
                    onChange={(e) => setInvSystem(e.target.value)}
                    className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {["Energy", "Detox", "Brain", "Inflammation", "Recovery"].map((s) => (
                      <option key={s}>{s}</option>
                    ))}
                  </select>
                </div>
                <div className="flex-1 flex flex-col gap-1">
                  <label className="text-xs text-gray-400">Adherence</label>
                  <select
                    value={invAdherence}
                    onChange={(e) => setInvAdherence(e.target.value)}
                    className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {["excellent", "good", "moderate", "poor", "unknown"].map((a) => (
                      <option key={a}>{a}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-gray-400">Interventions (comma-separated)</label>
                <input
                  required
                  value={invItems}
                  onChange={(e) => setInvItems(e.target.value)}
                  placeholder="NAC, Glutathione, Milk thistle"
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-gray-400">Notes</label>
                <input
                  value={invNotes}
                  onChange={(e) => setInvNotes(e.target.value)}
                  placeholder="Optional clinical notes"
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              {reports.length > 0 && (
                <div className="flex flex-col gap-1">
                  <label className="text-xs text-gray-400">Link to report (optional)</label>
                  <select
                    value={invReportId}
                    onChange={(e) => setInvReportId(e.target.value)}
                    className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">— none —</option>
                    {reports.map((r) => (
                      <option key={r.id} value={r.id}>
                        #{r.id} · {r.report_type} · {r.label ?? new Date(r.created_at).toLocaleDateString()}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              <button
                type="submit"
                disabled={savingInv}
                className="w-full py-2 bg-purple-700 hover:bg-purple-600 disabled:bg-purple-900 text-white text-sm font-medium rounded-lg transition-colors"
              >
                {savingInv ? "Saving…" : "Save Intervention"}
              </button>
              {invMsg && <p className="text-green-400 text-xs">{invMsg}</p>}
            </form>
          </div>
        </div>

        {/* Reports list */}
        {reports.length > 0 && (
          <div className="space-y-3">
            <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">Reports</h2>
            <div className="grid gap-3">
              {reports.map((r) => (
                <div key={r.id} className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span
                        className={`px-2 py-0.5 rounded text-xs font-semibold uppercase ${
                          r.report_type === "baseline"
                            ? "bg-blue-900 text-blue-200"
                            : "bg-purple-900 text-purple-200"
                        }`}
                      >
                        {r.report_type}
                      </span>
                      {r.label && <span className="text-sm text-gray-300">{r.label}</span>}
                    </div>
                    <span className="text-xs text-gray-500">
                      {new Date(r.created_at).toLocaleString()} · #{r.id}
                    </span>
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                    {Object.entries(r.system_scores).map(([sys, score]) => (
                      <ScoreBar key={sys} system={sys} score={score} />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
