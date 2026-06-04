import * as React from "react";
import { cn } from "@/lib/utils";

const variants: Record<string, string> = {
  default: "border border-border bg-muted text-foreground",
  success: "border border-foreground/25 bg-foreground text-background",
  warning: "border border-border bg-secondary text-secondary-foreground",
  danger: "border border-border bg-muted text-muted-foreground",
  info: "border border-border bg-accent text-accent-foreground",
};

export function Badge({
  className,
  variant = "default",
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { variant?: keyof typeof variants }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        variants[variant],
        className,
      )}
      {...props}
    />
  );
}

export function statusVariant(status: string): keyof typeof variants {
  const normalized = status.toLowerCase();
  if (["completed", "approved", "published", "classified", "success"].includes(normalized)) {
    return "success";
  }
  if (["running", "pending", "reviewing", "draft", "research_requested"].includes(normalized)) {
    return "warning";
  }
  if (["failed", "rejected", "cancelled", "error"].includes(normalized)) {
    return "danger";
  }
  return "default";
}
