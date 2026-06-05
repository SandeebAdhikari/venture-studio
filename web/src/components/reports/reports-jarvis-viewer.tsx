"use client";

import ReactMarkdown from "react-markdown";
import { motion, useReducedMotion } from "framer-motion";
import { Skeleton } from "@/components/ui/skeleton";

interface ReportsJarvisViewerProps {
  title: string;
  markdown: string | null | undefined;
  isLoading?: boolean;
}

export function ReportsJarvisViewer({ title, markdown, isLoading }: ReportsJarvisViewerProps) {
  const reduceMotion = useReducedMotion();

  if (isLoading) {
    return (
      <div className="jarvis-stage-lens rounded-2xl border border-[hsl(187_40%_32%/0.45)] p-6">
        <Skeleton className="mb-4 h-6 w-48" />
        <Skeleton className="mb-2 h-4 w-full" />
        <Skeleton className="mb-2 h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
      </div>
    );
  }

  if (!markdown) {
    return (
      <div className="jarvis-panel flex min-h-[16rem] flex-col items-center justify-center rounded-2xl border border-dashed border-[hsl(187_35%_28%/0.45)] p-8 text-center">
        <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[hsl(187_75%_58%)]">
          Awaiting selection
        </p>
        <p className="mt-2 text-sm text-muted-foreground">
          Choose a report from the library to render markdown.
        </p>
      </div>
    );
  }

  return (
    <motion.article
      className="jarvis-stage-lens jarvis-report-viewer max-h-[36rem] overflow-y-auto rounded-2xl border border-[hsl(187_40%_32%/0.45)] bg-gradient-to-br from-[hsl(187_26%_11%/0.5)] to-transparent p-6 sm:p-8"
      initial={reduceMotion ? false : { opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[hsl(187_75%_58%)]">
        Rendered output
      </p>
      <h3 className="mt-1 text-lg font-semibold text-foreground">{title}</h3>
      <div className="prose prose-sm mt-6 max-w-none dark:prose-invert prose-headings:text-foreground prose-p:text-muted-foreground">
        <ReactMarkdown>{markdown}</ReactMarkdown>
      </div>
    </motion.article>
  );
}
