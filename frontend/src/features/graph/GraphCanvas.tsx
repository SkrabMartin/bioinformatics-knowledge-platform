import cytoscape from "cytoscape";
import { useEffect, useRef } from "react";

import type { Core, EventObject } from "cytoscape";
import type { GraphResponse, GraphSelection } from "./types";

export function GraphCanvas({
  graph,
  selected,
  onSelect,
}: {
  graph: GraphResponse;
  selected: GraphSelection | null;
  onSelect: (selection: GraphSelection) => void;
}) {
  const container = useRef<HTMLDivElement>(null);
  const instance = useRef<Core | null>(null);
  const handler = useRef(onSelect);
  const laidOut = useRef(false);
  useEffect(() => {
    handler.current = onSelect;
  }, [onSelect]);
  useEffect(() => {
    if (!container.current) return;
    const cy = cytoscape({
      container: container.current,
      elements: [],
      minZoom: 0.15,
      maxZoom: 3,
      wheelSensitivity: 0.25,
      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            width: 48,
            height: 48,
            "font-size": 11,
            "text-valign": "bottom",
            "text-margin-y": 8,
            "text-wrap": "wrap",
            "text-max-width": "130px",
            color: "#193a34",
            "border-width": 2,
            "border-color": "#fff",
          },
        },
        {
          selector: "node[type='gene']",
          style: { "background-color": "#24766a", shape: "ellipse" },
        },
        {
          selector: "node[type='protein']",
          style: { "background-color": "#467ab0", shape: "round-rectangle" },
        },
        {
          selector: "node[type='disease']",
          style: { "background-color": "#a25676", shape: "diamond" },
        },
        {
          selector: "node[type='variant']",
          style: { "background-color": "#bb7b32", shape: "triangle" },
        },
        {
          selector: "node[type='publication']",
          style: { "background-color": "#7660a5", shape: "rectangle" },
        },
        { selector: "node.root", style: { "border-color": "#163f36", "border-width": 5 } },
        {
          selector: "node[type='pathway']",
          style: { "background-color": "#598038", shape: "hexagon" },
        },
        {
          selector: "node[type='biological_process']",
          style: { "background-color": "#278a91", shape: "pentagon" },
        },
        {
          selector: "node[type='molecular_function']",
          style: { "background-color": "#9a6c36", shape: "vee" },
        },
        {
          selector: "edge",
          style: {
            label: "data(label)",
            "font-size": 9,
            "text-rotation": "autorotate",
            "text-background-color": "#fff",
            "text-background-opacity": 0.9,
            "curve-style": "bezier",
            "line-color": "#a4b6b1",
            width: 2,
            "target-arrow-color": "#77958c",
          },
        },
        { selector: "edge.directed", style: { "target-arrow-shape": "triangle" } },
        {
          selector: ":selected",
          style: { "overlay-color": "#d49627", "overlay-opacity": 0.25, "overlay-padding": 6 },
        },
      ],
    });
    instance.current = cy;
    const nodeTap = (event: EventObject) =>
      handler.current({ kind: "node", id: event.target.id() as string });
    const edgeTap = (event: EventObject) =>
      handler.current({ kind: "edge", id: event.target.id() as string });
    cy.on("tap", "node", nodeTap);
    cy.on("tap", "edge", edgeTap);
    const observer = new ResizeObserver(() => cy.resize());
    observer.observe(container.current);
    return () => {
      observer.disconnect();
      cy.destroy();
      instance.current = null;
      laidOut.current = false;
    };
  }, []);

  useEffect(() => {
    const cy = instance.current;
    if (!cy) return;
    const ids = new Set([
      ...graph.nodes.map((node) => node.id),
      ...graph.edges.map((edge) => edge.id),
    ]);
    cy.batch(() => {
      cy.elements()
        .filter((element) => !ids.has(element.id()))
        .remove();
      for (const node of graph.nodes) {
        const data = {
          id: node.id,
          label: node.label.length > 70 ? `${node.label.slice(0, 67)}…` : node.label,
          type: node.entity_type,
        };
        const existing = cy.getElementById(node.id);
        if (existing.length) existing.data(data);
        else cy.add({ group: "nodes", data });
        cy.getElementById(node.id).toggleClass("root", node.id === graph.root_id);
      }
      for (const edge of graph.edges) {
        const data = {
          id: edge.id,
          source: edge.source_node,
          target: edge.target_node,
          label: edge.assertion.predicate.replaceAll("_", " "),
        };
        const existing = cy.getElementById(edge.id);
        if (existing.length) existing.data(data);
        else cy.add({ group: "edges", data });
        cy.getElementById(edge.id).toggleClass("directed", edge.directed);
      }
    });
    cy.layout({
      name: "breadthfirst",
      directed: false,
      roots: [graph.root_id],
      fit: !laidOut.current,
      padding: 45,
      spacingFactor: 1.4,
      animate: false,
    }).run();
    laidOut.current = true;
  }, [graph]);

  useEffect(() => {
    const cy = instance.current;
    if (!cy) return;
    cy.elements().unselect();
    if (selected) cy.getElementById(selected.id).select();
  }, [selected, graph]);

  return (
    <div className="graph-canvas-shell">
      <div className="graph-camera" aria-label="Graph view controls">
        <button
          type="button"
          onClick={() => {
            const cy = instance.current;
            if (cy)
              cy.zoom({
                level: Math.min(3, cy.zoom() * 1.3),
                renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 },
              });
          }}
        >
          Zoom in
        </button>
        <button
          type="button"
          onClick={() => {
            const cy = instance.current;
            if (cy)
              cy.zoom({
                level: Math.max(0.15, cy.zoom() / 1.3),
                renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 },
              });
          }}
        >
          Zoom out
        </button>
        <button type="button" onClick={() => instance.current?.fit(undefined, 45)}>
          Fit graph
        </button>
      </div>
      <div
        ref={container}
        className="graph-canvas"
        role="img"
        aria-label="Interactive biological relationship graph. Drag to pan, scroll to zoom. Keyboard selection is available in the inspection panel."
      />
    </div>
  );
}
