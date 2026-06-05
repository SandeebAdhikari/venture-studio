"use client";

import { useEffect, useMemo, useState } from "react";
import { usePollingApi } from "@/hooks/use-api";
import { agentKeyForStage, computePipelineLiveProgress } from "@/lib/pipeline/stage-sync";
import { buildQuery } from "@/lib/api/client";
import type { DashboardPipelineResponse } from "@/types/api";

const POLL_IDLE_MS = 10_000;
const POLL_LIVE_MS = 3_000;

export function usePipelineLive(enabled = true) {
  const [pollMs, setPollMs] = useState(POLL_IDLE_MS);
  const path = enabled
    ? `dashboard/pipeline${buildQuery({ limit: 1, offset: 0, include_stages: true })}`
    : null;

  const pipeline = usePollingApi<DashboardPipelineResponse>(path, pollMs);
  const isLive = !!pipeline.data?.running;

  useEffect(() => {
    setPollMs(isLive ? POLL_LIVE_MS : POLL_IDLE_MS);
  }, [isLive]);

  const progress = useMemo(() => {
    const stages = pipeline.data?.latest_detail?.stage_runs ?? [];
    const order = pipeline.data?.stage_order ?? [];
    return computePipelineLiveProgress(stages, order);
  }, [pipeline.data?.latest_detail?.stage_runs, pipeline.data?.stage_order]);

  const activeAgentKey = progress.runningStage
    ? agentKeyForStage(progress.runningStage.stage)
    : null;

  return {
    pipeline: pipeline.data,
    isLive,
    isLoading: pipeline.isLoading,
    error: pipeline.error,
    mutate: pipeline.mutate,
    isValidating: pipeline.isValidating,
    progress,
    activeAgentKey,
    runningRunId: pipeline.data?.running?.id ?? null,
  };
}
