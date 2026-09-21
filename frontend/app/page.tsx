"use client";

import React, { useState, useEffect } from "react";
import {
  Building2,
  Globe,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Sparkles,
  ShieldCheck,
  Copy,
  Check,
  ExternalLink,
  Target,
  FileText,
  Boxes,
  Flame,
  MessageSquare,
  RefreshCw,
  Zap,
  Activity,
  ArrowRight,
  Send,
  User,
  Compass,
  ChevronDown,
  Lock,
  Eye,
} from "lucide-react";
import type {
  AccountBrief,
  FactCheckedBrief,
  FactCheckedOutreach,
  FactCheckResult,
  ICPFitLabel,
} from "../types/brief";

/* ============================================================
   API Helpers (preserved from prior implementation)
   ============================================================ */

function sanitizeApiBaseUrl(rawUrl?: string): string {
  if (!rawUrl || !rawUrl.trim()) return "http://127.0.0.1:8000";
  let cleaned = rawUrl.trim();
  if (!cleaned.startsWith("http://") && !cleaned.startsWith("https://")) {
    cleaned = `https://${cleaned}`;
  }
  return cleaned.replace(/\/+$/, "");
}

const API_BASE_URL = sanitizeApiBaseUrl(process.env.NEXT_PUBLIC_API_URL);
const FETCH_TIMEOUT_MS = 120_000;

async function fetchWithTimeout(
  url: string,
  options: RequestInit,
  timeoutMs: number = FETCH_TIMEOUT_MS
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    return response;
  } finally {
    clearTimeout(timeoutId);
  }
}

function formatApiErrorMessage(err: any, endpoint: string): string {
  const isHttps = typeof window !== "undefined" && window.location.protocol === "https:";
  const isTargetHttp = API_BASE_URL.startsWith("http://");

  if (err.name === "AbortError" || err.message?.includes("aborted")) {
    return `Request to ${endpoint} timed out after 120s. The backend may be waking from cold sleep (Render free tier). Wait 15 seconds and retry.`;
  }
  if (isHttps && isTargetHttp) {
    return `Mixed Content Block: Frontend is HTTPS but API URL is HTTP (${API_BASE_URL}). Update NEXT_PUBLIC_API_URL to use https://.`;
  }
  if (
    err.message?.includes("Failed to fetch") ||
    err.message?.includes("NetworkError") ||
    err.message?.includes("Load failed")
  ) {
    const origin = typeof window !== "undefined" ? window.location.origin : "unknown";
    return `Cannot connect to ${API_BASE_URL}${endpoint}.\n\n• CORS: Verify ALLOWED_ORIGINS on Render includes '${origin}'\n• Cold Start: Visit ${API_BASE_URL}/api/health in a new tab to wake the backend\n• Config: Verify NEXT_PUBLIC_API_URL on Vercel matches your Render URL`;
  }
  return err.message || `Unexpected error calling ${endpoint}.`;
}

/* ============================================================
   Pipeline Stages
   ============================================================ */

interface StageInfo {
  step: string;
  agent: string;
  desc: string;
}

const STAGES: StageInfo[] = [
  { step: "01", agent: "ResearchAgent", desc: "Web scraping & context retrieval" },
  { step: "02", agent: "ICPClassifier", desc: "ICP qualification scoring" },
  { step: "03", agent: "SynthesisAgent", desc: "Brief compilation & grounding" },
  { step: "04", agent: "FactCheckAgent", desc: "Deterministic claim verification" },
];

/* ============================================================
   Main Page Component
   ============================================================ */

