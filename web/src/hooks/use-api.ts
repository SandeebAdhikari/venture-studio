"use client";

import useSWR, { type SWRConfiguration } from "swr";
import { clientApiFetch } from "@/lib/api/client";

const fetcher = <T,>(path: string) => clientApiFetch<T>(path);

export function useApi<T>(path: string | null, options?: SWRConfiguration<T>) {
  return useSWR<T>(path, fetcher, {
    revalidateOnFocus: true,
    ...options,
  });
}

export function usePollingApi<T>(
  path: string | null,
  intervalMs: number,
  options?: Omit<SWRConfiguration<T>, "refreshInterval">,
) {
  return useApi<T>(path, {
    refreshInterval: intervalMs,
    ...options,
  });
}
