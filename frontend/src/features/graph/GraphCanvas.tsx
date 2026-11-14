import cytoscape from "cytoscape";
import { useEffect, useRef } from "react";

import type { Core, EventObject } from "cytoscape";
import type { GraphResponse, GraphSelection } from "./types";

const INK = "#121412";
const ACCENT = "#1f4e79";

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
      // Node types differ by shape only; the legend in styles.css mirrors these shapes.
      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            width: 34,
            height: 34,
            "font-size": 11,
            "font-family": "Helvetica Neue, Helvetica, Arial, sans-serif",
            "text-valign": "bottom",
            "text-margin-y": 6,
            "text-wrap": "wrap",
            "text-max-width": "130px",
            "text-background-color": "#ffffff",
            "text-background-opacity": 0.85,
            color: INK,
            "background-color": INK,
          },
        },
        { selector: "node[type='gene']", style: { shape: "ellipse" } },
        { selector: "node[type='protein']", style: { shape: "rectangle" } },
        { selector: "node[type='disease']", style: { shape: "diamond" } },
        { selector: "node[type='variant']", style: { shape: "triangle" } },
        { selector: "node[type='dataset']", style: { shape: "octagon" } },
        { selector: "node[type='publication']", style: { shape: "rhomboid" } },
        { selector: "node[type='pathway']", style: { shape: "hexagon" } },
        { selector: "node[type='biological_process']", style: { shape: "pentagon" } },
        { selector: "node[type='molecular_function']", style: { shape: "vee" } },
        { selector: "node[type='cellular_component']", style: { shape: "star" } },
        { selector: "node.root", style: { "background-color": ACCENT, width: 44, height: 44 } },
        {
          selector: "edge",
          style: {
            label: "data(label)",
            "font-size": 9,
            color: "#4b4f4b",
            "text-rotation": "autorotate",
            "text-background-color": "#ffffff",
            "text-background-opacity": 0.9,
            "curve-style": "bezier",
            "line-color": "#8b8f8b",
            width: 1,
            "target-arrow-color": "#8b8f8b",
          },
        },
        { selector: "edge.directed", style: { "target-arrow-shape": "triangle" } },
        {
          selector: ":selected",
          style: { "overlay-color": ACCENT, "overlay-opacity": 0.25, "overlay-padding": 6 },
        },
        { selector: "edge:selected", style: { "line-color": ACCENT, width: 2 } },
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
    // A fitted graph of only a few nodes would otherwise fill the canvas at maximum zoom.
    if (!laidOut.current && cy.zoom() > 1.25) {
      cy.zoom(1.25);
      cy.center();
    }
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
