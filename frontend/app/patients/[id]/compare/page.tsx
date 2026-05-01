"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type ComparisonRow = {
  system: string;
  baseline: number;
  followup: number;
  delta: number;
  delta_pct: number;
  status: "improved" | "worse" | "same";
  interpretation: string;
  intervention: string | null;
};

type ComparisonResult = {
  patient_id: number;
  patient_name: string;
  baseline: { report_id: number; report_type: string; label: string | null; date: string };
  followup: { report_id: number; report_type: string; label: string | null; date: string };
  summary: {
    overall_status: string;
    improved: number;
    same: number;
    worse: number;
    avg_delta: number;
    systems_total: number;
  };
  systems: ComparisonRow[];
  interventions: Array<{
    id: number;
    system: string;
    interventions: string[];
    adherence: string;
    notes: string | null;
    created_at: string;
  }>;
};

type ReportMeta = { id: number; report_type: string; label: string | null; created_at: string };

const STATUS_STYLES: Record<string, string> = {
  improved: "bg-green-950 border-green-700 text-green-300",
  worse: "bg-red-950 border-red-700 text-red-300",
  same: "bg-gray-900 border-gray-700 text-gray-400",
};

const STATUS_ICON: Record<string, string> = {
  improved: "↑",
  worse: "↓",
  same: "→",
};

const SYSTEM_COLORS: Record<string, string> = {
  Energy: "#eab308",
  Detox: "#22c55e",
  Brain: "#3b82f6",
  Inflammation: "#ef4444",
  Recovery: "#a855f7",
};

function DeltaBadge({ delta }: { delta: number }) {
  const positive = delta > 0;
  const neutral = delta === 0;
  return (
    <span
      className={`inline-flex items-center gap-0.5 px-2 py-0.5 rounded-full text-xs font-bold ${
        neutral
          ? "bg-gray-800 text-gray-400"
          : positive
          ? "bg-green-900 text-green-300"
          : "bg-red-900 text-red-300"
      }`}
    >
      {positive ? "+" : ""}
      {delta}
    </span>
  );
}

function ScoreBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-gray-400">
        <span>{label}</span>
        <span>{value}</span>
      </div>
      <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${Math.min(100, Math.max(0, value))}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

