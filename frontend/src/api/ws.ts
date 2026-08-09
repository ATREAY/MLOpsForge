import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { getToken, getWsBaseUrl } from "@/api/client";
import type { Job } from "@/api/types";

const RECONNECT_DELAY_MS = 3000;

/**
 * Subscribes to /api/v1/ws/jobs and patches live status updates straight into
 * the shared ["jobs"] React Query cache — every page reading useJobs() sees
 * updates immediately, no polling required. Mounted once at the Layout level
 * (see components/Layout.tsx) so it's active for the whole app while logged in.
 */
export function useJobsLiveUpdates() {
  const queryClient = useQueryClient();

  useEffect(() => {
    const token = getToken();
    if (!token) return;

    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let cancelled = false;

    function connect() {
      socket = new WebSocket(`${getWsBaseUrl()}/ws/jobs?token=${token}`);

      socket.onmessage = (event) => {
        const job = JSON.parse(event.data) as Job;
        queryClient.setQueryData<Job[]>(["jobs"], (prev) => {
          if (!prev) return prev;
          const index = prev.findIndex((j) => j.id === job.id);
          if (index === -1) return [job, ...prev];
          const next = [...prev];
          next[index] = job;
          return next;
        });
      };

      socket.onclose = () => {
        if (!cancelled) reconnectTimer = setTimeout(connect, RECONNECT_DELAY_MS);
      };
    }

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, [queryClient]);
}
