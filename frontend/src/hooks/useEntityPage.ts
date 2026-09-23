import { useCallback, useEffect, useState } from "react";

import { getPage } from "../services/api";
import type { Page } from "../types/entities";

const PAGE_SIZE = 10;

export function useEntityPage<T>(resource: string, page: number) {
  const [data, setData] = useState<Page<T> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshToken, setRefreshToken] = useState(0);

  const retry = useCallback(() => setRefreshToken((value) => value + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);

    getPage<T>(resource, page, PAGE_SIZE, controller.signal)
      .then(setData)
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        setError(reason instanceof Error ? reason.message : "An unknown error occurred.");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [resource, page, refreshToken]);

  return { data, error, loading, retry };
}
