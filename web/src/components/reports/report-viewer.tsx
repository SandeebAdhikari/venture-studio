"use client";

import ReactMarkdown from "react-markdown";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

interface ReportViewerProps {
  title: string;
  markdown: string | null | undefined;
  isLoading?: boolean;
}

export function ReportViewer({ title, markdown, isLoading }: ReportViewerProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
        </CardHeader>
        <CardContent className="space-y-2">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
        </CardContent>
      </Card>
    );
  }

  if (!markdown) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <article className="prose prose-sm max-w-none dark:prose-invert prose-headings:scroll-mt-20 prose-p:text-muted-foreground">
          <ReactMarkdown>{markdown}</ReactMarkdown>
        </article>
      </CardContent>
    </Card>
  );
}
