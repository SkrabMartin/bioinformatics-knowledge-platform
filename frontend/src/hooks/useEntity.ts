import { useCallback, useEffect, useState } from "react";

import { getEntity } from "../services/api";

export function useEntity<T>(resourcePath: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshToken, setRefreshToken] = useState(0);

  const retry = useCallback(() => setRefreshToken((value) => value + 1), []);

  useEffect(() => {
    if (!resourcePath) {
      setLoading(false);
      setError("The entity identifier is missing from the URL.");
      return;
    }
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    setData(null);

    getEntity<T>(resourcePath, controller.signal)
      .then(setData)
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        setError(reason instanceof Error ? reason.message : "An unknown error occurred.");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [resourcePath, refreshToken]);

  return { data, error, loading, retry };
}
