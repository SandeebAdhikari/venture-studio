import * as React from "react";
import { cn } from "@/lib/utils";

const variants: Record<string, string> = {
  default: "bg-secondary text-secondary-foreground",
  success: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
  warning: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  danger: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
  info: "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300",
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
