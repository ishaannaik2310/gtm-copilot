export type ICPFitLabel = "strong_fit" | "possible_fit" | "poor_fit" | "unknown";

export interface ICPClassification {
  fit_score: number | null;
  fit_label: ICPFitLabel;
  rationale: string;
  matched_criteria: string[];
  mismatched_criteria: string[];
}

export interface AccountBrief {
  company_name: string;
  industry: string;
  icp_classification: ICPClassification;
  executive_summary: string;
  key_products_or_services: string[];
  likely_pain_points: string[];
  suggested_talk_tracks: string[];
  objection_handling_notes: string[];
  source_urls: string[];
}

export type FactCheckStatus = "directly_supported" | "reasonable_inference" | "unsupported";

export interface FactCheckResult {
  claim: string;
  status: FactCheckStatus;
  supported: boolean;
  supporting_evidence: string | null;
  confidence: number;
}

export interface FactCheckedBrief {
  brief: AccountBrief;
  fact_checks: FactCheckResult[];
  overall_faithfulness_score: number;
  flagged_claims: string[];
}
