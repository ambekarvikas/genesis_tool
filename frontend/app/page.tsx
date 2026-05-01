"use client";

import { useEffect, useRef, useState } from "react";

// ─── Types ────────────────────────────────────────────────────────────────────
type PathwayRow = {
  pathway: string;
  category: string;
  kegg_id?: string;
  score: number;
  n_genes?: number | null;
  median_fc?: number | null;
};

type PathwayGeneRow = {
  gene_symbol: string;
  expression_value: number | null;
};

type CategoryGroup = {
  category: string;
  avg_score: number;
  pathway_count: number;
  matched_count: number;
  pathways: PathwayRow[];
};

type Patient = {
  id: number;
  name: string;
  age: number;
  gender: string;
};

type Insight = {
  issue: string;
  impact: string;
  action: string[];
  priority: "Critical" | "High" | "Moderate" | "Low";
  severity?: "Critical" | "High" | "Moderate" | "Low";
  urgency?: "Immediate" | "High" | "Medium" | "Low";
  rank?: number;
  confidence?: string;
  clinical_label?: string;
  focus_area?: string;
  goal?: string;
  symptoms?: string[];
  expected_outcome?: string;
  recommended_actions?: string[];
  actions_structured?: { lifestyle?: string[]; nutrition?: string[]; clinical?: string[] };
  trend?: { status: string; interpretation: string };
  pathway?: string;
  n_genes?: number;
  system: string;
  score: number;
};

type FocusArea = {
  title: string;
  reason: string;
  system: string;
  urgency: string;
  goal?: string;
  current_score?: number;
  target_score?: number;
};

type SystemScores = {
  Energy: number;
  Inflammation: number;
  Detox: number;
  Brain: number;
  Recovery: number;
};

type HistoryRow = {
  date: string;
  systems: Partial<SystemScores>;
};

type AnalyzeResult = {
  patient_id: number;
  report_id: number;
  created_at: string;
  summary?: {
    overall?: string;
    top_issues?: Array<{
      system: string;
      issue: string;
      priority: string;
      score: number;
    }>;
  };
  systems: Array<{
    system: keyof SystemScores;
    label?: string;
    score: number;
    priority?: string;
    priority_score?: number;
    issue?: string;
    impact?: string;
    symptoms?: string[];
    actions?: { lifestyle?: string[]; nutrition?: string[]; clinical?: string[] } | string[];
    expected_outcome?: string;
    confidence?: string;
    reason?: {
      n_genes?: number;
      median_fc?: number | null;
    };
    trend?: { status: string; interpretation: string };
    goal?: string;
    urgency?: string;
    rank?: number;
  }>;
  system_scores?: SystemScores;
  top_issues: Insight[];
  insights: Insight[];
  focus_areas?: FocusArea[];
  pathways: PathwayRow[];
  pathway_genes?: Record<string, PathwayGeneRow[]>;
  pathway: {
    status: string;
    runner?: string;
    genes_output_file?: string;
    categories?: CategoryGroup[];
    scores?: PathwayRow[];
  };
  scores?: {
    source_column?: string;
    rows_total?: number;
    rows_used?: number;
  };
};

// ─── Helpers ──────────────────────────────────────────────────────────────────
function scoreColor(s: number): string {
  if (s >= 65) return "#16a34a";
  if (s >= 55) return "#65a30d";
  if (s >= 45) return "#64748b";
  if (s >= 35) return "#ea580c";
  return "#dc2626";
}

function scoreLabel(s: number): string {
  if (s >= 70) return "High";
  if (s >= 55) return "Elevated";
  if (s >= 45) return "Normal";
  if (s >= 35) return "Low";
  return "Suppressed";
}

function priorityColor(priority: Insight["priority"]): string {
  if (priority === "Critical") return "#991b1b";
  if (priority === "High") return "#dc2626";
  if (priority === "Moderate") return "#ea580c";
  return "#16a34a";
}

function confidenceFromGenes(nGenes: number | null | undefined): string {
  const genes = nGenes ?? 0;
  if (genes >= 30) return "High";
  if (genes >= 10) return "Medium";
  return "Low";
}

function trendSymbol(delta: number): string {
  if (delta > 0) return "↑";
  if (delta < 0) return "↓";
  return "→";
}

function formatFC(fc: number | null | undefined): string {
  if (fc == null) return "—";
  return fc > 0 ? `+${fc.toFixed(3)}` : fc.toFixed(3);
}

function fcColor(fc: number | null | undefined): string | undefined {
  if (fc == null) return undefined;
  return fc > 0 ? "#16a34a" : fc < 0 ? "#dc2626" : "#64748b";
}

function formatGeneExpression(value: number | null | undefined): string {
  if (value == null) return "—";
  return value > 0 ? `+${value.toFixed(4)}` : value.toFixed(4);
}

function prettyCategory(cat: string): string {
  return cat.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

// ─── Mini score bar ───────────────────────────────────────────────────────────
function ScoreBar({ score }: { score: number }) {
  const pct = `${score}%`;
  const color = scoreColor(score);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, flex: 1 }}>
      <div style={{ flex: 1, height: 8, background: "#e2e8f0", borderRadius: 4, overflow: "hidden" }}>
        <div style={{ width: pct, height: "100%", background: color, borderRadius: 4, transition: "width .4s" }} />
      </div>
      <span style={{ fontSize: 13, fontWeight: 600, color, minWidth: 28, textAlign: "right" }}>{score}</span>
    </div>
  );
}

