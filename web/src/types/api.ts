/** TypeScript mirrors of backend API schemas — display only, no business logic. */

export type ReviewStatus = "new" | "reviewing" | "approved" | "rejected" | "archived";
export type ReportStatus = "draft" | "published" | "archived";
export type ReportType =
  | "opportunity_brief"
  | "top_opportunities"
  | "venture_recommendation"
  | "daily_digest"
  | "pipeline_summary"
  | "custom";
export type ApprovalStatus = "pending" | "approved" | "rejected" | "research_requested";
export type ApprovalSubjectType = "executive_ranking" | "venture_report";
export type PipelineRunStatus = "pending" | "running" | "completed" | "failed" | "cancelled";
export type PipelineStageStatus = "pending" | "running" | "completed" | "failed" | "skipped";

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface DashboardReportSummary {
  id: string;
  report_type: ReportType;
  title: string;
  summary: string | null;
  status: ReportStatus;
  opportunity_id: string | null;
  created_at: string;
  report_metadata: Record<string, unknown>;
}

export interface DashboardPipelineRunSummary {
  id: string;
  trigger: string;
  status: PipelineRunStatus;
  started_at: string | null;
  finished_at: string | null;
  duration_ms: number | null;
  stages_completed: number;
  stages_failed: number;
  stages_skipped: number;
  error_summary: string | null;
}

export interface DashboardPipelineStageSummary {
  stage: string;
  sequence: number;
  status: PipelineStageStatus;
  duration_ms: number | null;
  items_in: number;
  items_out: number;
  items_failed: number;
  records_processed: number;
  error_detail: string | null;
}

export interface DashboardPipelineDetail {
  run: DashboardPipelineRunSummary;
  stage_runs: DashboardPipelineStageSummary[];
}

export interface DashboardAgentStatus {
  agent: string;
  display_name: string;
  current_completed: number;
  current_failed: number;
  current_skipped: number;
  current_total: number;
}

export interface DashboardOpportunityItem {
  rank: number | null;
  opportunity_id: string;
  title: string;
  review_status: ReviewStatus;
  confidence_score: number;
  final_opportunity_score?: number | null;
  pain_score?: number | null;
  market_score?: number | null;
  revenue_score?: number | null;
  competition_score?: number | null;
  growth_score?: number | null;
  founder_fit_score?: number | null;
  agent_coverage_count?: number | null;
  score?: number | null;
  is_top_opportunity: boolean;
}

export interface DashboardSummaryResponse {
  generated_at: string;
  pipeline: {
    running: DashboardPipelineRunSummary | null;
    latest: DashboardPipelineRunSummary | null;
  };
  collection: Record<string, number>;
  classification: Record<string, number>;
  research: {
    opportunities_total: number;
    agents: DashboardAgentStatus[];
    average_agent_coverage: number | null;
  };
  opportunities: {
    total: number;
    by_review_status: Record<string, number>;
  };
  ranking: {
    current_run_id: string | null;
    version: number | null;
    top_n: number | null;
    ranked_opportunity_count: number;
    generated_at: string | null;
  };
  reports: {
    latest_venture: DashboardReportSummary | null;
  };
  agents: DashboardAgentStatus[];
  background: {
    recent_jobs: Array<{
      job_id: string;
      job_name: string;
      status: string;
      finished_at: string | null;
    }>;
    scheduler_jobs: Array<{
      job_name: string;
      enabled: boolean;
      schedule_cron: string;
      last_run_status: string | null;
      failure_count: number;
    }>;
  };
}

export interface DashboardOpportunitiesResponse {
  source: "executive_ranking" | "opportunity_score";
  ranking_run_id: string | null;
  version: number | null;
  top_n: number;
  ranked_opportunity_count: number;
  total_opportunities: number;
  items: DashboardOpportunityItem[];
  executive_rankings: DashboardOpportunityItem[];
}

export interface DashboardPipelineResponse {
  running: DashboardPipelineRunSummary | null;
  runs: PaginatedResponse<DashboardPipelineRunSummary>;
  latest_detail: DashboardPipelineDetail | null;
  stage_order: string[];
}

export interface DashboardReportsResponse {
  featured_venture_report: DashboardReportSummary | null;
  venture_reports: DashboardReportSummary[];
  top_opportunity_reports: DashboardReportSummary[];
  pipeline_reports: DashboardReportSummary[];
  total_by_type: Record<string, number>;
}

export interface OpportunityRead {
  id: string;
  title: string;
  problem_statement: string;
  target_user: string;
  frequency_signal: string;
  existing_alternatives: string;
  gap: string;
  confidence_score: number;
  llm_model: string;
  review_status: ReviewStatus;
  reviewed_at: string | null;
  review_notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReportRead {
  id: string;
  report_type: ReportType;
  title: string;
  summary: string | null;
  content: Record<string, unknown>;
  status: ReportStatus;
  report_metadata: Record<string, unknown>;
  opportunity_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReportMarkdownRead {
  id: string;
  title: string;
  markdown: string;
}

export interface ApprovalDecisionRead {
  id: string;
  approval_request_id: string;
  decision_type: string;
  comment: string | null;
  actor: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ApprovalRequestRead {
  id: string;
  subject_type: ApprovalSubjectType;
  title: string;
  status: ApprovalStatus;
  executive_ranking_run_id: string | null;
  report_id: string | null;
  audit_trail: Array<Record<string, unknown>>;
  decisions: ApprovalDecisionRead[];
  created_at: string;
  updated_at: string;
}

export interface ApprovalActionResult {
  approval_request_id: string;
  status: ApprovalStatus;
  decision: ApprovalDecisionRead;
  finalized: boolean;
}

export interface BudgetAgentUsage {
  graph_name: string;
  display_name: string;
  calls_total: number;
  prompt_tokens_total: number;
  completion_tokens_total: number;
  estimated_cost_usd_total: number;
  actual_cost_usd_total: number;
}

export interface BudgetWarning {
  threshold_pct: number;
  triggered: boolean;
  current_utilization_pct: number;
}

export interface BudgetStatusResponse {
  usage_date: string;
  enabled: boolean;
  budget_usd: number;
  spent_usd: number;
  estimated_cost_usd_total: number;
  remaining_usd: number;
  utilization_pct: number;
  budget_exceeded: boolean;
  calls_total: number;
  prompt_tokens_total: number;
  completion_tokens_total: number;
  warning_thresholds_pct: number[];
  warnings: BudgetWarning[];
  by_agent: BudgetAgentUsage[];
}

export interface BudgetHistoryDay {
  usage_date: string;
  budget_usd: number;
  spent_usd: number;
  estimated_cost_usd_total: number;
  remaining_usd: number;
  utilization_pct: number;
  budget_exceeded: boolean;
  calls_total: number;
  prompt_tokens_total: number;
  completion_tokens_total: number;
}

export interface BudgetHistoryResponse {
  generated_at: string;
  days: number;
  items: BudgetHistoryDay[];
}

export interface PipelineRunRead {
  id: string;
  trigger: string;
  status: PipelineRunStatus;
  started_at: string | null;
  finished_at: string | null;
  duration_ms: number | null;
  stages_completed: number;
  stages_failed: number;
  stages_skipped: number;
  error_summary: string | null;
  created_at: string;
}

export interface PipelineRunDetail extends PipelineRunRead {
  audit_trail: Array<Record<string, unknown>>;
  stage_runs: DashboardPipelineStageSummary[];
}
