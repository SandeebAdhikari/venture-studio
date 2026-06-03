import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge, statusVariant } from "@/components/ui/badge";
import type { DashboardAgentStatus } from "@/types/api";

export function AgentActivityGrid({ agents }: { agents: DashboardAgentStatus[] }) {
  if (agents.length === 0) {
    return <p className="text-sm text-muted-foreground">No agent activity data available.</p>;
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {agents.map((agent) => {
        const successRate =
          agent.current_total > 0
            ? Math.round((agent.current_completed / agent.current_total) * 100)
            : 0;
        return (
          <Card key={agent.agent}>
            <CardHeader className="pb-2">
              <div className="flex items-start justify-between gap-2">
                <CardTitle className="text-base">{agent.display_name}</CardTitle>
                <Badge variant={agent.current_failed > 0 ? "warning" : "success"}>
                  {agent.current_total} runs
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <Progress value={successRate} />
              <div className="grid grid-cols-3 gap-2 text-center text-xs">
                <div>
                  <p className="font-semibold text-emerald-600">{agent.current_completed}</p>
                  <p className="text-muted-foreground">Done</p>
                </div>
                <div>
                  <p className="font-semibold text-amber-600">{agent.current_skipped}</p>
                  <p className="text-muted-foreground">Skipped</p>
                </div>
                <div>
                  <p className="font-semibold text-red-600">{agent.current_failed}</p>
                  <p className="text-muted-foreground">Failed</p>
                </div>
              </div>
              <p className="text-xs text-muted-foreground">Success rate: {successRate}%</p>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

export function AgentCompactList({ agents }: { agents: DashboardAgentStatus[] }) {
  return (
    <div className="space-y-2">
      {agents.map((agent) => (
        <div
          key={agent.agent}
          className="flex items-center justify-between rounded-lg border border-border px-4 py-3 text-sm"
        >
          <span className="font-medium">{agent.display_name}</span>
          <div className="flex gap-2">
            <Badge variant={statusVariant("completed")}>{agent.current_completed}</Badge>
            {agent.current_failed > 0 && (
              <Badge variant={statusVariant("failed")}>{agent.current_failed}</Badge>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
