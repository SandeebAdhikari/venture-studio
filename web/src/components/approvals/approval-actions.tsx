"use client";

import { useState } from "react";
import { useSWRConfig } from "swr";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/input";
import { clientApiFetch } from "@/lib/api/client";
import type { ApprovalActionResult, ApprovalRequestRead } from "@/types/api";

interface ApprovalActionsProps {
  approval: ApprovalRequestRead;
  onComplete?: () => void;
}

export function ApprovalActions({ approval, onComplete }: ApprovalActionsProps) {
  const { mutate } = useSWRConfig();
  const [comment, setComment] = useState("");
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const isPending = approval.status === "pending";

  async function act(action: "approve" | "reject" | "research") {
    setLoading(action);
    setError(null);
    try {
      const body = comment.trim() ? JSON.stringify({ comment: comment.trim() }) : undefined;
      await clientApiFetch<ApprovalActionResult>(
        `approvals/${approval.id}/${action}`,
        { method: "POST", body },
      );
      setComment("");
      await mutate((key) => typeof key === "string" && key.startsWith("approvals"));
      onComplete?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setLoading(null);
    }
  }

  if (!isPending) {
    return null;
  }

  return (
    <div className="space-y-3 rounded-lg border border-border bg-muted/20 p-4">
      <Textarea
        placeholder="Optional comment (required for research request)"
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        rows={2}
      />
      {error && <p className="text-sm text-destructive">{error}</p>}
      <div className="flex flex-wrap gap-2">
        <Button size="sm" disabled={!!loading} onClick={() => act("approve")}>
          {loading === "approve" ? "Approving…" : "Approve"}
        </Button>
        <Button size="sm" variant="destructive" disabled={!!loading} onClick={() => act("reject")}>
          {loading === "reject" ? "Rejecting…" : "Reject"}
        </Button>
        <Button size="sm" variant="outline" disabled={!!loading} onClick={() => act("research")}>
          {loading === "research" ? "Submitting…" : "Request research"}
        </Button>
      </div>
    </div>
  );
}
