import type { DashboardReportSummary, DashboardReportsResponse } from "@/types/api";

export function flattenReports(data: DashboardReportsResponse): DashboardReportSummary[] {
  const merged = [
    ...(data.featured_venture_report ? [data.featured_venture_report] : []),
    ...data.venture_reports,
    ...data.top_opportunity_reports,
    ...data.pipeline_reports,
  ];
  return merged.filter(
    (report, index, arr) => arr.findIndex((r) => r.id === report.id) === index,
  );
}

export function formatReportType(type: string): string {
  return type.replace(/_/g, " ");
}