export default function ComparePage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const patientId = Number(params.id);

  const [result, setResult] = useState<ComparisonResult | null>(null);
  const [reports, setReports] = useState<ReportMeta[]>([]);
  const [baselineId, setBaselineId] = useState<string>(searchParams.get("baseline") ?? "");
  const [followupId, setFollowupId] = useState<string>(searchParams.get("followup") ?? "");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load available reports
  useEffect(() => {
    fetch(`${API}/patient/${patientId}/reports`)
      .then((r) => r.json())
      .then((d) => setReports(d.reports ?? []))
      .catch(() => {});
  }, [patientId]);

  const runComparison = useCallback(
    async (bId?: string, fId?: string) => {
      setLoading(true);
      setError(null);
      setResult(null);
      try {
        const qs = new URLSearchParams();
        if (bId) qs.set("baseline_report_id", bId);
        if (fId) qs.set("followup_report_id", fId);
        const url = `${API}/patient/${patientId}/compare${qs.toString() ? `?${qs}` : ""}`;
        const res = await fetch(url);
        if (!res.ok) {
          const d = await res.json().catch(() => ({ detail: "Unknown error" }));
          throw new Error(d.detail ?? "Comparison failed");
        }
        setResult(await res.json());
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Comparison failed");
      } finally {
        setLoading(false);
      }
    },
    [patientId]
  );

  // Auto-run on mount
  useEffect(() => {
    runComparison(baselineId || undefined, followupId || undefined);
  }, []);

  const overallColor =
    result?.summary.overall_status === "net_improvement"
      ? "text-green-400"
      : result?.summary.overall_status === "net_decline"
      ? "text-red-400"
      : "text-yellow-400";

  return (
    <main className="min-h-screen bg-gray-950 text-gray-100 p-6">
      <div className="max-w-5xl mx-auto space-y-8">

        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">
              {result ? result.patient_name : "Compare Reports"}
            </h1>
            <p className="text-gray-400 text-sm mt-1">Before vs after — what worked?</p>
          </div>
          <Link href={`/patients/${patientId}`} className="text-sm text-blue-400 hover:text-blue-300 py-2">
            ← Patient Detail
          </Link>
        </div>

        {/* Report selectors */}
        {reports.length >= 2 && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
            <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">
              Choose Reports to Compare
            </h2>
            <div className="flex flex-wrap gap-4 items-end">
              <div className="flex flex-col gap-1">
                <label className="text-xs text-gray-400">Baseline (before)</label>
                <select
                  value={baselineId}
                  onChange={(e) => setBaselineId(e.target.value)}
                  className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">— auto (oldest) —</option>
                  {reports.map((r) => (
                    <option key={r.id} value={r.id}>
                      #{r.id} · {r.report_type} · {r.label ?? new Date(r.created_at).toLocaleDateString()}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-gray-400">Follow-up (after)</label>
                <select
                  value={followupId}
                  onChange={(e) => setFollowupId(e.target.value)}
                  className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">— auto (latest) —</option>
                  {reports.map((r) => (
                    <option key={r.id} value={r.id}>
                      #{r.id} · {r.report_type} · {r.label ?? new Date(r.created_at).toLocaleDateString()}
                    </option>
                  ))}
                </select>
              </div>
              <button
                onClick={() => runComparison(baselineId || undefined, followupId || undefined)}
                disabled={loading}
                className="px-5 py-2 bg-blue-700 hover:bg-blue-600 disabled:bg-blue-900 text-white text-sm font-medium rounded-lg transition-colors"
              >
                {loading ? "Comparing…" : "Compare"}
              </button>
            </div>
          </div>
        )}

        {error && (
          <div className="bg-red-950 border border-red-700 text-red-300 rounded-xl px-5 py-4 text-sm">
            {error}
          </div>
        )}

        {loading && (
          <div className="text-center text-gray-400 py-12">Comparing reports…</div>
        )}

        {result && (
          <>
            {/* Period header */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="bg-blue-950 border border-blue-800 rounded-xl p-4">
                <p className="text-xs text-blue-300 font-semibold uppercase mb-1">Baseline</p>
                <p className="text-white font-medium">
                  {result.baseline.label ?? `Report #${result.baseline.report_id}`}
                </p>
                <p className="text-blue-300 text-xs">{new Date(result.baseline.date).toLocaleDateString()}</p>
              </div>
              <div className="flex items-center justify-center">
                <div className="text-center">
                  <p className={`text-3xl font-black ${overallColor}`}>
                    {result.summary.overall_status === "net_improvement"
                      ? "↑ Net Improvement"
                      : result.summary.overall_status === "net_decline"
                      ? "↓ Net Decline"
                      : "↔ Mixed"}
                  </p>
                  <p className="text-xs text-gray-400 mt-1">
                    avg Δ {result.summary.avg_delta > 0 ? "+" : ""}
                    {result.summary.avg_delta} pts across {result.summary.systems_total} systems
                  </p>
                </div>
              </div>
              <div className="bg-purple-950 border border-purple-800 rounded-xl p-4 sm:text-right">
                <p className="text-xs text-purple-300 font-semibold uppercase mb-1">Follow-up</p>
                <p className="text-white font-medium">
                  {result.followup.label ?? `Report #${result.followup.report_id}`}
                </p>
                <p className="text-purple-300 text-xs">{new Date(result.followup.date).toLocaleDateString()}</p>
              </div>
            </div>

            {/* Quick stats */}
            <div className="grid grid-cols-3 gap-3">
              {[
                { label: "Improved", value: result.summary.improved, color: "text-green-400" },
                { label: "Same", value: result.summary.same, color: "text-gray-400" },
                { label: "Worse", value: result.summary.worse, color: "text-red-400" },
              ].map(({ label, value, color }) => (
                <div key={label} className="bg-gray-900 border border-gray-800 rounded-xl p-4 text-center">
                  <p className={`text-3xl font-black ${color}`}>{value}</p>
                  <p className="text-gray-400 text-xs mt-1">{label}</p>
                </div>
              ))}
            </div>

            {/* Per-system comparison */}
            <div className="space-y-3">
              <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">
                System-by-System Results
              </h2>
              {result.systems.map((row) => {
                const color = SYSTEM_COLORS[row.system] ?? "#6b7280";
                return (
                  <div
                    key={row.system}
                    className={`rounded-xl border p-5 space-y-3 ${STATUS_STYLES[row.status]}`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className="text-lg font-bold">{STATUS_ICON[row.status]}</span>
                        <div>
                          <p className="font-semibold text-white">{row.system}</p>
                          <p className="text-xs opacity-80">{row.interpretation}</p>
                        </div>
                      </div>
                      <DeltaBadge delta={row.delta} />
                    </div>

                    {/* Score bars */}
                    <div className="grid grid-cols-2 gap-4">
                      <ScoreBar label="Before" value={row.baseline} color="#6b7280" />
                      <ScoreBar label="After" value={row.followup} color={color} />
                    </div>

                    {/* Intervention label */}
                    {row.intervention && (
                      <div className="flex items-center gap-2 bg-black bg-opacity-20 rounded-lg px-3 py-2">
                        <span className="text-xs text-gray-400">Intervention:</span>
                        <span className="text-xs font-medium text-white">{row.intervention}</span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Interventions timeline */}
            {result.interventions.length > 0 && (
              <div className="space-y-3">
                <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">
                  Interventions in This Period
                </h2>
                <div className="space-y-2">
                  {result.interventions.map((inv) => (
                    <div
                      key={inv.id}
                      className="bg-gray-900 border border-gray-800 rounded-xl px-5 py-3 flex items-start justify-between gap-4"
                    >
                      <div className="space-y-0.5">
                        <p className="text-sm font-medium text-white">
                          <span className="text-gray-400 text-xs mr-2 uppercase">{inv.system}</span>
                          {Array.isArray(inv.interventions) ? inv.interventions.join(", ") : "—"}
                        </p>
                        {inv.notes && <p className="text-xs text-gray-400">{inv.notes}</p>}
                      </div>
                      <div className="text-right shrink-0">
                        <span className="text-xs px-2 py-0.5 bg-gray-800 text-gray-300 rounded-full">
                          {inv.adherence}
                        </span>
                        <p className="text-xs text-gray-500 mt-1">
                          {new Date(inv.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </main>
  );
}