export default function Home() {
  const [activeTab, setActiveTab] = useState<"brief" | "outreach">("brief");

  // Brief inputs
  const [companyName, setCompanyName] = useState("Notion");
  const [url, setUrl] = useState("https://www.notion.so");
  const [isLoadingBrief, setIsLoadingBrief] = useState(false);
  const [activeStageIndex, setActiveStageIndex] = useState(0);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // Outreach inputs
  const [contactName, setContactName] = useState("Alex Chen");
  const [contactRole, setContactRole] = useState("VP of Sales");
  const [contactNotes, setContactNotes] = useState(
    "Focused on expanding Notion's enterprise sales footprint and sales engineering enablement."
  );
  const [isLoadingOutreach, setIsLoadingOutreach] = useState(false);
  const [selectedEmailToneIndex, setSelectedEmailToneIndex] = useState(0);
  const [showDossierCheatSheet, setShowDossierCheatSheet] = useState(false);

  // Results
  const [briefResult, setBriefResult] = useState<FactCheckedBrief | null>(null);
  const [outreachResult, setOutreachResult] = useState<FactCheckedOutreach | null>(null);

  // Evidence Inspector
  const [selectedClaim, setSelectedClaim] = useState<FactCheckResult | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  // Derived
  const currentFactChecks: FactCheckResult[] =
    activeTab === "outreach" && outreachResult
      ? outreachResult.fact_checks
      : briefResult
      ? briefResult.fact_checks
      : [];

  const currentFaithfulness: number =
    activeTab === "outreach" && outreachResult
      ? outreachResult.overall_faithfulness_score
      : briefResult
      ? briefResult.overall_faithfulness_score
      : 1.0;

  const currentFlaggedClaims: string[] =
    activeTab === "outreach" && outreachResult
      ? outreachResult.flagged_claims
      : briefResult
      ? briefResult.flagged_claims
      : [];

  const directlyCount = currentFactChecks.filter((f) => f.status === "directly_supported").length;
  const inferenceCount = currentFactChecks.filter((f) => f.status === "reasonable_inference").length;
  const flaggedCount = currentFlaggedClaims.length;

  // Stage timer
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isLoadingBrief || isLoadingOutreach) {
      setElapsedSeconds(0);
      setActiveStageIndex(0);
      interval = setInterval(() => {
        setElapsedSeconds((prev) => {
          const next = prev + 1;
          if (next > 6 && next <= 14) setActiveStageIndex(1);
          else if (next > 14 && next <= 22) setActiveStageIndex(2);
          else if (next > 22) setActiveStageIndex(3);
          return next;
        });
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isLoadingBrief, isLoadingOutreach]);

  // Sync selectedClaim to active audit log when switching tabs or loading results
  useEffect(() => {
    if (currentFactChecks.length > 0) {
      const exists = selectedClaim && currentFactChecks.some((c) => c.claim === selectedClaim.claim);
      if (!exists) {
        setSelectedClaim(currentFactChecks[0]);
      }
    } else {
      setSelectedClaim(null);
    }
  }, [activeTab, briefResult, outreachResult]);

  /* ---- Handlers ---- */

  const handleGenerateBrief = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const trimmedName = companyName.trim();
    const trimmedUrl = url.trim();
    if (!trimmedName && !trimmedUrl) {
      setError("Provide a company name or URL to begin.");
      return;
    }
    setError(null);
    setBriefResult(null);
    setOutreachResult(null);
    setSelectedClaim(null);
    setIsLoadingBrief(true);
    setActiveTab("brief");

    try {
      const response = await fetchWithTimeout(`${API_BASE_URL}/api/brief`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          company_name: trimmedName || undefined,
          url: trimmedUrl || undefined,
        }),
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }
      const data: FactCheckedBrief = await response.json();
      setBriefResult(data);
      if (data.fact_checks.length > 0) setSelectedClaim(data.fact_checks[0]);
    } catch (err: any) {
      console.error("API error (/api/brief):", err);
      setError(formatApiErrorMessage(err, "/api/brief"));
    } finally {
      setIsLoadingBrief(false);
    }
  };

  const handleGenerateOutreach = async () => {
    if (!briefResult) {
      setError("Generate an Account Brief first.");
      return;
    }
    setError(null);
    setIsLoadingOutreach(true);

    try {
      const response = await fetchWithTimeout(`${API_BASE_URL}/api/outreach`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          account_brief: briefResult.brief,
          contact_name: contactName.trim() || undefined,
          contact_role: contactRole.trim() || undefined,
          contact_linkedin_or_notes: contactNotes.trim() || undefined,
        }),
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }
      const data: FactCheckedOutreach = await response.json();
      setOutreachResult(data);
      setActiveTab("outreach");
      if (data.fact_checks.length > 0) setSelectedClaim(data.fact_checks[0]);
    } catch (err: any) {
      console.error("API error (/api/outreach):", err);
      setError(formatApiErrorMessage(err, "/api/outreach"));
    } finally {
      setIsLoadingOutreach(false);
    }
  };

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  /* ---- Visual Helpers ---- */

  const getFitBadge = (label: ICPFitLabel, score: number | null) => {
    const map: Record<ICPFitLabel, { cls: string; dot: string; text: string }> = {
      strong_fit: { cls: "bg-emerald-950/50 text-emerald-400 border-emerald-800/60", dot: "bg-emerald-400", text: "Strong Fit" },
      possible_fit: { cls: "bg-fn-surface text-fn-text-secondary border-fn-border", dot: "bg-fn-text-secondary", text: "Possible Fit" },
      poor_fit: { cls: "bg-fn-surface text-fn-text-tertiary border-fn-border", dot: "bg-fn-text-tertiary", text: "Out-of-ICP" },
      unknown: { cls: "bg-fn-surface text-fn-text-tertiary border-fn-border", dot: "bg-fn-text-tertiary", text: "Unassessed" },
    };
    const m = map[label] || map.unknown;
    return (
      <div className={`px-3 py-1.5 rounded-full border flex items-center gap-2 text-xs font-medium ${m.cls}`}>
        <span className={`w-2 h-2 rounded-full ${m.dot}`} />
        <span>{m.text}</span>
        {score !== null && <span className="text-fn-text-tertiary">({Math.round(score * 100)}%)</span>}
      </div>
    );
  };

  const StatusBadge = ({ status }: { status: FactCheckResult["status"] }) => {
    switch (status) {
      case "directly_supported":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-emerald-950/50 text-fn-verified border border-emerald-800/50">
            <CheckCircle2 className="w-3 h-3" /> Verified
          </span>
        );
      case "reasonable_inference":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-fn-elevated text-fn-text-secondary border border-fn-border">
            <Compass className="w-3 h-3" /> Inferred
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-rose-950/50 text-fn-flagged border border-rose-800/50">
            <AlertTriangle className="w-3 h-3" /> Flagged
          </span>
        );
    }
  };

  /* ============================================================
     RENDER
     ============================================================ */

  return (
    <main className="min-h-[100dvh] bg-fn-void text-fn-text-primary bg-noise">
      {/* ── Header ─────────────────────────────────────── */}
      <header className="sticky top-0 z-40 bg-fn-void/85 backdrop-blur-lg border-b border-fn-border/60">
        <div className="max-w-[1400px] mx-auto px-5 sm:px-8 h-14 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="font-display font-bold text-sm tracking-tight text-fn-text-primary">
              GTM Copilot
            </h1>
            <div className="h-4 w-px bg-fn-border" />
            <span className="text-xs text-fn-text-tertiary hidden sm:inline font-display">
              Sales Intelligence & Grounded Outreach
            </span>
          </div>

          <div className="flex items-center gap-4">
            {/* Live Faithfulness Metric */}
            {(briefResult || outreachResult) && (
              <div className="flex items-center gap-2 px-3 py-1 rounded-md bg-fn-proof-subtle border border-amber-800/30">
                <ShieldCheck className="w-3.5 h-3.5 text-fn-proof" />
                <span className="text-xs font-mono font-semibold text-fn-proof">
                  {Math.round(currentFaithfulness * 100)}% Grounded
                </span>
              </div>
            )}
            <div className="flex items-center gap-2 px-2.5 py-1 rounded-md bg-fn-surface border border-fn-border text-fn-text-tertiary font-mono text-[11px]">
              <span className="w-1.5 h-1.5 rounded-full bg-fn-verified animate-pulse" />
              gemini-3.5-flash
            </div>
          </div>
        </div>
      </header>

      {/* ── Main Container ─────────────────────────────── */}
      <div className="max-w-[1400px] mx-auto px-5 sm:px-8 pt-8 pb-24">
        {/* ── Command Bar ────────────────────────────── */}
        <div className="mb-8">
          <form onSubmit={handleGenerateBrief} className="bg-fn-surface rounded-xl border border-fn-border p-6">
            <div className="flex flex-col sm:flex-row sm:items-end gap-4">
              <div className="flex-1">
                <label className="block text-xs font-mono font-medium text-fn-text-tertiary mb-1.5 uppercase tracking-wider">
                  Company
                </label>
                <div className="relative">
                  <Building2 className="w-4 h-4 absolute left-3 top-2.5 text-fn-text-tertiary" />
                  <input
                    type="text"
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    placeholder="e.g. Notion"
                    disabled={isLoadingBrief || isLoadingOutreach}
                    className="w-full pl-9 pr-3 py-2 rounded-lg bg-fn-void border border-fn-border text-fn-text-primary placeholder-fn-text-tertiary text-sm font-display focus:outline-none focus:border-fn-proof/50 transition-colors disabled:opacity-50"
                  />
                </div>
              </div>
              <div className="flex-1">
                <label className="block text-xs font-mono font-medium text-fn-text-tertiary mb-1.5 uppercase tracking-wider">
                  URL
                </label>
                <div className="relative">
                  <Globe className="w-4 h-4 absolute left-3 top-2.5 text-fn-text-tertiary" />
                  <input
                    type="url"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="https://www.notion.so"
                    disabled={isLoadingBrief || isLoadingOutreach}
                    className="w-full pl-9 pr-3 py-2 rounded-lg bg-fn-void border border-fn-border text-fn-text-primary placeholder-fn-text-tertiary text-sm font-display focus:outline-none focus:border-fn-proof/50 transition-colors disabled:opacity-50"
                  />
                </div>
              </div>
              <button
                type="submit"
                disabled={isLoadingBrief || isLoadingOutreach}
                className="px-6 py-2.5 rounded-lg bg-fn-proof hover:bg-fn-proof-muted text-fn-void text-xs font-display font-bold tracking-wide transition-all flex items-center justify-center gap-2 disabled:opacity-40 cursor-pointer btn-tactile shrink-0"
              >
                {isLoadingBrief ? (
                  <><RefreshCw className="w-3.5 h-3.5 animate-spin" /> Researching...</>
                ) : (
                  <><Zap className="w-3.5 h-3.5" /> Research & Qualify</>
                )}
              </button>
            </div>

            {/* Preset */}
            <div className="mt-3 flex items-center gap-2 text-xs">
              <span className="text-fn-text-tertiary font-mono">Preset:</span>
              <button
                type="button"
                onClick={() => { setCompanyName("Notion"); setUrl("https://www.notion.so"); setError(null); }}
                disabled={isLoadingBrief || isLoadingOutreach}
                className="px-2 py-0.5 rounded bg-fn-elevated hover:bg-fn-border text-fn-text-secondary text-xs font-display transition-colors cursor-pointer"
              >
                Notion
              </button>
            </div>
          </form>
        </div>

        {/* ── Error ───────────────────────────────────── */}
        {error && (
          <div className="mb-8 p-4 rounded-lg border-l-2 border-fn-proof bg-fn-surface border border-fn-border animate-fade-in-up">
            <div className="flex items-start gap-3">
              <XCircle className="w-4 h-4 shrink-0 mt-0.5 text-fn-flagged" />
              <div>
                <span className="font-display font-semibold text-xs text-fn-flagged block">Pipeline Diagnostics</span>
                <p className="mt-1 text-fn-text-secondary whitespace-pre-line font-mono text-[11px] leading-relaxed">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* ── Pipeline Stepper (Loading) ──────────────── */}
        {(isLoadingBrief || isLoadingOutreach) && (
          <div className="mb-8 bg-fn-surface rounded-xl border border-fn-border p-6 animate-fade-in-up">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-2.5">
                <Activity className="w-4 h-4 text-fn-proof animate-pulse" />
                <span className="text-xs font-display font-semibold text-fn-text-primary">
                  {isLoadingOutreach ? "Generating Grounded Outreach" : "4-Stage Research & Verification Pipeline"}
                </span>
              </div>
              <span className="text-xs font-mono text-fn-text-tertiary">{elapsedSeconds}s</span>
            </div>

            {/* Horizontal Timeline */}
            <div className="flex items-center gap-0">
              {STAGES.map((s, idx) => {
                const isDone = idx < activeStageIndex;
                const isCurrent = idx === activeStageIndex;
                return (
                  <React.Fragment key={s.step}>
                    <div className="flex flex-col items-center flex-1 min-w-0">
                      {/* Node */}
                      <div
                        className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-mono font-bold transition-all ${
                          isDone
                            ? "bg-emerald-950 text-fn-verified border border-emerald-800/60"
                            : isCurrent
                            ? "bg-fn-proof text-fn-void animate-pulse-amber"
                            : "bg-fn-elevated text-fn-text-tertiary border border-fn-border"
                        }`}
                      >
                        {isDone ? <Check className="w-3.5 h-3.5" /> : s.step}
                      </div>
                      {/* Label */}
                      <span className={`mt-2 text-[11px] font-display font-medium text-center leading-tight ${isCurrent ? "text-fn-text-primary" : isDone ? "text-fn-text-secondary" : "text-fn-text-tertiary"}`}>
                        {s.agent}
                      </span>
                      <span className="text-[10px] text-fn-text-tertiary text-center leading-tight mt-0.5 hidden sm:block">{s.desc}</span>
                    </div>
                    {/* Connector line */}
                    {idx < STAGES.length - 1 && (
                      <div className={`h-px flex-1 mx-1 mt-[-20px] ${isDone ? "bg-fn-verified/40" : "bg-fn-border"}`} />
                    )}
                  </React.Fragment>
                );
              })}
            </div>
          </div>
        )}

        {/* ── Empty State ─────────────────────────────── */}
        {!briefResult && !isLoadingBrief && !error && (
          <div className="py-24 text-center animate-fade-in-up">
            <p className="font-serif italic text-xl sm:text-2xl text-fn-text-secondary leading-relaxed max-w-lg mx-auto">
              Enter a company to begin intelligence gathering.
            </p>
            <p className="mt-4 text-xs text-fn-text-tertiary font-mono">
              Research → ICP Qualification → Synthesis → Fact-Check
            </p>
          </div>
        )}

        {/* ── Results Layout: Content + Evidence Rail ── */}
        {briefResult && !isLoadingBrief && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 animate-fade-in-up">
            {/* ── Left Column: Content (7/12) ─────────── */}
            <div className="lg:col-span-7 space-y-8">
              {/* Hero: Company + Faithfulness Score */}
              <div className="bg-fn-surface rounded-xl border border-fn-border p-6">
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-3">
                      <h2 className="text-2xl font-display font-bold tracking-tight">{briefResult.brief.company_name}</h2>
                      <span className="px-2.5 py-0.5 rounded text-xs font-mono bg-fn-elevated text-fn-text-secondary border border-fn-border">
                        {briefResult.brief.industry || "General / Enterprise"}
                      </span>
                    </div>
                    {briefResult.brief.source_urls.length > 0 && (
                      <div className="mt-2 flex items-center gap-2 text-xs font-mono text-fn-text-tertiary">
                        <Globe className="w-3 h-3" />
                        {briefResult.brief.source_urls.map((u) => (
                          <a key={u} href={u} target="_blank" rel="noopener noreferrer" className="hover:text-fn-proof underline flex items-center gap-1 transition-colors">
                            {u} <ExternalLink className="w-2.5 h-2.5" />
                          </a>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="flex items-center gap-3 shrink-0">
                    {getFitBadge(briefResult.brief.icp_classification.fit_label, briefResult.brief.icp_classification.fit_score)}
                  </div>
                </div>

                {/* Hero Faithfulness Score */}
                <div className="mt-6 pt-6 border-t border-fn-border flex items-center gap-6">
                  <div className="text-center">
                    <div className="text-5xl font-display font-bold text-fn-proof tabular-nums">
                      {Math.round(currentFaithfulness * 100)}
                      <span className="text-2xl text-fn-proof-muted">%</span>
                    </div>
                    <div className="text-[10px] font-mono uppercase tracking-wider text-fn-text-tertiary mt-1">Faithfulness</div>
                  </div>
                  <div className="flex-1 text-xs text-fn-text-secondary font-display">
                    <span className="text-fn-verified font-semibold">{directlyCount}</span> directly quoted ·{" "}
                    <span className="text-fn-text-secondary font-semibold">{inferenceCount}</span> inferred ·{" "}
                    {flaggedCount > 0 ? (
                      <span className="text-fn-flagged font-semibold">{flaggedCount} flagged</span>
                    ) : (
                      <span className="text-fn-text-tertiary">{flaggedCount} flagged</span>
                    )}
                    <span className="block mt-1 text-fn-text-tertiary">{currentFactChecks.length} claims audited against source context</span>
                  </div>
                </div>
              </div>

              {/* ── Tab Switcher ──────────────────────── */}
              {briefResult && (
                <div className="flex items-center gap-0 border-b border-fn-border">
                  <button
                    type="button"
                    onClick={() => setActiveTab("brief")}
                    className={`px-4 py-2.5 text-xs font-display font-semibold transition-colors relative cursor-pointer ${
                      activeTab === "brief" ? "text-fn-text-primary" : "text-fn-text-tertiary hover:text-fn-text-secondary"
                    }`}
                  >
                    Account Dossier
                    {activeTab === "brief" && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-fn-proof" />}
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveTab("outreach")}
                    className={`px-4 py-2.5 text-xs font-display font-semibold transition-colors relative cursor-pointer flex items-center gap-1.5 ${
                      activeTab === "outreach" ? "text-fn-text-primary" : briefResult ? "text-fn-text-tertiary hover:text-fn-text-secondary" : "text-fn-text-tertiary cursor-not-allowed"
                    }`}
                  >
                    Outreach Studio
                    {outreachResult && <span className="w-1.5 h-1.5 rounded-full bg-fn-verified" />}
                    {activeTab === "outreach" && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-fn-proof" />}
                  </button>
                </div>
              )}

              {/* ── MODE 1: ACCOUNT DOSSIER ──────────── */}
              {activeTab === "brief" && (
                <div className="space-y-6">
                  {/* ICP Rationale */}
                  <div className="p-5 rounded-lg bg-fn-surface border border-fn-border">
                    <div className="text-[11px] font-mono uppercase tracking-wider text-fn-text-tertiary mb-2 flex items-center gap-1.5">
                      <Target className="w-3.5 h-3.5" /> ICP FIT RATIONALE
                    </div>
                    <p className="text-sm text-fn-text-secondary font-serif leading-relaxed">
                      {briefResult.brief.icp_classification.rationale}
                    </p>
                    {(briefResult.brief.icp_classification.matched_criteria.length > 0 || briefResult.brief.icp_classification.mismatched_criteria.length > 0) && (
                      <div className="mt-4 pt-4 border-t border-fn-border grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                        {briefResult.brief.icp_classification.matched_criteria.length > 0 && (
                          <div>
                            <span className="text-fn-verified font-mono text-[11px] font-semibold flex items-center gap-1 mb-1.5">
                              <CheckCircle2 className="w-3 h-3" /> Matched
                            </span>
                            <ul className="space-y-1 text-fn-text-secondary font-display">
                              {briefResult.brief.icp_classification.matched_criteria.map((c, i) => (
                                <li key={i} className="flex items-start gap-1.5"><span className="text-fn-verified">✓</span> {c}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {briefResult.brief.icp_classification.mismatched_criteria.length > 0 && (
                          <div>
                            <span className="text-fn-text-tertiary font-mono text-[11px] font-semibold flex items-center gap-1 mb-1.5">
                              <AlertTriangle className="w-3 h-3" /> Gaps
                            </span>
                            <ul className="space-y-1 text-fn-text-tertiary font-display">
                              {briefResult.brief.icp_classification.mismatched_criteria.map((c, i) => (
                                <li key={i} className="flex items-start gap-1.5">• {c}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Executive Summary — Editorial Serif */}
                  <div className="p-6 rounded-lg bg-fn-surface border border-fn-border">
                    <div className="text-[11px] font-mono uppercase tracking-wider text-fn-text-tertiary mb-3 flex items-center gap-1.5">
                      <FileText className="w-3.5 h-3.5" /> EXECUTIVE SUMMARY
                    </div>
                    <p className="prose-editorial text-[15px] text-fn-text-primary leading-[1.8]">
                      {briefResult.brief.executive_summary}
                    </p>
                  </div>

                  {/* Products */}
                  <div className="p-6 rounded-lg bg-fn-surface border border-fn-border">
                    <div className="text-[11px] font-mono uppercase tracking-wider text-fn-text-tertiary mb-3 flex items-center gap-1.5">
                      <Boxes className="w-3.5 h-3.5" /> KEY PRODUCTS & SERVICES
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {briefResult.brief.key_products_or_services.map((p, i) => (
                        <span key={i} className="px-3 py-1 rounded-md bg-fn-elevated text-fn-text-secondary text-xs font-display border border-fn-border">{p}</span>
                      ))}
                    </div>
                  </div>

                  {/* Pain Points */}
                  <div className="p-6 rounded-lg bg-fn-surface border border-fn-border">
                    <div className="text-[11px] font-mono uppercase tracking-wider text-fn-text-tertiary mb-3 flex items-center gap-1.5">
                      <Flame className="w-3.5 h-3.5" /> IDENTIFIED PAIN POINTS
                    </div>
                    <ul className="space-y-3">
                      {briefResult.brief.likely_pain_points.map((pain, i) => (
                        <li key={i} className="flex items-start gap-3 text-sm text-fn-text-secondary font-display">
                          <span className="text-fn-proof font-mono text-xs font-bold mt-0.5">0{i + 1}</span>
                          <span>{pain}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Talk Tracks */}
                  <div className="p-6 rounded-lg bg-fn-surface border border-fn-border">
                    <div className="text-[11px] font-mono uppercase tracking-wider text-fn-text-tertiary mb-3 flex items-center gap-1.5">
                      <MessageSquare className="w-3.5 h-3.5" /> SALES TALK TRACKS
                    </div>
                    <div className="space-y-3">
                      {briefResult.brief.suggested_talk_tracks.map((track, i) => (
                        <div key={i} className="p-4 rounded-lg bg-fn-void border border-fn-border flex items-start justify-between gap-4 group hover:border-fn-border-focus transition-colors">
                          <div className="space-y-1 flex-1">
                            <span className="text-[10px] font-mono text-fn-text-tertiary uppercase tracking-wider block">Track #{i + 1}</span>
                            <p className="text-sm text-fn-text-secondary font-serif italic leading-relaxed">"{track}"</p>
                          </div>
                          <button
                            type="button"
                            onClick={() => handleCopy(track, `track-${i}`)}
                            className="p-2 rounded bg-fn-elevated hover:bg-fn-border text-fn-text-tertiary transition-colors shrink-0 cursor-pointer btn-tactile"
                            title="Copy"
                          >
                            {copiedKey === `track-${i}` ? <Check className="w-3.5 h-3.5 text-fn-verified" /> : <Copy className="w-3.5 h-3.5" />}
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Transition CTA */}
                  <div className="p-6 rounded-xl bg-fn-surface border border-fn-proof/30 flex flex-col sm:flex-row items-center justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2 text-fn-proof font-mono text-xs font-semibold uppercase tracking-wider mb-1">
                        <CheckCircle2 className="w-4 h-4" /> Research Complete · {Math.round(briefResult.overall_faithfulness_score * 100)}% Grounded
                      </div>
                      <h4 className="font-display font-bold text-base text-fn-text-primary">
                        Generate Outreach for {briefResult.brief.company_name}
                      </h4>
                      <p className="text-xs text-fn-text-tertiary mt-1 max-w-xl font-display">
                        Pass this verified dossier into outreach generation — 4 email tone variants and a follow-up cadence.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setActiveTab("outreach")}
                      className="px-5 py-3 rounded-lg bg-fn-proof hover:bg-fn-proof-muted text-fn-void text-xs font-display font-bold flex items-center gap-2 cursor-pointer shrink-0 transition-all btn-tactile"
                    >
                      Compose Outreach <ArrowRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )}

              {/* ── MODE 2: OUTREACH STUDIO ──────────── */}
              {activeTab === "outreach" && (
                <div className="space-y-6">
                  {/* Connected Context Banner */}
                  <div className="p-5 rounded-lg bg-fn-surface border border-fn-border">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-fn-border">
                      <div>
                        <span className="text-[10px] font-mono text-fn-proof uppercase tracking-wider font-semibold block">
                          Connected Account Context
                        </span>
                        <div className="text-sm font-display font-bold text-fn-text-primary flex items-center gap-2 mt-0.5">
                          {briefResult.brief.company_name}
                          <span className="text-fn-text-tertiary font-normal">·</span>
                          <span className="text-xs font-mono text-fn-text-secondary font-normal">
                            {briefResult.brief.industry || "General / Enterprise"}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => setShowDossierCheatSheet(!showDossierCheatSheet)}
                          className="px-2.5 py-1 rounded bg-fn-elevated hover:bg-fn-border text-fn-text-secondary text-xs font-display border border-fn-border transition-all flex items-center gap-1.5 cursor-pointer"
                        >
                          <Eye className="w-3 h-3" />
                          {showDossierCheatSheet ? "Hide" : "Cheat Sheet"}
                          <ChevronDown className={`w-3 h-3 transition-transform ${showDossierCheatSheet ? "rotate-180" : ""}`} />
                        </button>
                        <button
                          type="button"
                          onClick={() => setActiveTab("brief")}
                          className="px-2.5 py-1 rounded bg-fn-elevated hover:bg-fn-border text-fn-text-secondary text-xs font-display border border-fn-border transition-all flex items-center gap-1.5 cursor-pointer"
                        >
                          Full Dossier ↗
                        </button>
                      </div>
                    </div>

                    {showDossierCheatSheet && (
                      <div className="mt-3 pt-3 border-t border-fn-border grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                        <div className="p-3 rounded bg-fn-void border border-fn-border">
                          <span className="font-mono text-[11px] text-fn-text-tertiary uppercase tracking-wider block mb-1">Pain Points:</span>
                          <ul className="space-y-1 text-fn-text-secondary font-display text-[11px]">
                            {briefResult.brief.likely_pain_points.slice(0, 3).map((pp, i) => (
                              <li key={i}>• {pp}</li>
                            ))}
                          </ul>
                        </div>
                        <div className="p-3 rounded bg-fn-void border border-fn-border">
                          <span className="font-mono text-[11px] text-fn-text-tertiary uppercase tracking-wider block mb-1">Primary Talk Track:</span>
                          <p className="text-fn-text-secondary font-serif italic text-[11px]">
                            "{briefResult.brief.suggested_talk_tracks[0] || "N/A"}"
                          </p>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Prospect Input */}
                  <div className="p-6 rounded-lg bg-fn-surface border border-fn-border">
                    <div className="text-[11px] font-mono uppercase tracking-wider text-fn-text-tertiary mb-4 flex items-center gap-1.5">
                      <User className="w-3.5 h-3.5" /> PROSPECT CUSTOMIZATION
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
                      <div>
                        <label className="block text-xs font-mono text-fn-text-tertiary mb-1">Contact Name</label>
                        <input type="text" value={contactName} onChange={(e) => setContactName(e.target.value)}
                          placeholder="e.g. Alex Chen"
                          className="w-full px-3 py-2 rounded-lg bg-fn-void border border-fn-border text-fn-text-primary text-xs font-display focus:outline-none focus:border-fn-proof/50" />
                      </div>
                      <div>
                        <label className="block text-xs font-mono text-fn-text-tertiary mb-1">Role / Title</label>
                        <input type="text" value={contactRole} onChange={(e) => setContactRole(e.target.value)}
                          placeholder="e.g. VP of Sales"
                          className="w-full px-3 py-2 rounded-lg bg-fn-void border border-fn-border text-fn-text-primary text-xs font-display focus:outline-none focus:border-fn-proof/50" />
                      </div>
                    </div>
                    <div className="mb-4">
                      <label className="block text-xs font-mono text-fn-text-tertiary mb-1">Prospect Notes</label>
                      <textarea rows={2} value={contactNotes} onChange={(e) => setContactNotes(e.target.value)}
                        placeholder="Context, LinkedIn posts, or areas of focus..."
                        className="w-full px-3 py-2 rounded-lg bg-fn-void border border-fn-border text-fn-text-primary text-xs font-display focus:outline-none focus:border-fn-proof/50" />
                    </div>
                    <button
                      type="button"
                      onClick={handleGenerateOutreach}
                      disabled={isLoadingOutreach}
                      className="w-full py-2.5 rounded-lg bg-fn-proof hover:bg-fn-proof-muted text-fn-void text-xs font-display font-bold tracking-wide transition-all flex items-center justify-center gap-2 cursor-pointer btn-tactile disabled:opacity-40"
                    >
                      {isLoadingOutreach ? (
                        <><RefreshCw className="w-3.5 h-3.5 animate-spin" /> Compiling Outreach...</>
                      ) : (
                        <><Send className="w-3.5 h-3.5" /> Generate Grounded Outreach</>
                      )}
                    </button>
                  </div>

                  {/* Outreach Results */}
                  {outreachResult && (
                    <div className="space-y-6">
                      {/* Email Composer */}
                      <div className="p-6 rounded-lg bg-fn-surface border border-fn-border">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 mb-4 border-b border-fn-border">
                          <div className="text-[11px] font-mono uppercase tracking-wider text-fn-text-tertiary flex items-center gap-1.5">
                            <MessageSquare className="w-3.5 h-3.5" /> EMAIL VARIANTS ({outreachResult.outreach.email_variants.length} Tones)
                          </div>
                          <span className="text-xs font-mono text-fn-text-tertiary">
                            To: {outreachResult.outreach.contact_name || "General Lead"}
                          </span>
                        </div>

                        {/* Underline Tone Tabs */}
                        <div className="flex items-center gap-0 border-b border-fn-border mb-5">
                          {outreachResult.outreach.email_variants.map((v, i) => (
                            <button
                              key={i}
                              type="button"
                              onClick={() => setSelectedEmailToneIndex(i)}
                              className={`px-3 py-2 text-xs font-display font-medium uppercase tracking-wider transition-colors relative cursor-pointer ${
                                selectedEmailToneIndex === i ? "text-fn-proof" : "text-fn-text-tertiary hover:text-fn-text-secondary"
                              }`}
                            >
                              {v.tone_label}
                              {selectedEmailToneIndex === i && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-fn-proof" />}
                            </button>
                          ))}
                        </div>

                        {/* Email Body */}
                        {(() => {
                          const v = outreachResult.outreach.email_variants[selectedEmailToneIndex] || outreachResult.outreach.email_variants[0];
                          if (!v) return null;
                          return (
                            <div className="p-5 rounded-lg bg-fn-void border border-fn-border space-y-4">
                              <div className="flex items-start justify-between gap-4 pb-3 border-b border-fn-border">
                                <div>
                                  <span className="text-[10px] font-mono text-fn-text-tertiary uppercase tracking-wider block">Subject</span>
                                  <span className="text-sm font-display font-semibold text-fn-text-primary">{v.subject}</span>
                                </div>
                                <button
                                  type="button"
                                  onClick={() => handleCopy(`Subject: ${v.subject}\n\n${v.body}`, `variant-${selectedEmailToneIndex}`)}
                                  className="p-2 rounded bg-fn-elevated hover:bg-fn-border text-fn-text-tertiary transition-colors shrink-0 cursor-pointer btn-tactile"
                                >
                                  {copiedKey === `variant-${selectedEmailToneIndex}` ? <Check className="w-3.5 h-3.5 text-fn-verified" /> : <Copy className="w-3.5 h-3.5" />}
                                </button>
                              </div>
                              <div className="prose-editorial text-sm text-fn-text-secondary whitespace-pre-line">{v.body}</div>
                            </div>
                          );
                        })()}
                      </div>

                      {/* Follow-up Timeline */}
                      <div className="p-6 rounded-lg bg-fn-surface border border-fn-border">
                        <div className="text-[11px] font-mono uppercase tracking-wider text-fn-text-tertiary mb-4 flex items-center gap-1.5">
                          <Compass className="w-3.5 h-3.5" /> FOLLOW-UP CADENCE ({outreachResult.outreach.follow_up_sequence.length} Touches)
                        </div>
                        <div className="space-y-0">
                          {outreachResult.outreach.follow_up_sequence.map((fu, idx) => (
                            <div key={idx} className="flex gap-4">
                              {/* Timeline spine */}
                              <div className="flex flex-col items-center">
                                <div className="w-6 h-6 rounded-full bg-fn-elevated border border-fn-border flex items-center justify-center text-[10px] font-mono font-bold text-fn-text-secondary">{fu.sequence_position}</div>
                                {idx < outreachResult.outreach.follow_up_sequence.length - 1 && <div className="w-px flex-1 bg-fn-border my-1" />}
                              </div>
                              {/* Content */}
                              <div className="flex-1 pb-5">
                                <div className="flex items-center justify-between mb-1">
                                  <span className="text-xs font-display font-semibold text-fn-text-primary">Touch #{fu.sequence_position}</span>
                                  <span className="text-[10px] font-mono text-fn-text-tertiary">+{fu.send_after_days}d</span>
                                </div>
                                <p className="text-xs font-display font-medium text-fn-text-secondary">{fu.subject}</p>
                                <p className="text-xs text-fn-text-tertiary font-display leading-relaxed whitespace-pre-line mt-1">{fu.body}</p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Personalization */}
                      <div className="p-6 rounded-lg bg-fn-surface border border-fn-border">
                        <div className="text-[11px] font-mono uppercase tracking-wider text-fn-text-tertiary mb-3 flex items-center gap-1.5">
                          <Sparkles className="w-3.5 h-3.5" /> PERSONALIZATION SIGNALS
                        </div>
                        <ul className="space-y-2 text-xs text-fn-text-secondary font-display">
                          {outreachResult.outreach.personalization_notes.map((note, i) => (
                            <li key={i} className="flex items-start gap-2">
                              <span className="text-fn-proof mt-0.5">▸</span> {note}
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* ── Right Column: The Amber Evidence Rail (5/12) ── */}
            <div className="lg:col-span-5">
              <div className="bg-fn-surface rounded-xl border border-fn-border evidence-rail p-6 sticky top-20">
                <div className="flex items-center justify-between pb-4 border-b border-fn-border">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-fn-proof" />
                    <span className="text-xs font-display font-bold text-fn-text-primary uppercase tracking-wider">
                      Grounding Inspector
                    </span>
                  </div>
                  <span className="text-[11px] font-mono text-fn-text-tertiary">
                    {currentFactChecks.length} claims
                  </span>
                </div>

                {/* Scorecard */}
                <div className="mt-4 grid grid-cols-3 gap-2 text-center">
                  <div className="p-3 rounded-lg bg-fn-void border border-fn-border">
                    <div className="text-lg font-display font-bold text-fn-verified tabular-nums">{directlyCount}</div>
                    <div className="text-[9px] font-mono uppercase text-fn-text-tertiary mt-0.5">Verified</div>
                  </div>
                  <div className="p-3 rounded-lg bg-fn-void border border-fn-border">
                    <div className="text-lg font-display font-bold text-fn-text-secondary tabular-nums">{inferenceCount}</div>
                    <div className="text-[9px] font-mono uppercase text-fn-text-tertiary mt-0.5">Inferred</div>
                  </div>
                  <div className="p-3 rounded-lg bg-fn-void border border-fn-border">
                    <div className={`text-lg font-display font-bold tabular-nums ${flaggedCount > 0 ? "text-fn-flagged" : "text-fn-text-tertiary"}`}>{flaggedCount}</div>
                    <div className="text-[9px] font-mono uppercase text-fn-text-tertiary mt-0.5">Flagged</div>
                  </div>
                </div>

                {/* Flagged Alert */}
                {currentFlaggedClaims.length > 0 && (
                  <div className="mt-4 p-3 rounded-lg bg-rose-950/30 border border-rose-800/40 text-xs">
                    <div className="font-mono font-semibold flex items-center gap-1.5 mb-1 text-fn-flagged text-[11px]">
                      <AlertTriangle className="w-3 h-3" /> Unsupported Claims:
                    </div>
                    <ul className="list-disc list-inside space-y-1 text-[11px] text-rose-300/80 font-display">
                      {currentFlaggedClaims.map((claim, idx) => (
                        <li key={idx}>{claim}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Claim List */}
                <div className="mt-5">
                  <div className="text-[10px] font-mono uppercase tracking-wider text-fn-text-tertiary mb-2.5 flex items-center justify-between">
                    <span>{activeTab === "outreach" ? "Outreach Audit" : "Brief Audit"}</span>
                    <span>Status</span>
                  </div>
                  <div className="max-h-72 overflow-y-auto space-y-1.5 pr-1">
                    {currentFactChecks.map((fc, i) => {
                      const isActive = selectedClaim?.claim === fc.claim;
                      return (
                        <button
                          key={i}
                          type="button"
                          onClick={() => setSelectedClaim(fc)}
                          className={`w-full text-left p-3 rounded-lg transition-all text-xs cursor-pointer ${
                            isActive
                              ? "claim-active"
                              : "bg-fn-void border border-fn-border hover:border-fn-border-focus"
                          }`}
                        >
                          <div className="flex items-center justify-between gap-2 mb-1">
                            <span className="font-mono text-[10px] text-fn-text-tertiary">#{i + 1}</span>
                            <StatusBadge status={fc.status} />
                          </div>
                          <p className="text-fn-text-secondary text-xs line-clamp-2 font-display">"{fc.claim}"</p>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Selected Claim Evidence */}
                {selectedClaim && (
                  <div className="mt-5 p-4 rounded-lg bg-fn-void border border-fn-border space-y-2.5">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[10px] text-fn-text-tertiary uppercase tracking-wider">Source Evidence</span>
                      <StatusBadge status={selectedClaim.status} />
                    </div>
                    <p className="text-fn-text-primary font-display text-xs font-medium leading-snug">
                      "{selectedClaim.claim}"
                    </p>
                    <div className="p-3 rounded bg-fn-surface border border-fn-border text-fn-text-secondary font-mono text-[11px] leading-relaxed">
                      <span className="text-fn-proof font-bold block mb-1 text-[10px]">PRIMARY SOURCE CITATION:</span>
                      {selectedClaim.supporting_evidence || "Grounded in source context."}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
