import { useCallback, useEffect, useState } from "react";

import { searchEntities } from "../services/api";
import type { SearchEntityType, SearchResponse } from "../types/entities";

const PAGE_SIZE = 12;

export function useSearchResults(query: string, page: number, entityType: SearchEntityType | null) {
  const [data, setData] = useState<SearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [refreshToken, setRefreshToken] = useState(0);

  const retry = useCallback(() => setRefreshToken((value) => value + 1), []);

  useEffect(() => {
    if (!query) {
      setData(null);
      setError(null);
      setLoading(false);
      return;
    }
    const controller = new AbortController();
    setLoading(true);
    setError(null);

    searchEntities(query, page, PAGE_SIZE, entityType ? [entityType] : [], controller.signal)
      .then(setData)
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        setError(reason instanceof Error ? reason.message : "An unknown error occurred.");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [entityType, page, query, refreshToken]);

  return { data, error, loading, retry };
}
