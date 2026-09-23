import { useCallback, useEffect, useState } from "react";

import { getRelationships } from "../services/api";
import type { EntityRelationship, Page, RelatedEntityType } from "../types/entities";

export function useRelationships(entityType: RelatedEntityType, entityId: number, page: number) {
  const [data, setData] = useState<Page<EntityRelationship> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshToken, setRefreshToken] = useState(0);
  const retry = useCallback(() => setRefreshToken((value) => value + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    getRelationships(entityType, entityId, page, controller.signal)
      .then(setData)
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        setError(reason instanceof Error ? reason.message : "An unknown error occurred.");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [entityType, entityId, page, refreshToken]);

  return { data, error, loading, retry };
}
