import { useCallback, useEffect, useRef, useState } from "react";

import { getEntity } from "../../services/api";
import { collapseBranch, graphParams, mergeGraph } from "./state";
import type { GraphNode, GraphResponse } from "./types";

export function useGraphExplorer(resource: string) {
  const [graph, setGraph] = useState<GraphResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expansionError, setExpansionError] = useState<string | null>(null);
  const [expanding, setExpanding] = useState<string | null>(null);
  const [refresh, setRefresh] = useState(0);
  const activeExpansion = useRef<AbortController | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    setGraph(null);
    setExpansionError(null);
    getEntity<GraphResponse>(resource, controller.signal)
      .then((result) => {
        if (!controller.signal.aborted) setGraph(result);
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted)
          setError(reason instanceof Error ? reason.message : "Unable to load graph.");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => {
      controller.abort();
      activeExpansion.current?.abort();
      activeExpansion.current = null;
    };
  }, [resource, refresh]);

  async function expand(node: GraphNode) {
    if (!graph || activeExpansion.current) return;
    const controller = new AbortController();
    activeExpansion.current = controller;
    setExpanding(node.id);
    setExpansionError(null);
    try {
      const addition = await getEntity<GraphResponse>(
        `graph/${node.entity_type}/${node.entity_id}?${graphParams(graph.limits, 1)}`,
        controller.signal,
      );
      if (!controller.signal.aborted)
        setGraph((current) => (current ? mergeGraph(current, addition) : current));
    } catch (reason) {
      if (!controller.signal.aborted)
        setExpansionError(reason instanceof Error ? reason.message : "Unable to expand this node.");
    } finally {
      if (activeExpansion.current === controller) activeExpansion.current = null;
      if (!controller.signal.aborted) setExpanding(null);
    }
  }

  function collapse(id: string) {
    if (activeExpansion.current) return;
    setGraph((current) => (current ? collapseBranch(current, id) : null));
    setExpansionError(null);
  }
  const retry = useCallback(() => setRefresh((value) => value + 1), []);
  return { graph, loading, error, retry, expand, collapse, expanding, expansionError };
}
