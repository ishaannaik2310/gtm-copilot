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
  Terminal,
  Activity,
  ArrowRight,
  Send,
  User,
  Compass,
  FileSearch,
  ChevronRight,
  Clock,
  Layers,
} from "lucide-react";
import type {
  AccountBrief,
  FactCheckedBrief,
  FactCheckedOutreach,
  FactCheckResult,
  ICPFitLabel,
} from "../types/brief";

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
    desc: "Ingesting live website HTML & Playbook context",
  },
  {
    step: "02",
    agent: "ICPClassifierAgent",
    desc: "Auditing company signals against sales ICP rules",
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
  // Navigation Mode: "brief" or "outreach"
  const [activeTab, setActiveTab] = useState<"brief" | "outreach">("brief");

  // Brief generation inputs
  const [companyName, setCompanyName] = useState("Notion");
  const [url, setUrl] = useState("https://www.notion.so");
  const [isLoadingBrief, setIsLoadingBrief] = useState(false);
  const [activeStageIndex, setActiveStageIndex] = useState(0);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // Outreach generation inputs
  const [contactName, setContactName] = useState("Alex Chen");
  const [contactRole, setContactRole] = useState("VP of Sales");
  const [contactNotes, setContactNotes] = useState(
    "Focused on expanding Notion's enterprise sales footprint and sales engineering enablement."
  );
  const [isLoadingOutreach, setIsLoadingOutreach] = useState(false);
  const [selectedEmailToneIndex, setSelectedEmailToneIndex] = useState(0);

  // Results
  const [briefResult, setBriefResult] = useState<FactCheckedBrief | null>(null);
  const [outreachResult, setOutreachResult] = useState<FactCheckedOutreach | null>(null);

  // Evidence Inspector state
  const [selectedClaim, setSelectedClaim] = useState<FactCheckResult | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  // Active fact-checks depending on active tab
  const currentFactChecks: FactCheckResult[] =
    activeTab === "outreach" && outreachResult
      ? outreachResult.fact_checks
      : briefResult
      ? briefResult.fact_checks
      : [];

  const currentFaithfulnessScore: number =
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

  // Stage timer simulation
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

  // Handle Account Brief Generation
  const handleGenerateBrief = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const trimmedName = companyName.trim();
    const trimmedUrl = url.trim();

    if (!trimmedName && !trimmedUrl) {
      setError("Please provide at least a Target Company Name or Website URL.");
      return;
    }

    setError(null);
    setBriefResult(null);
    setOutreachResult(null);
    setSelectedClaim(null);
    setIsLoadingBrief(true);

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
        throw new Error(
          errorData.detail ||
            `Backend returned HTTP ${response.status}: ${response.statusText}`
        );
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
      setIsLoadingBrief(false);
    }
  };

  // Handle Outreach Cadence Generation
  const handleGenerateOutreach = async () => {
    if (!briefResult) {
      setError("Generate an Account Brief first before compiling outreach.");
      return;
    }

    setError(null);
    setIsLoadingOutreach(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/outreach`, {
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
        throw new Error(
          errorData.detail ||
            `Backend returned HTTP ${response.status}: ${response.statusText}`
        );
      }

      const data: FactCheckedOutreach = await response.json();
      setOutreachResult(data);
      setActiveTab("outreach");
      if (data.fact_checks.length > 0) {
        setSelectedClaim(data.fact_checks[0]);
      }
    } catch (err: any) {
      console.error("Outreach API error:", err);
      setError(err.message || "Failed to generate personalized outreach.");
    } finally {
      setIsLoadingOutreach(false);
    }
  };

  const handleCopyText = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const getFitBadge = (label: ICPFitLabel, score: number | null) => {
    switch (label) {
      case "strong_fit":
        return {
          badgeClass: "bg-emerald-950/40 text-emerald-400 border-emerald-800/60",
          dotClass: "bg-emerald-400",
          label: "Strong ICP Fit",
          scoreText: score !== null ? `${Math.round(score * 100)}%` : null,
        };
      case "possible_fit":
        return {
          badgeClass: "bg-neutral-900 text-neutral-300 border-neutral-700",
          dotClass: "bg-neutral-400",
          label: "Possible Fit",
          scoreText: score !== null ? `${Math.round(score * 100)}%` : null,
        };
      case "poor_fit":
        return {
          badgeClass: "bg-neutral-900 text-neutral-400 border-neutral-800",
          dotClass: "bg-neutral-500",
          label: "Strategic / Out-of-ICP",
          scoreText: score !== null ? `${Math.round(score * 100)}%` : null,
        };
      case "unknown":
      default:
        return {
          badgeClass: "bg-neutral-900 text-neutral-500 border-neutral-800",
          dotClass: "bg-neutral-600",
          label: "Unassessed",
          scoreText: "N/A",
        };
    }
  };

  const getStatusBadge = (status: FactCheckResult["status"]) => {
    switch (status) {
      case "directly_supported":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-mono font-medium bg-emerald-950/50 text-emerald-400 border border-emerald-800/50">
            <CheckCircle2 className="w-3 h-3" />
            Direct Quote
          </span>
        );
      case "reasonable_inference":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-mono font-medium bg-neutral-800 text-neutral-300 border border-neutral-700">
            <Compass className="w-3 h-3 text-neutral-400" />
            Logical Inference
          </span>
        );
      case "unsupported":
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-mono font-medium bg-rose-950/50 text-rose-400 border border-rose-800/50">
            <AlertTriangle className="w-3 h-3" />
            Unsupported
          </span>
        );
    }
  };

  const directlyCount =
    currentFactChecks.filter((f) => f.status === "directly_supported").length ||
    0;
  const inferenceCount =
    currentFactChecks.filter((f) => f.status === "reasonable_inference")
      .length || 0;
  const flaggedCount = currentFlaggedClaims.length;

  return (
    <main className="min-h-[100dvh] bg-black text-neutral-100 bg-vercel-grid bg-vercel-radial selection:bg-neutral-800">
      {/* Vercel Style Minimalist Header */}
      <header className="sticky top-0 z-40 bg-black/80 backdrop-blur-md border-b border-neutral-800/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <span className="text-white text-base">▲</span>
              <span className="font-bold text-sm tracking-tight text-white">
                GTM Copilot
              </span>
            </div>
            <div className="h-4 w-[1px] bg-neutral-800"></div>
            <span className="text-xs text-neutral-400 hidden sm:inline-block">
              Sales Intelligence & Outreach
            </span>
          </div>

          <div className="flex items-center gap-3 text-xs">
            <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-neutral-900 border border-neutral-800 text-neutral-300 font-mono text-[11px]">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              <span>gemini-3.5-flash</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 pt-8 pb-20">
        {/* Command & Ingestion Card */}
        <div className="bg-[#0A0A0A] rounded-xl border border-neutral-800 p-6 mb-8 shadow-2xl">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-neutral-800/80">
            <div>
              <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
                Account Research & Grounded Outreach
              </h1>
              <p className="mt-1 text-sm text-neutral-400">
                Generate verified account dossiers and personalized cold email sequences grounded in source facts.
              </p>
            </div>

            {/* Segmented Mode Switcher */}
            <div className="flex items-center p-1 rounded-lg bg-neutral-900 border border-neutral-800 self-start sm:self-auto text-xs">
              <button
                type="button"
                onClick={() => setActiveTab("brief")}
                className={`px-3.5 py-1.5 rounded-md font-medium transition-all cursor-pointer ${
                  activeTab === "brief"
                    ? "bg-neutral-800 text-white shadow-sm"
                    : "text-neutral-400 hover:text-neutral-200"
                }`}
              >
                1. Account Dossier
              </button>
              <button
                type="button"
                onClick={() => {
                  if (briefResult) setActiveTab("outreach");
                  else setError("Generate an Account Brief first to unlock Outreach Studio.");
                }}
                className={`px-3.5 py-1.5 rounded-md font-medium transition-all cursor-pointer flex items-center gap-1.5 ${
                  activeTab === "outreach"
                    ? "bg-neutral-800 text-white shadow-sm"
                    : "text-neutral-400 hover:text-neutral-200"
                }`}
              >
                2. Outreach Studio
                {outreachResult && (
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                )}
              </button>
            </div>
          </div>

          {/* Form Input Row */}
          <form onSubmit={handleGenerateBrief} className="mt-6 space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-neutral-400 mb-1.5">
                  Company Name
                </label>
                <div className="relative">
                  <Building2 className="w-4 h-4 absolute left-3 top-3 text-neutral-500" />
                  <input
                    type="text"
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    placeholder="e.g. Notion"
                    disabled={isLoadingBrief || isLoadingOutreach}
                    className="w-full pl-9 pr-3 py-2 rounded-lg bg-neutral-900 border border-neutral-800 text-white placeholder-neutral-500 text-sm focus:outline-none focus:border-neutral-600 transition-colors disabled:opacity-50"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-neutral-400 mb-1.5">
                  Company URL
                </label>
                <div className="relative">
                  <Globe className="w-4 h-4 absolute left-3 top-3 text-neutral-500" />
                  <input
                    type="url"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="https://www.notion.so"
                    disabled={isLoadingBrief || isLoadingOutreach}
                    className="w-full pl-9 pr-3 py-2 rounded-lg bg-neutral-900 border border-neutral-800 text-white placeholder-neutral-500 text-sm focus:outline-none focus:border-neutral-600 transition-colors disabled:opacity-50"
                  />
                </div>
              </div>
            </div>

            <div className="pt-2 flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-2 text-xs text-neutral-400 w-full sm:w-auto">
                <span className="text-neutral-500">Preset:</span>
                <button
                  type="button"
                  onClick={() => {
                    setCompanyName("Notion");
                    setUrl("https://www.notion.so");
                    setError(null);
                  }}
                  disabled={isLoadingBrief || isLoadingOutreach}
                  className="px-2.5 py-1 rounded-md bg-neutral-900 hover:bg-neutral-800 text-neutral-300 text-xs border border-neutral-800 hover:border-neutral-700 transition-all flex items-center gap-1.5 cursor-pointer"
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                  Notion (notion.so)
                </button>
              </div>

              <button
                type="submit"
                disabled={isLoadingBrief || isLoadingOutreach}
                className="w-full sm:w-auto px-5 py-2.5 rounded-lg bg-white hover:bg-neutral-200 text-black text-xs font-semibold tracking-wide transition-all flex items-center justify-center gap-2 disabled:bg-neutral-700 disabled:text-neutral-400 cursor-pointer shadow-sm btn-tactile"
              >
                {isLoadingBrief ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin text-black" />
                    Generating Account Brief...
                  </>
                ) : (
                  <>
                    <Zap className="w-3.5 h-3.5 text-black" />
                    Run Research & Audit
                  </>
                )}
              </button>
            </div>
          </form>
        </div>

        {/* Error Callout */}
        {error && (
          <div className="bg-rose-950/30 border border-rose-800/60 rounded-xl p-4 mb-8 flex items-start gap-3 text-rose-400 shadow-sm">
            <XCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-400" />
            <div className="text-xs">
              <span className="font-semibold block text-rose-300">
                Pipeline Error
              </span>
              <p className="mt-0.5 text-rose-400/90">{error}</p>
            </div>
          </div>
        )}

        {/* Pipeline Stepper Progress */}
        {(isLoadingBrief || isLoadingOutreach) && (
          <div className="bg-[#0A0A0A] rounded-xl border border-neutral-800 p-6 mb-8 shadow-2xl">
            <div className="flex items-center justify-between mb-5 pb-3 border-b border-neutral-800/80">
              <div className="flex items-center gap-2.5">
                <Activity className="w-4 h-4 text-emerald-400 animate-pulse" />
                <span className="text-xs font-semibold text-white tracking-wide">
                  {isLoadingOutreach
                    ? "Generating Personalized Outreach Cadence"
                    : "Executing 4-Stage Research & Verification Pipeline"}
                </span>
              </div>
              <span className="text-xs font-mono text-neutral-400 bg-neutral-900 px-2.5 py-1 rounded-full border border-neutral-800">
                {elapsedSeconds}s elapsed
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
              {STAGES.map((s, idx) => {
                const isDone = idx < activeStageIndex;
                const isCurrent = idx === activeStageIndex;
                return (
                  <div
                    key={s.step}
                    className={`p-3.5 rounded-lg border transition-all ${
                      isCurrent
                        ? "bg-neutral-900 border-neutral-600 shadow-sm"
                        : isDone
                        ? "bg-neutral-950/60 border-neutral-800 text-neutral-300"
                        : "bg-neutral-950/30 border-neutral-900 opacity-40"
                    }`}
                  >
                    <div className="flex items-center justify-between text-[10px] font-mono mb-1.5">
                      <span className={isCurrent ? "text-white font-bold" : "text-neutral-500"}>
                        STAGE {s.step}
                      </span>
                      {isDone ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                      ) : isCurrent ? (
                        <RefreshCw className="w-3.5 h-3.5 text-white animate-spin" />
                      ) : (
                        <span className="w-1.5 h-1.5 rounded-full bg-neutral-700"></span>
                      )}
                    </div>
                    <p className="text-xs font-semibold text-white">{s.agent}</p>
                    <p className="text-[11px] text-neutral-400 mt-1 leading-snug">{s.desc}</p>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Empty State */}
        {!briefResult && !isLoadingBrief && (
          <div className="bg-[#0A0A0A] rounded-xl border border-neutral-800 p-12 text-center shadow-2xl space-y-4">
            <div className="w-12 h-12 rounded-xl bg-neutral-900 border border-neutral-800 mx-auto flex items-center justify-center text-neutral-400">
              <FileSearch className="w-6 h-6 text-white" />
            </div>
            <div className="max-w-md mx-auto space-y-1.5">
              <h3 className="text-base font-semibold text-white">
                No Account Brief Generated
              </h3>
              <p className="text-xs text-neutral-400 leading-relaxed">
                Enter a target company name or URL above and click{" "}
                <span className="text-neutral-200 font-medium">
                  "Run Research & Audit"
                </span>{" "}
                to generate a fact-checked brief and cold outreach sequence.
              </p>
            </div>
            <div className="pt-2">
              <button
                type="button"
                onClick={handleGenerateBrief}
                className="px-4 py-2 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white text-xs font-medium border border-neutral-700 transition-all inline-flex items-center gap-2 cursor-pointer btn-tactile"
              >
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                Run Preset (Notion)
              </button>
            </div>
          </div>
        )}

        {/* Intelligence Workspace (60% Main / 40% Evidence Inspector) */}
        {briefResult && !isLoadingBrief && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
            {/* Left 60%: Main Content */}
            <div className="lg:col-span-7 space-y-6">
              {/* Company Hero Card */}
              <div className="bg-[#0A0A0A] rounded-xl border border-neutral-800 p-6 shadow-2xl">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-neutral-800">
                  <div>
                    <div className="flex items-center gap-3">
                      <h2 className="text-2xl font-bold tracking-tight text-white">
                        {briefResult.brief.company_name}
                      </h2>
                      <span className="px-2.5 py-0.5 rounded-full text-xs font-mono bg-neutral-900 text-neutral-300 border border-neutral-800">
                        {briefResult.brief.industry}
                      </span>
                    </div>

                    {briefResult.brief.source_urls.length > 0 && (
                      <div className="mt-2 flex items-center gap-2 text-xs font-mono text-neutral-400">
                        <Globe className="w-3.5 h-3.5 text-neutral-500" />
                        {briefResult.brief.source_urls.map((sourceUrl) => (
                          <a
                            key={sourceUrl}
                            href={sourceUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="hover:text-white underline flex items-center gap-1 transition-colors"
                          >
                            {sourceUrl}
                            <ExternalLink className="w-2.5 h-2.5" />
                          </a>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* ICP Fit Badge */}
                  {(() => {
                    const fit = getFitBadge(
                      briefResult.brief.icp_classification.fit_label,
                      briefResult.brief.icp_classification.fit_score
                    );
                    return (
                      <div
                        className={`px-3 py-1.5 rounded-full border flex items-center gap-2 text-xs font-medium ${fit.badgeClass}`}
                      >
                        <span className={`w-2 h-2 rounded-full ${fit.dotClass}`}></span>
                        <span>{fit.label}</span>
                        {fit.scoreText && (
                          <span className="text-neutral-400">({fit.scoreText})</span>
                        )}
                      </div>
                    );
                  })()}
                </div>

                {/* ICP Rationale */}
                <div className="mt-5 p-4 rounded-lg bg-neutral-900/60 border border-neutral-800 text-xs">
                  <div className="font-mono text-[11px] uppercase tracking-wider text-neutral-400 mb-1.5 flex items-center gap-1.5 font-medium">
                    <Target className="w-3.5 h-3.5 text-neutral-300" />
                    ICP Fit Rationale:
                  </div>
                  <p className="text-neutral-300 leading-relaxed font-sans">
                    {briefResult.brief.icp_classification.rationale}
                  </p>

                  {(briefResult.brief.icp_classification.matched_criteria.length > 0 ||
                    briefResult.brief.icp_classification.mismatched_criteria.length > 0) && (
                    <div className="mt-3.5 pt-3.5 border-t border-neutral-800 grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                      {briefResult.brief.icp_classification.matched_criteria.length > 0 && (
                        <div>
                          <span className="text-emerald-400 font-medium flex items-center gap-1 mb-1">
                            <CheckCircle2 className="w-3.5 h-3.5" /> Matched Criteria
                          </span>
                          <ul className="space-y-1 text-neutral-400 font-sans">
                            {briefResult.brief.icp_classification.matched_criteria.map((c, i) => (
                              <li key={i} className="flex items-start gap-1.5">
                                <span className="text-emerald-400">✓</span> {c}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {briefResult.brief.icp_classification.mismatched_criteria.length > 0 && (
                        <div>
                          <span className="text-neutral-400 font-medium flex items-center gap-1 mb-1">
                            <AlertTriangle className="w-3.5 h-3.5 text-neutral-500" /> Discrepancies / Gaps
                          </span>
                          <ul className="space-y-1 text-neutral-400 font-sans">
                            {briefResult.brief.icp_classification.mismatched_criteria.map((c, i) => (
                              <li key={i} className="flex items-start gap-1.5">
                                <span className="text-neutral-500">•</span> {c}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* MODE 1: ACCOUNT BRIEF */}
              {activeTab === "brief" && (
                <div className="space-y-6">
                  {/* Executive Brief */}
                  <div className="bg-[#0A0A0A] rounded-xl border border-neutral-800 p-6 shadow-2xl">
                    <div className="flex items-center justify-between pb-3 mb-4 border-b border-neutral-800">
                      <span className="text-xs font-semibold text-neutral-300 uppercase tracking-wider flex items-center gap-2">
                        <FileText className="w-4 h-4 text-neutral-400" />
                        Executive Summary
                      </span>
                    </div>
                    <p className="text-sm text-neutral-200 leading-relaxed font-sans">
                      {briefResult.brief.executive_summary}
                    </p>
                  </div>

                  {/* Key Products / Offerings */}
                  <div className="bg-[#0A0A0A] rounded-xl border border-neutral-800 p-6 shadow-2xl">
                    <div className="flex items-center justify-between pb-3 mb-4 border-b border-neutral-800">
                      <span className="text-xs font-semibold text-neutral-300 uppercase tracking-wider flex items-center gap-2">
                        <Boxes className="w-4 h-4 text-neutral-400" />
                        Key Products & Services
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {briefResult.brief.key_products_or_services.map((product, i) => (
                        <span
                          key={i}
                          className="px-3 py-1 rounded-md bg-neutral-900 text-neutral-200 text-xs border border-neutral-800"
                        >
                          {product}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Pain Points */}
                  <div className="bg-[#0A0A0A] rounded-xl border border-neutral-800 p-6 shadow-2xl">
                    <div className="flex items-center justify-between pb-3 mb-4 border-b border-neutral-800">
                      <span className="text-xs font-semibold text-neutral-300 uppercase tracking-wider flex items-center gap-2">
                        <Flame className="w-4 h-4 text-neutral-400" />
                        Identified Pain Points
                      </span>
                    </div>
                    <ul className="space-y-2.5">
                      {briefResult.brief.likely_pain_points.map((pain, i) => (
                        <li
                          key={i}
                          className="p-3.5 rounded-lg bg-neutral-900/50 border border-neutral-800/80 text-xs text-neutral-300 leading-relaxed flex items-start gap-3"
                        >
                          <span className="text-neutral-500 font-mono text-[11px] mt-0.5">
                            0{i + 1}
                          </span>
                          <span>{pain}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Talk Tracks */}
                  <div className="bg-[#0A0A0A] rounded-xl border border-neutral-800 p-6 shadow-2xl">
                    <div className="flex items-center justify-between pb-3 mb-4 border-b border-neutral-800">
                      <span className="text-xs font-semibold text-neutral-300 uppercase tracking-wider flex items-center gap-2">
                        <MessageSquare className="w-4 h-4 text-neutral-400" />
                        Recommended Sales Talk Tracks
                      </span>
                    </div>
                    <div className="space-y-3.5">
                      {briefResult.brief.suggested_talk_tracks.map((track, i) => (
                        <div
                          key={i}
                          className="p-4 rounded-lg bg-neutral-900/50 border border-neutral-800 flex items-start justify-between gap-4 group hover:border-neutral-700 transition-colors"
                        >
                          <div className="space-y-1">
                            <span className="text-[10px] font-mono text-neutral-500 uppercase tracking-wider block">
                              Track #{i + 1}
                            </span>
                            <p className="text-xs text-neutral-200 leading-relaxed italic">
                              "{track}"
                            </p>
                          </div>
                          <button
                            type="button"
                            onClick={() => handleCopyText(track, `track-${i}`)}
                            className="p-2 rounded-md bg-neutral-800 hover:bg-neutral-700 text-neutral-300 border border-neutral-700 transition-all shrink-0 cursor-pointer btn-tactile"
                            title="Copy talk track"
                          >
                            {copiedKey === `track-${i}` ? (
                              <Check className="w-3.5 h-3.5 text-emerald-400" />
                            ) : (
                              <Copy className="w-3.5 h-3.5" />
                            )}
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* CTA Banner to Outreach Studio */}
                  <div className="p-5 rounded-xl bg-neutral-900 border border-neutral-800 flex flex-col sm:flex-row items-center justify-between gap-4">
                    <div>
                      <h4 className="font-semibold text-sm text-white">
                        Generate Personalized Cold Outreach
                      </h4>
                      <p className="text-xs text-neutral-400 mt-0.5">
                        Compile 4 cold email variants and a multi-step follow-up cadence for this account.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setActiveTab("outreach")}
                      className="px-4 py-2 rounded-lg bg-white hover:bg-neutral-200 text-black text-xs font-semibold flex items-center gap-1.5 cursor-pointer shrink-0 transition-all btn-tactile"
                    >
                      Open Outreach Studio
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              )}

              {/* MODE 2: OUTREACH STUDIO */}
              {activeTab === "outreach" && (
                <div className="space-y-6">
                  {/* Prospect Input Config */}
                  <div className="bg-[#0A0A0A] rounded-xl border border-neutral-800 p-6 shadow-2xl">
                    <div className="flex items-center justify-between pb-3 mb-4 border-b border-neutral-800">
                      <span className="text-xs font-semibold text-neutral-300 uppercase tracking-wider flex items-center gap-2">
                        <User className="w-4 h-4 text-neutral-400" />
                        Target Contact Information
                      </span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
                      <div>
                        <label className="block text-xs font-medium text-neutral-400 mb-1">
                          Contact Name
                        </label>
                        <input
                          type="text"
                          value={contactName}
                          onChange={(e) => setContactName(e.target.value)}
                          placeholder="e.g. Alex Chen"
                          className="w-full px-3 py-2 rounded-lg bg-neutral-900 border border-neutral-800 text-white text-xs focus:outline-none focus:border-neutral-600"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-neutral-400 mb-1">
                          Contact Role / Title
                        </label>
                        <input
                          type="text"
                          value={contactRole}
                          onChange={(e) => setContactRole(e.target.value)}
                          placeholder="e.g. VP of Sales"
                          className="w-full px-3 py-2 rounded-lg bg-neutral-900 border border-neutral-800 text-white text-xs focus:outline-none focus:border-neutral-600"
                        />
                      </div>
                    </div>

                    <div className="mb-4">
                      <label className="block text-xs font-medium text-neutral-400 mb-1">
                        Prospect Notes / Context
                      </label>
                      <textarea
                        rows={2}
                        value={contactNotes}
                        onChange={(e) => setContactNotes(e.target.value)}
                        placeholder="e.g. Expanding enterprise sales footprint..."
                        className="w-full px-3 py-2 rounded-lg bg-neutral-900 border border-neutral-800 text-white text-xs focus:outline-none focus:border-neutral-600"
                      />
                    </div>

                    <button
                      type="button"
                      onClick={handleGenerateOutreach}
                      disabled={isLoadingOutreach}
                      className="w-full py-2.5 rounded-lg bg-white hover:bg-neutral-200 text-black text-xs font-semibold tracking-wide transition-all flex items-center justify-center gap-2 cursor-pointer shadow-sm btn-tactile disabled:opacity-50"
                    >
                      {isLoadingOutreach ? (
                        <>
                          <RefreshCw className="w-3.5 h-3.5 animate-spin text-black" />
                          Compiling Outreach...
                        </>
                      ) : (
                        <>
                          <Send className="w-3.5 h-3.5 text-black" />
                          Generate Grounded Outreach Cadence
                        </>
                      )}
                    </button>
                  </div>

                  {/* Outreach Result Preview */}
                  {outreachResult && (
                    <div className="space-y-6">
                      {/* Email Composer */}
                      <div className="bg-[#0A0A0A] rounded-xl border border-neutral-800 p-6 shadow-2xl">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 mb-4 border-b border-neutral-800">
                          <span className="text-xs font-semibold text-neutral-300 uppercase tracking-wider flex items-center gap-2">
                            <MessageSquare className="w-4 h-4 text-neutral-400" />
                            Cold Email Variants ({outreachResult.outreach.email_variants.length} Tones)
                          </span>
                          <span className="text-xs font-mono text-neutral-400 bg-neutral-900 px-2.5 py-1 rounded-full border border-neutral-800">
                            To: {outreachResult.outreach.contact_name || "General Lead"}
                          </span>
                        </div>

                        {/* Tone Selector Pills */}
                        <div className="flex flex-wrap gap-2 mb-4">
                          {outreachResult.outreach.email_variants.map((v, i) => (
                            <button
                              key={i}
                              type="button"
                              onClick={() => setSelectedEmailToneIndex(i)}
                              className={`px-3 py-1.5 rounded-md text-xs font-medium uppercase tracking-wider transition-all cursor-pointer ${
                                selectedEmailToneIndex === i
                                  ? "bg-white text-black shadow-sm"
                                  : "bg-neutral-900 text-neutral-400 hover:text-white border border-neutral-800"
                              }`}
                            >
                              {v.tone_label}
                            </button>
                          ))}
                        </div>

                        {/* Email Body */}
                        {(() => {
                          const currentVariant =
                            outreachResult.outreach.email_variants[selectedEmailToneIndex] ||
                            outreachResult.outreach.email_variants[0];
                          if (!currentVariant) return null;

                          return (
                            <div className="p-5 rounded-lg bg-neutral-900/60 border border-neutral-800 space-y-4">
                              <div className="flex items-start justify-between gap-4 pb-3 border-b border-neutral-800">
                                <div>
                                  <span className="text-[10px] font-mono text-neutral-500 uppercase tracking-wider block">
                                    Subject
                                  </span>
                                  <span className="text-xs font-semibold text-white">
                                    {currentVariant.subject}
                                  </span>
                                </div>
                                <button
                                  type="button"
                                  onClick={() =>
                                    handleCopyText(
                                      `Subject: ${currentVariant.subject}\n\n${currentVariant.body}`,
                                      `variant-${selectedEmailToneIndex}`
                                    )
                                  }
                                  className="p-2 rounded-md bg-neutral-800 hover:bg-neutral-700 text-neutral-300 border border-neutral-700 transition-all shrink-0 cursor-pointer btn-tactile"
                                  title="Copy email"
                                >
                                  {copiedKey === `variant-${selectedEmailToneIndex}` ? (
                                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                                  ) : (
                                    <Copy className="w-3.5 h-3.5" />
                                  )}
                                </button>
                              </div>

                              <div className="text-xs text-neutral-200 leading-relaxed whitespace-pre-line font-sans">
                                {currentVariant.body}
                              </div>
                            </div>
                          );
                        })()}
                      </div>

                      {/* Follow-up Sequence */}
                      <div className="bg-[#0A0A0A] rounded-xl border border-neutral-800 p-6 shadow-2xl">
                        <div className="flex items-center justify-between pb-3 mb-4 border-b border-neutral-800">
                          <span className="text-xs font-semibold text-neutral-300 uppercase tracking-wider flex items-center gap-2">
                            <Compass className="w-4 h-4 text-neutral-400" />
                            Multi-Touch Cadence ({outreachResult.outreach.follow_up_sequence.length} Follow-ups)
                          </span>
                        </div>

                        <div className="space-y-3.5">
                          {outreachResult.outreach.follow_up_sequence.map((fu, idx) => (
                            <div
                              key={idx}
                              className="p-4 rounded-lg bg-neutral-900/50 border border-neutral-800 space-y-2.5"
                            >
                              <div className="flex items-center justify-between text-xs">
                                <span className="font-semibold text-white flex items-center gap-2">
                                  <span className="w-5 h-5 rounded-full bg-neutral-800 text-neutral-300 text-[10px] flex items-center justify-center font-bold">
                                    {fu.sequence_position}
                                  </span>
                                  Touch #{fu.sequence_position}
                                </span>
                                <span className="px-2.5 py-0.5 rounded-full bg-neutral-900 text-neutral-400 text-[10px] font-mono border border-neutral-800">
                                  Send after {fu.send_after_days} days
                                </span>
                              </div>

                              <p className="text-xs font-medium text-neutral-300">
                                {fu.subject}
                              </p>
                              <p className="text-xs text-neutral-400 leading-relaxed whitespace-pre-line">
                                {fu.body}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Personalization Signals */}
                      <div className="bg-[#0A0A0A] rounded-xl border border-neutral-800 p-6 shadow-2xl">
                        <div className="flex items-center justify-between pb-3 mb-4 border-b border-neutral-800">
                          <span className="text-xs font-semibold text-neutral-300 uppercase tracking-wider flex items-center gap-2">
                            <Sparkles className="w-4 h-4 text-neutral-400" />
                            Applied Personalization Triggers
                          </span>
                        </div>
                        <ul className="space-y-2 text-xs text-neutral-300 font-mono">
                          {outreachResult.outreach.personalization_notes.map((note, i) => (
                            <li key={i} className="flex items-start gap-2">
                              <span className="text-neutral-500">▸</span>
                              <span>{note}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Right 40%: Grounding & Fact-Check Inspector */}
            <div className="lg:col-span-5 space-y-6">
              <div className="bg-[#0A0A0A] rounded-xl border border-neutral-800 p-6 shadow-2xl sticky top-20">
                <div className="flex items-center justify-between pb-4 border-b border-neutral-800">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-emerald-400" />
                    <span className="text-xs font-semibold text-white uppercase tracking-wider">
                      Grounding Inspector
                    </span>
                  </div>
                  <span className="text-xs font-mono text-neutral-400 bg-neutral-900 px-2.5 py-1 rounded-full border border-neutral-800">
                    {currentFactChecks.length} Claims Audited
                  </span>
                </div>

                {/* Scorecard */}
                <div className="mt-4 grid grid-cols-3 gap-2 text-center font-mono">
                  <div className="p-3 rounded-lg bg-neutral-900/60 border border-neutral-800">
                    <div className="text-base font-bold text-emerald-400">
                      {directlyCount}
                    </div>
                    <div className="text-[10px] text-neutral-500 uppercase mt-0.5">
                      Direct Quotes
                    </div>
                  </div>
                  <div className="p-3 rounded-lg bg-neutral-900/60 border border-neutral-800">
                    <div className="text-base font-bold text-neutral-200">
                      {inferenceCount}
                    </div>
                    <div className="text-[10px] text-neutral-500 uppercase mt-0.5">
                      Inferences
                    </div>
                  </div>
                  <div className="p-3 rounded-lg bg-neutral-900/60 border border-neutral-800">
                    <div
                      className={`text-base font-bold ${
                        flaggedCount > 0 ? "text-rose-400" : "text-neutral-500"
                      }`}
                    >
                      {flaggedCount}
                    </div>
                    <div className="text-[10px] text-neutral-500 uppercase mt-0.5">
                      Flagged
                    </div>
                  </div>
                </div>

                {/* Flagged Alert */}
                {currentFlaggedClaims.length > 0 && (
                  <div className="mt-4 p-3.5 rounded-lg bg-rose-950/40 border border-rose-800/60 text-xs text-rose-300 font-mono">
                    <div className="font-semibold flex items-center gap-1.5 mb-1 text-rose-400">
                      <AlertTriangle className="w-3.5 h-3.5" /> Flagged Unsupported Claims:
                    </div>
                    <ul className="list-disc list-inside space-y-1 text-[11px] text-rose-300/80">
                      {currentFlaggedClaims.map((claim, idx) => (
                        <li key={idx}>{claim}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Claim List */}
                <div className="mt-5">
                  <div className="text-[10px] font-mono uppercase tracking-wider text-neutral-500 mb-2.5 font-medium flex items-center justify-between">
                    <span>Audit Log</span>
                    <span>Status</span>
                  </div>
                  <div className="max-h-64 overflow-y-auto space-y-2 pr-1">
                    {currentFactChecks.map((fc, i) => {
                      const isSelected = selectedClaim?.claim === fc.claim;
                      return (
                        <button
                          key={i}
                          type="button"
                          onClick={() => setSelectedClaim(fc)}
                          className={`w-full text-left p-3 rounded-lg border transition-all text-xs cursor-pointer ${
                            isSelected
                              ? "bg-neutral-900 border-neutral-600 shadow-sm"
                              : "bg-neutral-950/60 border-neutral-800/80 hover:border-neutral-700"
                          }`}
                        >
                          <div className="flex items-center justify-between gap-2 mb-1">
                            <span className="font-mono text-[10px] text-neutral-500">
                              Claim #{i + 1}
                            </span>
                            {getStatusBadge(fc.status)}
                          </div>
                          <p className="text-neutral-300 text-xs line-clamp-2 font-sans">
                            "{fc.claim}"
                          </p>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Selected Claim Citation Box */}
                {selectedClaim && (
                  <div className="mt-5 p-4 rounded-lg bg-neutral-900/80 border border-neutral-800 text-xs space-y-2.5">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[10px] text-neutral-400 uppercase tracking-wider">
                        Source Evidence
                      </span>
                      {getStatusBadge(selectedClaim.status)}
                    </div>

                    <p className="text-white font-medium text-xs leading-snug">
                      "{selectedClaim.claim}"
                    </p>

                    <div className="p-3 rounded-md bg-black border border-neutral-800 text-neutral-300 font-mono text-[11px] leading-relaxed">
                      <span className="text-emerald-400 font-bold block mb-1 text-[10px]">
                        PRIMARY SOURCE CITATION:
                      </span>
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