// ─── Category card with collapsible table ─────────────────────────────────────
function CategoryCard({ group, pathwayGenes }: { group: CategoryGroup; pathwayGenes: Record<string, PathwayGeneRow[]> }) {
  const [open, setOpen] = useState(false);
  const { category, avg_score, pathway_count, matched_count, pathways } = group;

  return (
    <div style={{ border: "1px solid #e2e8f0", borderRadius: 10, overflow: "hidden", marginBottom: 10 }}>
      {/* Header row */}
      <button
        onClick={() => setOpen((o) => !o)}
        style={{
          width: "100%", display: "flex", alignItems: "center", gap: 12,
          padding: "12px 16px", background: "#f8fafc", border: "none", cursor: "pointer",
          textAlign: "left",
        }}
      >
        <span style={{ fontWeight: 600, fontSize: 14, minWidth: 220 }}>{prettyCategory(category)}</span>
        <ScoreBar score={avg_score} />
        <span style={{ fontSize: 12, color: "#64748b", minWidth: 80, textAlign: "right" }}>
          {matched_count}/{pathway_count} matched
        </span>
        <span style={{ fontSize: 12, color: "#94a3b8", minWidth: 20 }}>{open ? "▲" : "▼"}</span>
      </button>

      {/* Expanded pathway table */}
      {open && (
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ background: "#f1f5f9" }}>
                <th style={{ textAlign: "left",   padding: "6px 12px", borderBottom: "1px solid #e2e8f0" }}>Pathway</th>
                <th style={{ textAlign: "center", padding: "6px 10px", borderBottom: "1px solid #e2e8f0" }}>Score</th>
                <th style={{ textAlign: "center", padding: "6px 10px", borderBottom: "1px solid #e2e8f0" }}>Status</th>
                <th style={{ textAlign: "center", padding: "6px 10px", borderBottom: "1px solid #e2e8f0" }}>Confidence</th>
                <th style={{ textAlign: "center", padding: "6px 10px", borderBottom: "1px solid #e2e8f0" }}>Genes</th>
                <th style={{ textAlign: "center", padding: "6px 10px", borderBottom: "1px solid #e2e8f0" }}>Median log2FC</th>
                <th style={{ textAlign: "center", padding: "6px 10px", borderBottom: "1px solid #e2e8f0" }}>Drill-down</th>
              </tr>
            </thead>
            <tbody>
              {pathways.map((row) => {
                const genes = row.kegg_id ? (pathwayGenes[row.kegg_id] ?? []) : [];
                return (
                <tr key={row.pathway} style={{ borderBottom: "1px solid #f1f5f9" }}>
                  <td style={{ padding: "7px 12px", color: "#1e293b" }}>
                    {row.pathway.replace(/_/g, " ")}
                  </td>
                  <td style={{ padding: "7px 10px", textAlign: "center", fontWeight: 600, color: scoreColor(row.score) }}>
                    {row.score}
                  </td>
                  <td style={{ padding: "7px 10px", textAlign: "center", fontSize: 12, color: scoreColor(row.score) }}>
                    {scoreLabel(row.score)}
                  </td>
                  <td style={{ padding: "7px 10px", textAlign: "center", color: "#334155" }}>
                    {confidenceFromGenes(row.n_genes)}
                  </td>
                  <td style={{ padding: "7px 10px", textAlign: "center", color: "#475569" }}>
                    {row.n_genes ?? "—"}
                  </td>
                  <td style={{ padding: "7px 10px", textAlign: "center", fontWeight: 500, color: fcColor(row.median_fc) }}>
                    {formatFC(row.median_fc)}
                  </td>
                  <td style={{ padding: "7px 10px", textAlign: "left", minWidth: 280 }}>
                    {genes.length === 0 ? (
                      <span style={{ color: "#94a3b8", fontSize: 12 }}>No gene matches</span>
                    ) : (
                      <details>
                        <summary style={{ cursor: "pointer", color: "#1d4ed8", fontSize: 12 }}>
                          View genes ({genes.length})
                        </summary>
                        <div style={{ marginTop: 8, maxHeight: 220, overflowY: "auto", border: "1px solid #e2e8f0", borderRadius: 6 }}>
                          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                            <thead>
                              <tr style={{ background: "#f8fafc" }}>
                                <th style={{ textAlign: "left", padding: "6px 8px", borderBottom: "1px solid #e2e8f0" }}>Gene</th>
                                <th style={{ textAlign: "center", padding: "6px 8px", borderBottom: "1px solid #e2e8f0" }}>Expression (log2FC)</th>
                              </tr>
                            </thead>
                            <tbody>
                              {genes.map((gene, index) => (
                                <tr key={`${row.pathway}-${gene.gene_symbol}-${index}`} style={{ borderBottom: "1px solid #f1f5f9" }}>
                                  <td style={{ padding: "6px 8px", fontWeight: 600, color: "#1e293b" }}>{gene.gene_symbol}</td>
                                  <td style={{
                                    padding: "6px 8px",
                                    textAlign: "center",
                                    color:
                                      gene.expression_value == null
                                        ? "#64748b"
                                        : gene.expression_value > 0
                                          ? "#166534"
                                          : gene.expression_value < 0
                                            ? "#b91c1c"
                                            : "#475569",
                                    fontWeight: 600,
                                  }}>
                                    {formatGeneExpression(gene.expression_value)}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </details>
                    )}
                  </td>
                </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────
export default function Home() {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [selectedFileName, setSelectedFileName] = useState("");
  const [patients, setPatients] = useState<Patient[]>([]);
  const [selectedPatientId, setSelectedPatientId] = useState<number | "">("");
  const [result, setResult] = useState<AnalyzeResult | null>(null);
  const [history, setHistory] = useState<HistoryRow[]>([]);
  const [error, setError] = useState<string>("");
  const [success, setSuccess] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [loadingPatients, setLoadingPatients] = useState(true);

  const loadPatients = async () => {
    setLoadingPatients(true);
    try {
      const response = await fetch("http://127.0.0.1:8091/patients");
      if (!response.ok) throw new Error("Failed to load patients");
      const rows: Patient[] = await response.json();
      setPatients(rows);
      if (rows.length > 0) {
        setSelectedPatientId(rows[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load patients");
    } finally {
      setLoadingPatients(false);
    }
  };

  const loadHistory = async (patientId: number) => {
    try {
      const response = await fetch(`http://127.0.0.1:8091/patient/${patientId}/history`);
      if (!response.ok) throw new Error("Failed to load patient history");
      const rows: HistoryRow[] = await response.json();
      setHistory(rows);
    } catch {
      setHistory([]);
    }
  };

  useEffect(() => {
    loadPatients();
  }, []);

  useEffect(() => {
    if (typeof selectedPatientId === "number") {
      loadHistory(selectedPatientId);
    }
  }, [selectedPatientId]);

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] ?? null;
    setSelectedFileName(f ? f.name : "");
    setError("");
    setSuccess("");
    setResult(null);
  };

  const uploadFile = async () => {
    const selectedFile = fileInputRef.current?.files?.[0] ?? null;
    if (!selectedFile) { setError("Please choose a CSV or Excel file first."); return; }
    if (selectedPatientId === "") { setError("Please select a patient first."); return; }

    setLoading(true);
    setError("");
    setSuccess("");

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("patient_id", String(selectedPatientId));

    try {
      const response = await fetch("http://127.0.0.1:8091/analyze", { method: "POST", body: formData });

      if (!response.ok) {
        let msg = "Upload failed.";
        try { const b = await response.json(); if (b?.detail) msg = b.detail; } catch { /* ignore */ }
        throw new Error(msg);
      }

      const payload: AnalyzeResult = await response.json();
      setResult(payload);
      await loadHistory(payload.patient_id);
      setSuccess("File processed successfully.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  const categories = result?.pathway?.categories ?? [];
  const pathwayGenes = result?.pathway_genes ?? {};
  const systemScores: SystemScores = (() => {
    if (!result) {
      return { Energy: 50, Inflammation: 50, Detox: 50, Brain: 50, Recovery: 50 };
    }
    if (result.system_scores) return result.system_scores;
    const fallback: SystemScores = { Energy: 50, Inflammation: 50, Detox: 50, Brain: 50, Recovery: 50 };
    for (const row of result.systems ?? []) {
      fallback[row.system] = row.score;
    }
    return fallback;
  })();
  const totalPathways = categories.reduce((a, c) => a + c.pathway_count, 0);
  const totalMatched = categories.reduce((a, c) => a + c.matched_count, 0);
  const focusAreas = result?.focus_areas ?? [];
  const effectiveFocusAreas: FocusArea[] = (() => {
    if (focusAreas.length > 0) return focusAreas;

    const fromIssues: FocusArea[] = (result?.top_issues ?? [])
      .slice(0, 3)
      .map((item, index) => ({
        title: item.focus_area || `${item.system} system stabilization`,
        reason: item.impact,
        system: item.system,
        urgency: item.urgency || (index === 0 ? "High" : "Medium"),
        goal: item.goal || `Improve ${item.system} score from ${item.score}`,
      }));

    if (fromIssues.length > 0) {
      const seen = new Set<string>();
      return fromIssues.filter((row) => {
        const key = `${row.system}::${row.title}`;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      }).slice(0, 3);
    }

    const systemRows = Object.entries(systemScores) as Array<[keyof SystemScores, number]>;
    const byScore = [...systemRows].sort((a, b) => a[1] - b[1]).slice(0, 2);
    return byScore.map(([system, score]) => ({
      title: `${system} resilience reset`,
      reason: `Current ${system} score is ${score}. Prioritize sleep, nutrition, hydration, and adherence to care plan to improve this domain over the next 30 days.`,
      system,
      urgency: score < 45 ? "High" : "Medium",
      goal: `Increase ${system} score from ${score} to ${Math.min(75, score + 15)}`,
    }));
  })();

  const selectedPatient = patients.find((patient) => patient.id === selectedPatientId) ?? null;
  const previousHistory = history.length >= 2 ? history[history.length - 2] : null;

  const topActions = Array.from(
    new Set(
      (result?.top_issues ?? []).flatMap((item) => item.recommended_actions ?? item.action ?? [])
    )
  ).slice(0, 5);

  const buildReportHtml = (kind: "client" | "doctor"): string => {
    if (!result) return "";

    const escapeHtml = (value: string) =>
      value
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\"/g, "&quot;")
        .replace(/'/g, "&#39;");

    const patientName = selectedPatient?.name ?? `ID ${result.patient_id}`;
    const generatedAt = new Date(result.created_at).toLocaleString();

    const systemsHtml = (Object.entries(systemScores) as Array<[keyof SystemScores, number]>)
      .map(([system, value]) => `<tr><td>${escapeHtml(system)}</td><td style="text-align:center;">${value}</td></tr>`)
      .join("");

    const issueRowsHtml = (result.top_issues ?? [])
      .map((issue, index) => {
        const structured = issue.actions_structured;
        let actionsHtml = "";
        if (structured && Object.values(structured).some(a => (a ?? []).length > 0)) {
          const catColors: Record<string, string> = { lifestyle: "#1d4ed8", nutrition: "#15803d", clinical: "#b45309" };
          actionsHtml = `<div style="margin-top:6px;"><strong>Actions:</strong>${(["lifestyle", "nutrition", "clinical"] as const)
            .map(cat => {
              const acts = structured[cat] ?? [];
              if (acts.length === 0) return "";
              const items = acts.map((a: string) => `<li>${escapeHtml(a)}</li>`).join("");
              return `<div style="margin-top:4px;"><span style="font-weight:700;color:${catColors[cat]};text-transform:capitalize;">${cat}:</span><ul style="margin:2px 0 0 18px;">${items}</ul></div>`;
            }).join("")}</div>`;
        } else {
          const flatActs = (issue.recommended_actions ?? issue.action ?? []).map((a: string) => `<li>${escapeHtml(a)}</li>`).join("");
          if (flatActs) actionsHtml = `<div style="margin-top:6px;"><strong>Recommended Actions:</strong><ul style="margin:6px 0 0 18px;">${flatActs}</ul></div>`;
        }
        const symptomsHtml = (issue.symptoms ?? []).length > 0
          ? `<div style="margin-top:4px;"><strong>Symptoms:</strong> ${escapeHtml((issue.symptoms ?? []).join(" · "))}</div>`
          : "";
        const outcomeHtml = issue.expected_outcome
          ? `<div style="margin-top:4px;color:#166534;"><strong>Expected outcome:</strong> ${escapeHtml(issue.expected_outcome)}</div>`
          : "";
        const trendHtml = issue.trend?.interpretation
          ? `<div style="margin-top:4px;color:#64748b;font-style:italic;font-size:12px;">${escapeHtml(issue.trend.interpretation)}</div>`
          : "";
        return `
          <div style="margin-bottom:14px;padding:10px;border:1px solid #e2e8f0;border-radius:8px;">
            <div><strong>#${issue.rank ?? index + 1} ${(issue.severity ?? issue.priority).toUpperCase()}</strong> - ${escapeHtml(issue.clinical_label ?? issue.issue)}</div>
            <div style="margin-top:4px;"><strong>Impact:</strong> ${escapeHtml(issue.impact)}</div>
            ${symptomsHtml}
            <div style="margin-top:4px;"><strong>Urgency:</strong> ${escapeHtml(issue.urgency ?? "Medium")} | <strong>Confidence:</strong> ${escapeHtml(issue.confidence ?? "Medium")} | <strong>Score:</strong> ${issue.score}</div>
            ${trendHtml}
            ${outcomeHtml}
            ${actionsHtml}
          </div>`;
      })
      .join("");

    const focusHtml = (effectiveFocusAreas ?? [])
      .map((area, index) => {
        const goalLine = area.goal ? `<br/><span style="color:#166534;font-weight:600;">🎯 Goal: ${escapeHtml(area.goal)}</span>` : "";
        return `<li><strong>${index + 1}. ${escapeHtml(area.title)}</strong> (${escapeHtml(area.urgency)})${goalLine}<br/>${escapeHtml(area.reason)}</li>`;
      })
      .join("");

    const monthlyActionsHtml = topActions.length > 0
      ? `<ol>${topActions.map((action) => `<li>${escapeHtml(action)}</li>`).join("")}</ol>`
      : "<p>Follow your clinician-approved nutrition, sleep, movement, and supplement plan, then re-test in 4–6 weeks to confirm score movement.</p>";

    const expectedOutcomesHtml = (result.top_issues ?? [])
      .slice(0, 3)
      .map((issue) => issue.expected_outcome ? `<li>${escapeHtml(issue.expected_outcome)}</li>` : "")
      .filter(Boolean)
      .join("");

    const lowPathways = [...(result.pathways ?? [])]
      .filter((row) => (row.n_genes ?? 0) > 0)
      .sort((a, b) => a.score - b.score)
      .slice(0, 12);

    const pathwayTableHtml = lowPathways
      .map(
        (row) =>
          `<tr><td>${escapeHtml(row.pathway.replace(/_/g, " "))}</td><td>${escapeHtml(row.kegg_id ?? "")}</td><td style="text-align:center;">${row.score}</td><td style="text-align:center;">${row.n_genes ?? "—"}</td><td style="text-align:center;">${formatFC(row.median_fc)}</td></tr>`
      )
      .join("");

    const doctorGeneSections = (result.top_issues ?? [])
      .filter((issue) => !!issue.pathway)
      .slice(0, 3)
      .map((issue) => {
        const pathwayId = result.pathways.find((p) => p.pathway === issue.pathway)?.kegg_id;
        const genes = pathwayId ? (pathwayGenes[pathwayId] ?? []) : [];
        if (!pathwayId || genes.length === 0) {
          return `
            <div style="margin-bottom:12px;">
              <strong>${escapeHtml((issue.pathway ?? "Unknown").replace(/_/g, " "))}</strong>
              <div>No gene-level drill-down rows available.</div>
            </div>`;
        }
        const topGenes = genes.slice(0, 20)
          .map((gene) => `<tr><td>${escapeHtml(gene.gene_symbol)}</td><td style="text-align:center;">${formatGeneExpression(gene.expression_value)}</td></tr>`)
          .join("");
        return `
          <div style="margin-bottom:14px;">
            <strong>${escapeHtml((issue.pathway ?? "Unknown").replace(/_/g, " "))}</strong> (${escapeHtml(pathwayId)})
            <table style="width:100%;border-collapse:collapse;margin-top:6px;">
              <thead><tr><th style="text-align:left;">Gene</th><th style="text-align:center;">Expression (log2FC)</th></tr></thead>
              <tbody>${topGenes}</tbody>
            </table>
          </div>`;
      })
      .join("");

    const html = kind === "client"
      ? `
        <html><head><meta charset="utf-8"/><title>Client Report</title>
        <style>
          body{font-family:Arial,sans-serif;max-width:900px;margin:16px auto;padding:0 14px;color:#0f172a;}
          h1,h2{color:#0f172a;}
          table{width:100%;border-collapse:collapse;}
          th,td{padding:6px 8px;border:1px solid #e2e8f0;}
          @media print{
            body{max-width:100%;margin:0;padding:10mm 12mm;font-size:11pt;}
            button{display:none!important;}
            h2{page-break-after:avoid;}
            .no-break{page-break-inside:avoid;}
            @page{margin:15mm;}
          }
        </style>
        </head>
        <body>
          <h1>Rhino Gene Intelligence &ndash; Client Report</h1>
          <p><strong>Patient:</strong> ${escapeHtml(patientName)}<br/><strong>Generated:</strong> ${escapeHtml(generatedAt)}</p>
          <h2>Executive Summary</h2>
          <p>${escapeHtml(result.summary?.overall ?? "Top systems require targeted intervention over the next 30 days.")}</p>
          <h2>System Snapshot</h2>
          <table>${systemsHtml}</table>
          <h2>Key Issues</h2>
          ${issueRowsHtml || "<p>No major issues found.</p>"}
          <h2>Focus Areas (Next 30 Days)</h2>
          <ol>${focusHtml || "<li>No focus areas generated.</li>"}</ol>
          <h2>Actions</h2>
          ${monthlyActionsHtml}
          <h2>Expected Outcomes</h2>
          <ol>${expectedOutcomesHtml || "<li>Expected outcomes will populate after issue generation.</li>"}</ol>
          <div style="margin-top:20px;"><button onclick="window.print()" style="background:#0f766e;color:#fff;border:none;padding:9px 16px;border-radius:6px;cursor:pointer;font-size:13px;">&#128438; Print / Save as PDF</button></div>
        </body></html>`
      : `
        <html><head><meta charset="utf-8"/><title>Doctor Report</title>
        <style>
          body{font-family:Arial,sans-serif;max-width:1020px;margin:16px auto;padding:0 14px;color:#0f172a;}
          h1,h2{color:#0f172a;}
          table{width:100%;border-collapse:collapse;}
          th,td{padding:6px 8px;border:1px solid #e2e8f0;}
          @media print{
            body{max-width:100%;margin:0;padding:10mm 12mm;font-size:10.5pt;}
            button{display:none!important;}
            h2{page-break-after:avoid;}
            .no-break{page-break-inside:avoid;}
            @page{margin:15mm;}
          }
        </style>
        </head>
        <body>
          <h1>Rhino Gene Intelligence &ndash; Doctor Report</h1>
          <p><strong>Patient:</strong> ${escapeHtml(patientName)}<br/><strong>Patient ID:</strong> ${result.patient_id}<br/><strong>Report ID:</strong> ${result.report_id}<br/><strong>Generated:</strong> ${escapeHtml(generatedAt)}</p>
          <h2>Executive Summary</h2>
          <p>${escapeHtml(result.summary?.overall ?? "Top systems require targeted intervention over the next 30 days.")}</p>
          <h2>System Scores</h2>
          <table>${systemsHtml}</table>
          <h2>Key Issues</h2>
          ${issueRowsHtml || "<p>No major issues found.</p>"}
          <h2>Actions</h2>
          ${monthlyActionsHtml}
          <h2>Expected Outcomes</h2>
          <ol>${expectedOutcomesHtml || "<li>Expected outcomes will populate after issue generation.</li>"}</ol>
          <h2>Lowest Pathway Scores (Matched)</h2>
          <table border="1" cellpadding="6">
            <thead><tr><th style="text-align:left;">Pathway</th><th style="text-align:left;">KEGG ID</th><th>Score</th><th>Genes</th><th>Median log2FC</th></tr></thead>
            <tbody>${pathwayTableHtml || "<tr><td colspan='5'>No matched pathways available.</td></tr>"}</tbody>
          </table>
          <h2>Gene Drill-down (Top Issue Pathways)</h2>
          ${doctorGeneSections || "<p>No gene drill-down sections available.</p>"}
          <h2>Technical Appendix</h2>
          <p><strong>Source column:</strong> ${escapeHtml(result.scores?.source_column ?? "N/A")}<br/>
          <strong>Rows:</strong> ${result.scores?.rows_used ?? "N/A"} / ${result.scores?.rows_total ?? "N/A"}<br/>
          <strong>R runner:</strong> ${escapeHtml(result.pathway.runner ?? "N/A")}<br/>
          <strong>Status:</strong> ${escapeHtml(result.pathway.status)}</p>
          <div style="margin-top:20px;"><button onclick="window.print()" style="background:#1d4ed8;color:#fff;border:none;padding:9px 16px;border-radius:6px;cursor:pointer;font-size:13px;">&#128438; Print / Save as PDF</button></div>
        </body></html>`;

    return html;
  };

  const downloadReport = (kind: "client" | "doctor") => {
    if (!result) return;
    const html = buildReportHtml(kind);
    const blob = new Blob([html], { type: "text/html;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${kind}_report_patient_${result.patient_id}_report_${result.report_id}.html`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  };

  const printReport = (kind: "client" | "doctor") => {
    if (!result) return;
    const html = buildReportHtml(kind);
    const win = window.open("", "_blank");
    if (!win) return;
    win.document.open();
    win.document.write(html);
    win.document.close();
    win.focus();
    win.addEventListener("load", () => {
      win.print();
    });
  };

  return (
    <div style={{ padding: "20px 24px", fontFamily: "Arial, sans-serif", maxWidth: 860, margin: "0 auto" }}>
      <h1 style={{ marginBottom: 4, fontSize: 24 }}>Rhino Gene Intelligence</h1>
      <p style={{ marginTop: 0, marginBottom: 18, color: "#64748b", fontSize: 14 }}>
        Upload gene expression data, generate system scores, and track patient progress over time.
      </p>

      {/* Upload row */}
      <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap", marginBottom: 6 }}>
        <select
          value={selectedPatientId}
          onChange={(event) => setSelectedPatientId(event.target.value ? Number(event.target.value) : "")}
          disabled={loadingPatients}
          style={{ fontSize: 14, padding: "8px 10px", borderRadius: 6, border: "1px solid #cbd5e1" }}
        >
          {patients.map((patient) => (
            <option key={patient.id} value={patient.id}>
              {patient.name} ({patient.gender}, {patient.age})
            </option>
          ))}
        </select>
        <input ref={fileInputRef} type="file" accept=".csv,.xlsx,.xls" onChange={onFileChange} style={{ fontSize: 14 }} />
        <span style={{ fontSize: 13, color: "#64748b" }}>
          {selectedFileName ? `Selected: ${selectedFileName}` : "No file selected"}
        </span>
        <button
          type="button" onClick={uploadFile} disabled={loading}
          style={{
            background: loading ? "#9ca3af" : "#2563eb", color: "#fff", border: "none",
            padding: "10px 18px", borderRadius: 6, cursor: loading ? "not-allowed" : "pointer", fontSize: 14,
          }}
        >
          {loading ? "Analyzing…" : "Analyze"}
        </button>
      </div>
      {loading && (
        <p style={{ fontSize: 13, color: "#64748b" }}>
          Fetching KEGG gene sets and scoring pathways — first run may take ~60 s while gene lists are downloaded. Subsequent runs use the local cache and finish in a few seconds.
        </p>
      )}

      {error && <div style={{ marginTop: 12, color: "#b91c1c", fontSize: 14 }}>{error}</div>}
      {success && <div style={{ marginTop: 12, color: "#166534", fontSize: 14 }}>{success}</div>}

      {result && (
        <div style={{ marginTop: 24, display: "grid", gap: 20 }}>

          <div style={{ padding: 12, borderRadius: 8, border: "1px solid #e2e8f0", background: "#f8fafc", fontSize: 14, display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
            <div>
              Patient: <strong>{selectedPatient?.name ?? `ID ${result.patient_id}`}</strong> · Report ID: <strong>{result.report_id}</strong>
            </div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button
                type="button"
                onClick={() => downloadReport("client")}
                style={{ background: "#0f766e", color: "#fff", border: "none", padding: "7px 10px", borderRadius: 6, cursor: "pointer", fontSize: 12 }}
              >
                ⬇ Client Report
              </button>
              <button
                type="button"
                onClick={() => printReport("client")}
                style={{ background: "#134e4a", color: "#fff", border: "none", padding: "7px 10px", borderRadius: 6, cursor: "pointer", fontSize: 12 }}
              >
                🖨 Client PDF
              </button>
              <button
                type="button"
                onClick={() => downloadReport("doctor")}
                style={{ background: "#1d4ed8", color: "#fff", border: "none", padding: "7px 10px", borderRadius: 6, cursor: "pointer", fontSize: 12 }}
              >
                ⬇ Doctor Report
              </button>
              <button
                type="button"
                onClick={() => printReport("doctor")}
                style={{ background: "#1e3a8a", color: "#fff", border: "none", padding: "7px 10px", borderRadius: 6, cursor: "pointer", fontSize: 12 }}
              >
                🖨 Doctor PDF
              </button>
            </div>
          </div>

          {/* Summary bar */}
          <div style={{
            display: "flex", gap: 20, flexWrap: "wrap",
            background: "#f0f9ff", border: "1px solid #bae6fd", borderRadius: 10, padding: "12px 18px",
          }}>
            <div><span style={{ fontSize: 12, color: "#64748b" }}>Energy</span><br/>
              <strong style={{ fontSize: 14, color: scoreColor(systemScores.Energy) }}>{systemScores.Energy}</strong></div>
            <div><span style={{ fontSize: 12, color: "#64748b" }}>Inflammation</span><br/>
              <strong style={{ fontSize: 14, color: scoreColor(systemScores.Inflammation) }}>{systemScores.Inflammation}</strong></div>
            <div><span style={{ fontSize: 12, color: "#64748b" }}>Detox</span><br/>
              <strong style={{ fontSize: 14, color: scoreColor(systemScores.Detox) }}>{systemScores.Detox}</strong></div>
            <div><span style={{ fontSize: 12, color: "#64748b" }}>Brain</span><br/>
              <strong style={{ fontSize: 14, color: scoreColor(systemScores.Brain) }}>{systemScores.Brain}</strong></div>
            <div><span style={{ fontSize: 12, color: "#64748b" }}>Recovery</span><br/>
              <strong style={{ fontSize: 14, color: scoreColor(systemScores.Recovery) }}>{systemScores.Recovery}</strong></div>
            <div><span style={{ fontSize: 12, color: "#64748b" }}>Pathways scored</span><br/>
              <strong style={{ fontSize: 14 }}>{totalPathways}</strong></div>
            <div><span style={{ fontSize: 12, color: "#64748b" }}>Pathways with matches</span><br/>
              <strong style={{ fontSize: 14 }}>{totalMatched}</strong></div>
            <div><span style={{ fontSize: 12, color: "#64748b" }}>Categories</span><br/>
              <strong style={{ fontSize: 14 }}>{categories.length}</strong></div>
          </div>

          {result.summary?.overall && (
            <div style={{ background: "#f8fafc", border: "1px solid #cbd5e1", borderRadius: 10, padding: "12px 16px" }}>
              <h2 style={{ marginTop: 0, marginBottom: 8, fontSize: 16 }}>System Summary</h2>
              <div style={{ color: "#334155", fontSize: 14 }}>{result.summary.overall}</div>
            </div>
          )}

          {previousHistory && (
            <div style={{ background: "#f8fafc", border: "1px solid #dbeafe", borderRadius: 10, padding: "14px 16px" }}>
              <h2 style={{ marginTop: 0, marginBottom: 12, fontSize: 16 }}>Trend vs Previous Report</h2>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 10, fontSize: 13 }}>
                {(["Energy", "Inflammation", "Detox", "Brain", "Recovery"] as const).map((system) => {
                  const current = systemScores[system];
                  const previous = previousHistory.systems[system] ?? current;
                  const delta = current - previous;
                  return (
                    <div key={system} style={{ border: "1px solid #e2e8f0", borderRadius: 8, padding: "8px 10px", background: "#fff" }}>
                      <div style={{ color: "#64748b", marginBottom: 3 }}>{system}</div>
                      <div style={{ fontWeight: 700 }}>
                        {previous} → {current} {trendSymbol(delta)}
                      </div>
                      <div style={{ color: delta > 0 ? "#166534" : delta < 0 ? "#b91c1c" : "#475569" }}>
                        {delta === 0
                          ? "Stable — no change detected"
                          : `${delta > 0 ? "+" : ""}${delta} points ${delta > 0 ? "— improving" : "— declining"}`}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          <div style={{ background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 10, padding: "16px 18px" }}>
            <h2 style={{ marginTop: 0, marginBottom: 12, fontSize: 16 }}>Top 3 Issues</h2>
            <div style={{ display: "grid", gap: 12 }}>
              {result.top_issues.map((item, index) => (
                <div key={`${item.issue}-${index}`} style={{ background: "#fff", border: "1px solid #fca5a5", borderRadius: 8, padding: "12px 14px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: 6 }}>
                    <span style={{ background: priorityColor(item.severity ?? item.priority), color: "#fff", borderRadius: 4, padding: "2px 8px", fontSize: 11, fontWeight: 700 }}>
                      #{item.rank ?? index + 1} {(item.severity ?? item.priority).toUpperCase()}
                    </span>
                    <strong style={{ fontSize: 14 }}>{item.clinical_label ?? item.issue}</strong>
                  </div>
                  <div style={{ fontSize: 13, color: "#334155", marginBottom: 4 }}>
                    <strong>Impact:</strong> {item.impact}
                  </div>
                  {(item.symptoms ?? []).length > 0 && (
                    <div style={{ fontSize: 13, color: "#475569", marginBottom: 4 }}>
                      <strong>Symptoms:</strong> {(item.symptoms ?? []).join(" · ")}
                    </div>
                  )}
                  {item.expected_outcome && (
                    <div style={{ fontSize: 13, color: "#166534", marginBottom: 4 }}>
                      <strong>Expected outcome:</strong> {item.expected_outcome}
                    </div>
                  )}
                  {item.actions_structured && (Object.values(item.actions_structured).some(a => (a ?? []).length > 0)) && (
                    <div style={{ fontSize: 12, marginTop: 6, marginBottom: 4 }}>
                      {(["lifestyle", "nutrition", "clinical"] as const).map((cat) => {
                        const acts = item.actions_structured?.[cat] ?? [];
                        if (acts.length === 0) return null;
                        const colors: Record<string, string> = { lifestyle: "#1d4ed8", nutrition: "#15803d", clinical: "#b45309" };
                        return (
                          <div key={cat} style={{ marginBottom: 3 }}>
                            <span style={{ fontWeight: 700, color: colors[cat], textTransform: "capitalize" }}>{cat}: </span>
                            {acts.join(" · ")}
                          </div>
                        );
                      })}
                    </div>
                  )}
                  {item.trend && (
                    <div style={{ fontSize: 12, color: "#64748b", marginBottom: 4, fontStyle: "italic" }}>
                      {item.trend.interpretation}
                    </div>
                  )}
                  <div style={{ fontSize: 12, color: "#64748b" }}>
                    Urgency: <strong>{item.urgency ?? "Medium"}</strong> · Confidence: <strong>{item.confidence ?? "Medium"}</strong> · Score: <strong>{item.score}</strong>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div style={{ background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: 10, padding: "16px 18px" }}>
            <h2 style={{ marginTop: 0, marginBottom: 10, fontSize: 16 }}>Focus Areas (Next 30 Days)</h2>
            {effectiveFocusAreas.length === 0 ? (
              <div style={{ color: "#64748b", fontSize: 14 }}>Focus areas will appear once enough trend/priority data is available.</div>
            ) : (
              <div style={{ display: "grid", gap: 10 }}>
                {effectiveFocusAreas.map((area, index) => (
                  <div key={`${area.title}-${index}`} style={{ background: "#fff", border: "1px solid #bbf7d0", borderRadius: 8, padding: "10px 14px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: 4 }}>
                      <span style={{ background: "#15803d", color: "#fff", borderRadius: 4, padding: "2px 8px", fontSize: 11, fontWeight: 700 }}>
                        {index + 1}. {area.urgency?.toUpperCase() ?? "MEDIUM"}
                      </span>
                      <strong style={{ fontSize: 14 }}>{area.title}</strong>
                    </div>
                    {area.goal && (
                      <div style={{ fontSize: 13, color: "#166534", fontWeight: 600, marginBottom: 3 }}>
                        🎯 Goal: {area.goal}
                      </div>
                    )}
                    <div style={{ fontSize: 13, color: "#475569" }}>{area.reason}</div>
                  </div>
                ))}              
              </div>
            )}
          </div>

          <div style={{ background: "#eff6ff", border: "1px solid #bfdbfe", borderRadius: 10, padding: "16px 18px" }}>
            <h2 style={{ marginTop: 0, marginBottom: 10, fontSize: 16 }}>Recommended Actions</h2>
            {topActions.length === 0 ? (
              <div style={{ color: "#64748b", fontSize: 14 }}>No actions generated yet.</div>
            ) : (
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                {topActions.map((action, idx) => (
                  <li key={`${action}-${idx}`} style={{ marginBottom: 6, fontSize: 14 }}>{action}</li>
                ))}
              </ul>
            )}
          </div>

          {/* Insights */}
          <div style={{ background: "#f8fafc", borderRadius: 10, padding: "16px 18px" }}>
            <h2 style={{ marginTop: 0, marginBottom: 12, fontSize: 16 }}>Key Insights</h2>
            <ul style={{ margin: 0, paddingLeft: 20 }}>
              {result.insights.map((ins, i) => (
                <li key={i} style={{ marginBottom: 10, fontSize: 14, lineHeight: 1.4 }}>
                  <strong style={{ color: priorityColor(ins.severity ?? ins.priority) }}>
                    [{(ins.severity ?? ins.priority)}] {ins.clinical_label ?? ins.issue}
                  </strong>
                  <div>{ins.impact}</div>
                  <div style={{ color: "#475569" }}>Urgency: {ins.urgency ?? "Medium"} · Confidence: {ins.confidence ?? "N/A"}</div>
                  <div style={{ color: "#475569" }}>Action: {(ins.recommended_actions ?? ins.action).join(", ")}</div>
                </li>
              ))}
            </ul>
          </div>

          {/* Category scores overview grid */}
          <div>
            <h2 style={{ marginTop: 0, marginBottom: 12, fontSize: 16 }}>Category Overview</h2>
            <div style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
              gap: 10,
            }}>
              {categories.map((cat) => (
                <div key={cat.category} style={{
                  background: "#f8fafc", borderRadius: 8, padding: "12px 14px",
                  border: `1px solid #e2e8f0`,
                }}>
                  <div style={{ fontSize: 12, color: "#64748b", marginBottom: 4 }}>{prettyCategory(cat.category)}</div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <div style={{ flex: 1, height: 8, background: "#e2e8f0", borderRadius: 4, overflow: "hidden" }}>
                      <div style={{ width: `${cat.avg_score}%`, height: "100%", background: scoreColor(cat.avg_score), borderRadius: 4 }} />
                    </div>
                    <span style={{ fontWeight: 700, fontSize: 15, color: scoreColor(cat.avg_score), minWidth: 28 }}>
                      {cat.avg_score}
                    </span>
                  </div>
                  <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 4 }}>
                    {cat.matched_count}/{cat.pathway_count} pathways matched
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Detailed pathway breakdown */}
          <div>
            <h2 style={{ marginTop: 0, marginBottom: 12, fontSize: 16 }}>Pathway Details <span style={{ fontWeight: 400, color: "#94a3b8", fontSize: 13 }}>(click to expand)</span></h2>
            {categories.map((cat) => (
              <CategoryCard key={cat.category} group={cat} pathwayGenes={pathwayGenes} />
            ))}
          </div>

          {/* Technical footer */}
          <details style={{ fontSize: 12, color: "#94a3b8" }}>
            <summary style={{ cursor: "pointer", userSelect: "none" }}>Technical details</summary>
            <div style={{ marginTop: 8, display: "grid", gap: 4 }}>
              <div>Source column: {result.scores?.source_column ?? "N/A"}</div>
              <div>Rows: {result.scores?.rows_used ?? "N/A"} / {result.scores?.rows_total ?? "N/A"}</div>
              <div>R runner: {result.pathway.runner ?? "N/A"}</div>
              <div>Status: {result.pathway.status}</div>
            </div>
          </details>

          <div style={{ background: "#f8fafc", borderRadius: 10, padding: "16px 18px" }}>
            <h2 style={{ marginTop: 0, marginBottom: 12, fontSize: 16 }}>Patient History</h2>
            {history.length === 0 ? (
              <div style={{ color: "#64748b" }}>No historical reports yet.</div>
            ) : (
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr>
                    <th style={{ textAlign: "left", padding: "8px 6px", borderBottom: "1px solid #cbd5e1" }}>Date</th>
                    <th style={{ textAlign: "center", padding: "8px 6px", borderBottom: "1px solid #cbd5e1" }}>Energy</th>
                    <th style={{ textAlign: "center", padding: "8px 6px", borderBottom: "1px solid #cbd5e1" }}>Inflammation</th>
                    <th style={{ textAlign: "center", padding: "8px 6px", borderBottom: "1px solid #cbd5e1" }}>Detox</th>
                    <th style={{ textAlign: "center", padding: "8px 6px", borderBottom: "1px solid #cbd5e1" }}>Brain</th>
                    <th style={{ textAlign: "center", padding: "8px 6px", borderBottom: "1px solid #cbd5e1" }}>Recovery</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((row, idx) => (
                    <tr key={`${row.date}-${idx}`}>
                      <td style={{ padding: "8px 6px", borderBottom: "1px solid #e2e8f0" }}>{new Date(row.date).toLocaleString()}</td>
                      <td style={{ textAlign: "center", padding: "8px 6px", borderBottom: "1px solid #e2e8f0" }}>{row.systems.Energy ?? "—"}</td>
                      <td style={{ textAlign: "center", padding: "8px 6px", borderBottom: "1px solid #e2e8f0" }}>{row.systems.Inflammation ?? "—"}</td>
                      <td style={{ textAlign: "center", padding: "8px 6px", borderBottom: "1px solid #e2e8f0" }}>{row.systems.Detox ?? "—"}</td>
                      <td style={{ textAlign: "center", padding: "8px 6px", borderBottom: "1px solid #e2e8f0" }}>{row.systems.Brain ?? "—"}</td>
                      <td style={{ textAlign: "center", padding: "8px 6px", borderBottom: "1px solid #e2e8f0" }}>{row.systems.Recovery ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

        </div>
      )}
    </div>
  );
}
