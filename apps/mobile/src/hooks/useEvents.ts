import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { fetchWithAuth } from "@/api/client";
import type { EventListResponse } from "@/types/api";

const STALE_TIME = 60_000;
const DEBOUNCE_MS = 300;

export function useEvents(query: string): UseQueryResult<EventListResponse> {
  const [debouncedQuery, setDebouncedQuery] = useState(query);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedQuery(query), DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [query]);

  const q = debouncedQuery.trim();
  const url = q.length > 0 ? `/api/events?q=${encodeURIComponent(q)}` : "/api/events";

  return useQuery<EventListResponse>({
    queryKey: ["events", q],
    queryFn: () => fetchWithAuth<EventListResponse>(url),
    staleTime: STALE_TIME,
  });
}
