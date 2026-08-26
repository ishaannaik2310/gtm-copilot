"use client";

import React, { useState, useEffect } from "react";
import {
  Building2,
  Globe,
  Search,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Sparkles,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
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
  Terminal,
  Activity,
  Layers,
  FileCheck2,
} from "lucide-react";
import type { FactCheckedBrief, FactCheckResult, ICPFitLabel } from "../types/brief";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

interface StageInfo {
  step: string;
  agent: string;
  desc: string;
}

const STAGES: StageInfo[] = [
  {
    step: "01",
    agent: "ResearchAgent",
    desc: "Ingesting live website HTML & RAG documents",
  },
  {
    step: "02",
    agent: "ICPClassifierAgent",
    desc: "Auditing company signals against sales playbooks",
  },
  {
    step: "03",
    agent: "SynthesisAgent",
    desc: "Compiling strategic pain points & talk tracks",
  },
  {
    step: "04",
    agent: "FactCheckAgent",
    desc: "Deterministic verification of all assertions",
  },
];

export default function Home() {
  const [companyName, setCompanyName] = useState("");
  const [url, setUrl] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [activeStageIndex, setActiveStageIndex] = useState(0);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [briefResult, setBriefResult] = useState<FactCheckedBrief | null>(null);
  const [selectedClaim, setSelectedClaim] = useState<FactCheckResult | null>(null);
  const [copiedTrackIndex, setCopiedTrackIndex] = useState<number | null>(null);
  const [showFullAudit, setShowFullAudit] = useState(false);

  // Stage timer simulation
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isLoading) {
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
  }, [isLoading]);

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const trimmedName = companyName.trim();
    const trimmedUrl = url.trim();

    if (!trimmedName && !trimmedUrl) {
      setError("Please provide at least a Target Company Name or Website URL.");
      return;
    }

    setError(null);
    setBriefResult(null);
    setSelectedClaim(null);
    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/brief`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          company_name: trimmedName || undefined,
          url: trimmedUrl || undefined,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const message =
          errorData.detail ||
          `Backend returned HTTP ${response.status}: ${response.statusText}`;
        throw new Error(message);
      }

      const data: FactCheckedBrief = await response.json();
      setBriefResult(data);
      if (data.fact_checks.length > 0) {
        setSelectedClaim(data.fact_checks[0]);
      }
    } catch (err: any) {
      console.error("API error:", err);
      if (
        err.message?.includes("Failed to fetch") ||
        err.message?.includes("NetworkError")
      ) {
        setError(
          `Cannot reach backend server at ${API_BASE_URL}. Ensure FastAPI is running via 'python run_dev.py'.`
        );
      } else {
        setError(err.message || "Failed to generate account brief.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleApplyPreset = (name: string, targetUrl: string) => {
    setCompanyName(name);
    setUrl(targetUrl);
    setError(null);
  };

  const handleCopyTrack = (text: string, index: number) => {
    navigator.clipboard.writeText(text);
    setCopiedTrackIndex(index);
    setTimeout(() => setCopiedTrackIndex(null), 2000);
  };

  const getFitBadge = (label: ICPFitLabel, score: number | null) => {
    switch (label) {
      case "strong_fit":
        return {
          badgeClass: "bg-emerald-950/80 text-emerald-300 border-emerald-500/40",
          dotClass: "bg-emerald-400 shadow-sm shadow-emerald-500/50",
          label: "Strong ICP Fit",
          scoreText: score !== null ? `${Math.round(score * 100)}%` : null,
        };
      case "possible_fit":
        return {
          badgeClass: "bg-amber-950/80 text-amber-300 border-amber-500/40",
          dotClass: "bg-amber-400 shadow-sm shadow-amber-500/50",
          label: "Possible Fit",
          scoreText: score !== null ? `${Math.round(score * 100)}%` : null,
        };
      case "poor_fit":
        return {
          badgeClass: "bg-rose-950/80 text-rose-300 border-rose-500/40",
          dotClass: "bg-rose-400 shadow-sm shadow-rose-500/50",
          label: "Poor Fit",
          scoreText: score !== null ? `${Math.round(score * 100)}%` : null,
        };
      case "unknown":
      default:
        return {
          badgeClass: "bg-slate-900 text-slate-400 border-slate-700",
          dotClass: "bg-slate-500",
          label: "Unassessed",
          scoreText: "N/A",
        };
    }
  };

  const getStatusBadge = (status: FactCheckResult["status"]) => {
    switch (status) {
      case "directly_supported":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-mono font-semibold bg-emerald-950/90 text-emerald-300 border border-emerald-500/40">
            <CheckCircle2 className="w-3 h-3 text-emerald-400" />
            DIRECTLY SUPPORTED
          </span>
        );
      case "reasonable_inference":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-mono font-semibold bg-sky-950/90 text-sky-300 border border-sky-500/40">
            <Sparkles className="w-3 h-3 text-sky-400" />
            REASONABLE INFERENCE
          </span>
        );
      case "unsupported":
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-mono font-semibold bg-rose-950/90 text-rose-300 border border-rose-500/40">
            <AlertTriangle className="w-3 h-3 text-rose-400" />
            UNSUPPORTED / FLAGGED
          </span>
        );
    }
  };

  const directlyCount =
    briefResult?.fact_checks.filter((f) => f.status === "directly_supported")
      .length || 0;
  const inferenceCount =
    briefResult?.fact_checks.filter((f) => f.status === "reasonable_inference")
      .length || 0;
  const flaggedCount = briefResult?.flagged_claims.length || 0;

  return (
    <main className="min-h-screen bg-obsidian-950 text-slate-200 selection:bg-emerald-500/20 selection:text-emerald-300">
      {/* Top Telemetry Bar */}
      <header className="sticky top-0 z-40 bg-obsidian-900/90 backdrop-blur-md border-b border-obsidian-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 font-bold">
              <Zap className="w-4 h-4" />
            </div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-sm tracking-tight text-white">
                GTM OPS COPILOT
              </span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-obsidian-800 border border-obsidian-700 text-slate-400">
                v1.0
              </span>
            </div>
          </div>

          <div className="flex items-center gap-4 text-xs font-mono text-slate-400">
            <div className="hidden sm:flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              <span className="text-slate-300">HYBRID RAG + VERIFICATION ENGINE</span>
            </div>
          </div>
        </div>
      </header>

      {/* Hero & Command Deck */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 pt-8 pb-16">
        {/* Title Bar */}
        <div className="mb-6">
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight flex items-center gap-3">
            Account Intelligence Dossier
            <span className="text-xs font-mono font-normal px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Deterministic Fact Audit
            </span>
          </h1>
          <p className="mt-1 text-xs sm:text-sm text-slate-400 max-w-3xl">
            Live web research synthesized with internal sales playbooks and audited
            against primary source context to eliminate AI hallucinations.
          </p>
        </div>

        {/* Command Input Card */}
        <div className="bg-obsidian-900 rounded-xl border border-obsidian-800 p-5 sm:p-6 mb-8 shadow-xl shadow-black/40">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-1.5 flex items-center gap-1.5">
                  <Building2 className="w-3.5 h-3.5 text-emerald-400" />
                  Target Company Name
                </label>
                <input
                  type="text"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  placeholder="e.g. Notion"
                  disabled={isLoading}
                  className="w-full px-3.5 py-2 rounded-lg bg-obsidian-950 border border-obsidian-700 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-colors disabled:opacity-50"
                />
              </div>

              <div>
                <label className="block text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-1.5 flex items-center gap-1.5">
                  <Globe className="w-3.5 h-3.5 text-sky-400" />
                  Target Company URL
                </label>
                <input
                  type="url"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://www.notion.so"
                  disabled={isLoading}
                  className="w-full px-3.5 py-2 rounded-lg bg-obsidian-950 border border-obsidian-700 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-colors disabled:opacity-50"
                />
              </div>
            </div>

            {/* Presets and Compile Action */}
            <div className="pt-3 flex flex-col sm:flex-row items-center justify-between gap-3 border-t border-obsidian-800">
              <div className="flex items-center gap-2 text-xs text-slate-400 w-full sm:w-auto">
                <span className="font-mono text-[11px] text-slate-500 uppercase">
                  Validated Preset:
                </span>
                <button
                  type="button"
                  onClick={() =>
                    handleApplyPreset("Notion", "https://www.notion.so")
                  }
                  disabled={isLoading}
                  className="px-2.5 py-1 rounded bg-obsidian-800 hover:bg-obsidian-700 text-slate-200 text-xs font-mono border border-obsidian-700 transition-colors disabled:opacity-50 flex items-center gap-1.5 cursor-pointer"
                >
                  <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                  Notion (notion.so)
                </button>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full sm:w-auto px-5 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 active:bg-emerald-600 text-obsidian-950 text-xs font-mono font-bold tracking-wider uppercase transition-all flex items-center justify-center gap-2 disabled:bg-slate-700 disabled:text-slate-400 disabled:cursor-not-allowed cursor-pointer shadow-lg shadow-emerald-500/10"
              >
                {isLoading ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    Executing Pipeline...
                  </>
                ) : (
                  <>
                    <Terminal className="w-3.5 h-3.5" />
                    Compile Account Dossier
                  </>
                )}
              </button>
            </div>
          </form>
        </div>

        {/* Error Notification */}
        {error && (
          <div className="bg-rose-950/40 border border-rose-500/40 rounded-xl p-4 mb-8 flex items-start gap-3 text-rose-200 shadow-md">
            <XCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <div className="text-xs">
              <h3 className="font-bold text-rose-300 font-mono">
                Pipeline Execution Error
              </h3>
              <p className="mt-0.5 text-rose-200/90 leading-relaxed font-mono">
                {error}
              </p>
            </div>
          </div>
        )}

        {/* Live Execution Telemetry Stepper */}
        {isLoading && (
          <div className="bg-obsidian-900 rounded-xl border border-obsidian-800 p-6 sm:p-8 mb-8 shadow-xl">
            <div className="flex items-center justify-between mb-6 pb-4 border-b border-obsidian-800">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                  <Activity className="w-4 h-4 animate-pulse" />
                </div>
                <div>
                  <h3 className="font-mono text-xs font-bold text-white uppercase tracking-wider">
                    Agent Pipeline In Progress
                  </h3>
                  <p className="text-[11px] font-mono text-slate-400">
                    Executing 4 sequential LLM stages with RAG grounding
                  </p>
                </div>
              </div>
              <div className="font-mono text-xs text-emerald-400 bg-emerald-950/80 px-2.5 py-1 rounded border border-emerald-500/30">
                {elapsedSeconds}s elapsed
              </div>
            </div>

            {/* Stepper Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
              {STAGES.map((s, idx) => {
                const isDone = idx < activeStageIndex;
                const isCurrent = idx === activeStageIndex;
                return (
                  <div
                    key={s.step}
                    className={`p-3.5 rounded-lg border transition-all ${
                      isCurrent
                        ? "bg-obsidian-850 border-emerald-500/60 shadow-lg shadow-emerald-500/5"
                        : isDone
                        ? "bg-obsidian-950 border-obsidian-700 opacity-90"
                        : "bg-obsidian-950/50 border-obsidian-800 opacity-40"
                    }`}
                  >
                    <div className="flex items-center justify-between text-[11px] font-mono mb-1">
                      <span
                        className={`font-bold ${
                          isCurrent
                            ? "text-emerald-400"
                            : isDone
                            ? "text-slate-400"
                            : "text-slate-600"
                        }`}
                      >
                        STAGE {s.step}
                      </span>
                      {isDone ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                      ) : isCurrent ? (
                        <RefreshCw className="w-3.5 h-3.5 text-emerald-400 animate-spin" />
                      ) : (
                        <div className="w-2.5 h-2.5 rounded-full bg-obsidian-700"></div>
                      )}
                    </div>
                    <p className="text-xs font-bold text-slate-200">
                      {s.agent}
                    </p>
                    <p className="text-[11px] text-slate-400 mt-1 leading-snug">
                      {s.desc}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Dossier Output */}
        {briefResult && !isLoading && (
          <div className="space-y-6 animate-in fade-in duration-300">
            {/* Header Hero Strip */}
            <div className="bg-obsidian-900 rounded-xl border border-obsidian-800 p-6 shadow-xl">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-obsidian-800">
                <div>
                  <div className="flex flex-wrap items-center gap-3">
                    <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                      {briefResult.brief.company_name}
                    </h2>
                    <span className="px-2.5 py-0.5 rounded text-xs font-mono font-medium bg-obsidian-800 text-slate-300 border border-obsidian-700">
                      {briefResult.brief.industry}
                    </span>
                  </div>

                  {briefResult.brief.source_urls.length > 0 && (
                    <div className="mt-2 flex items-center gap-2 text-xs font-mono text-slate-400">
                      <Globe className="w-3.5 h-3.5 text-slate-500" />
                      {briefResult.brief.source_urls.map((sourceUrl) => (
                        <a
                          key={sourceUrl}
                          href={sourceUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="hover:text-emerald-400 underline flex items-center gap-1 transition-colors"
                        >
                          {sourceUrl}
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      ))}
                    </div>
                  )}
                </div>

                {/* Top Metrics Badges */}
                <div className="flex flex-wrap items-center gap-3">
                  {/* ICP Fit Badge */}
                  {(() => {
                    const fit = getFitBadge(
                      briefResult.brief.icp_classification.fit_label,
                      briefResult.brief.icp_classification.fit_score
                    );
                    return (
                      <div
                        className={`px-3 py-1.5 rounded-lg border flex items-center gap-2 text-xs font-mono font-bold ${fit.badgeClass}`}
                      >
                        <span className={`w-2 h-2 rounded-full ${fit.dotClass}`}></span>
                        <span>{fit.label}</span>
                        {fit.scoreText && (
                          <span className="text-slate-300 font-normal">
                            [{fit.scoreText}]
                          </span>
                        )}
                      </div>
                    );
                  })()}

                  {/* Faithfulness Score Badge */}
                  <div
                    className={`px-3 py-1.5 rounded-lg border flex items-center gap-2 text-xs font-mono font-bold ${
                      briefResult.overall_faithfulness_score >= 0.8
                        ? "bg-emerald-950/80 text-emerald-300 border-emerald-500/40"
                        : "bg-amber-950/80 text-amber-300 border-amber-500/40"
                    }`}
                  >
                    <ShieldCheck className="w-4 h-4 text-emerald-400" />
                    <span>
                      {Math.round(briefResult.overall_faithfulness_score * 100)}%
                      FAITHFULNESS
                    </span>
                    {briefResult.flagged_claims.length > 0 && (
                      <span className="px-1.5 py-0.5 rounded bg-rose-900 text-rose-200 text-[10px]">
                        {briefResult.flagged_claims.length} FLAGGED
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* ICP Qualification Breakdown */}
              <div className="mt-5 p-4 rounded-lg bg-obsidian-950 border border-obsidian-800">
                <div className="flex items-center gap-2 text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-2">
                  <Target className="w-3.5 h-3.5 text-emerald-400" />
                  ICP Qualification Rationale
                </div>
                <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
                  {briefResult.brief.icp_classification.rationale}
                </p>

                {(briefResult.brief.icp_classification.matched_criteria.length > 0 ||
                  briefResult.brief.icp_classification.mismatched_criteria.length > 0) && (
                  <div className="mt-3 pt-3 border-t border-obsidian-800 grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-mono">
                    {briefResult.brief.icp_classification.matched_criteria.length > 0 && (
                      <div>
                        <span className="text-emerald-400 font-semibold flex items-center gap-1.5 mb-1">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Matched Criteria:
                        </span>
                        <ul className="space-y-1 text-slate-400">
                          {briefResult.brief.icp_classification.matched_criteria.map(
                            (c, i) => (
                              <li key={i} className="flex items-start gap-1.5">
                                <span className="text-emerald-500">✓</span> {c}
                              </li>
                            )
                          )}
                        </ul>
                      </div>
                    )}
                    {briefResult.brief.icp_classification.mismatched_criteria.length > 0 && (
                      <div>
                        <span className="text-rose-400 font-semibold flex items-center gap-1.5 mb-1">
                          <XCircle className="w-3.5 h-3.5" /> Stage / Signal Gaps:
                        </span>
                        <ul className="space-y-1 text-slate-400">
                          {briefResult.brief.icp_classification.mismatched_criteria.map(
                            (c, i) => (
                              <li key={i} className="flex items-start gap-1.5">
                                <span className="text-rose-500">✗</span> {c}
                              </li>
                            )
                          )}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* 2-Column Split: Brief Content (Left) & Verification Inspector (Right) */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              {/* Left Column: Intelligence Sections (7 Cols) */}
              <div className="lg:col-span-7 space-y-6">
                {/* Executive Summary */}
                <div className="bg-obsidian-900 rounded-xl border border-obsidian-800 p-6 shadow-xl">
                  <div className="flex items-center gap-2 text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-3">
                    <FileText className="w-3.5 h-3.5 text-emerald-400" />
                    Executive Brief
                  </div>
                  <p className="text-slate-200 text-xs sm:text-sm leading-relaxed">
                    {briefResult.brief.executive_summary}
                  </p>
                </div>

                {/* Key Offerings & Capabilities */}
                <div className="bg-obsidian-900 rounded-xl border border-obsidian-800 p-6 shadow-xl">
                  <div className="flex items-center gap-2 text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-4">
                    <Boxes className="w-3.5 h-3.5 text-sky-400" />
                    Key Products & Services
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {briefResult.brief.key_products_or_services.map((product, i) => (
                      <span
                        key={i}
                        className="px-2.5 py-1 rounded bg-obsidian-950 text-slate-300 text-xs font-mono border border-obsidian-700"
                      >
                        {product}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Likely Operational Pain Points */}
                <div className="bg-obsidian-900 rounded-xl border border-obsidian-800 p-6 shadow-xl">
                  <div className="flex items-center gap-2 text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-4">
                    <Flame className="w-3.5 h-3.5 text-amber-400" />
                    Likely Target Pain Points
                  </div>
                  <ul className="space-y-3">
                    {briefResult.brief.likely_pain_points.map((pain, i) => (
                      <li
                        key={i}
                        className="p-3 rounded-lg bg-obsidian-950 border border-obsidian-800 text-xs sm:text-sm text-slate-300 leading-relaxed flex items-start gap-2.5"
                      >
                        <span className="w-1.5 h-1.5 rounded-full bg-amber-400 shrink-0 mt-2"></span>
                        <span>{pain}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Suggested Talk Tracks */}
                <div className="bg-obsidian-900 rounded-xl border border-obsidian-800 p-6 shadow-xl">
                  <div className="flex items-center gap-2 text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-4">
                    <MessageSquare className="w-3.5 h-3.5 text-indigo-400" />
                    Actionable Talk Tracks for Sales Reps
                  </div>
                  <div className="space-y-3.5">
                    {briefResult.brief.suggested_talk_tracks.map((track, i) => (
                      <div
                        key={i}
                        className="p-4 rounded-lg bg-obsidian-950 border border-obsidian-800 flex items-start justify-between gap-4 group hover:border-obsidian-700 transition-colors"
                      >
                        <p className="text-xs sm:text-sm text-slate-300 leading-relaxed italic">
                          {track}
                        </p>
                        <button
                          onClick={() => handleCopyTrack(track, i)}
                          className="p-2 rounded bg-obsidian-900 hover:bg-obsidian-800 text-slate-400 hover:text-white border border-obsidian-700 transition-all shrink-0 cursor-pointer"
                          title="Copy talk track"
                        >
                          {copiedTrackIndex === i ? (
                            <Check className="w-3.5 h-3.5 text-emerald-400" />
                          ) : (
                            <Copy className="w-3.5 h-3.5" />
                          )}
                        </button>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Objection Handling Notes */}
                {briefResult.brief.objection_handling_notes.length > 0 && (
                  <div className="bg-obsidian-900 rounded-xl border border-obsidian-800 p-6 shadow-xl">
                    <div className="flex items-center gap-2 text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-4">
                      <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                      Objection Handling Notes
                    </div>
                    <div className="space-y-3">
                      {briefResult.brief.objection_handling_notes.map((note, i) => (
                        <div
                          key={i}
                          className="p-3.5 rounded-lg bg-obsidian-950 border border-obsidian-800 text-xs text-slate-300 leading-relaxed font-mono"
                        >
                          {note}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Right Column: Signature Verification Audit Inspector (5 Cols) */}
              <div className="lg:col-span-5 space-y-6">
                <div className="bg-obsidian-900 rounded-xl border border-obsidian-800 p-6 shadow-xl sticky top-20">
                  <div className="flex items-center justify-between pb-4 border-b border-obsidian-800">
                    <div className="flex items-center gap-2 text-xs font-mono font-bold text-white uppercase tracking-wider">
                      <ShieldCheck className="w-4 h-4 text-emerald-400" />
                      Verification Inspector
                    </div>
                    <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-500/30">
                      {briefResult.fact_checks.length} Claims Audited
                    </span>
                  </div>

                  {/* Audit Metric Counters */}
                  <div className="mt-4 grid grid-cols-3 gap-2 text-center font-mono">
                    <div className="p-2.5 rounded bg-obsidian-950 border border-obsidian-800">
                      <div className="text-base font-bold text-emerald-400">
                        {directlyCount}
                      </div>
                      <div className="text-[10px] text-slate-400 uppercase">
                        Direct Quotes
                      </div>
                    </div>
                    <div className="p-2.5 rounded bg-obsidian-950 border border-obsidian-800">
                      <div className="text-base font-bold text-sky-400">
                        {inferenceCount}
                      </div>
                      <div className="text-[10px] text-slate-400 uppercase">
                        Inferences
                      </div>
                    </div>
                    <div className="p-2.5 rounded bg-obsidian-950 border border-obsidian-800">
                      <div className="text-base font-bold text-rose-400">
                        {flaggedCount}
                      </div>
                      <div className="text-[10px] text-slate-400 uppercase">
                        Flagged
                      </div>
                    </div>
                  </div>

                  {/* Flagged Claims Alert */}
                  {briefResult.flagged_claims.length > 0 && (
                    <div className="mt-4 p-3 rounded bg-rose-950/40 border border-rose-500/30 text-xs text-rose-300 font-mono">
                      <div className="font-bold flex items-center gap-1.5 text-rose-400 mb-1">
                        <AlertTriangle className="w-3.5 h-3.5" /> Flagged Claims Requiring Review:
                      </div>
                      <ul className="list-disc list-inside space-y-1 text-rose-200 text-[11px]">
                        {briefResult.flagged_claims.map((claim, idx) => (
                          <li key={idx}>{claim}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Interactive Claim Inspector */}
                  <div className="mt-5">
                    <div className="text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-2.5">
                      Select Claim to Inspect Grounding:
                    </div>
                    <div className="max-h-72 overflow-y-auto space-y-2 pr-1">
                      {briefResult.fact_checks.map((fc, i) => {
                        const isSelected = selectedClaim?.claim === fc.claim;
                        return (
                          <button
                            key={i}
                            type="button"
                            onClick={() => setSelectedClaim(fc)}
                            className={`w-full text-left p-2.5 rounded border transition-all text-xs cursor-pointer ${
                              isSelected
                                ? "bg-obsidian-800 border-emerald-500/50 shadow-md"
                                : "bg-obsidian-950 border-obsidian-800 hover:border-obsidian-700"
                            }`}
                          >
                            <div className="flex items-center justify-between gap-2 mb-1">
                              <span className="font-mono text-[10px] text-slate-400">
                                CLAIM #{i + 1}
                              </span>
                              {getStatusBadge(fc.status)}
                            </div>
                            <p className="text-slate-200 text-[11px] line-clamp-2">
                              "{fc.claim}"
                            </p>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Selected Claim Grounding Detail Card */}
                  {selectedClaim && (
                    <div className="mt-5 p-4 rounded-lg bg-obsidian-950 border border-emerald-500/30 text-xs space-y-2.5">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-[11px] text-emerald-400 font-bold uppercase">
                          Grounding Evidence & Citations:
                        </span>
                        {getStatusBadge(selectedClaim.status)}
                      </div>

                      <p className="text-slate-200 font-medium text-xs leading-snug">
                        "{selectedClaim.claim}"
                      </p>

                      <div className="p-3 rounded bg-obsidian-900 border border-obsidian-800 text-slate-300 font-mono text-[11px] leading-relaxed">
                        <span className="text-emerald-400 font-semibold">CITED EVIDENCE: </span>
                        {selectedClaim.supporting_evidence || "No evidence citation available."}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
