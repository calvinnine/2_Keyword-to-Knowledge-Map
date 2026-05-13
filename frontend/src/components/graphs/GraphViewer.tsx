"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Graph from "graphology";
import forceAtlas2 from "graphology-layout-forceatlas2";
import Sigma from "sigma";
import { graphsApi } from "@/lib/api/client";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { formatNumber } from "@/lib/utils";
import type { GraphResultDetail, GraphType } from "@/lib/types/api";

const graphTypeLabel: Record<GraphType, string> = {
  paper: "논문 네트워크",
  author: "저자 네트워크",
  keyword: "키워드 네트워크",
};

// Categorical palette for clusters (Claude-flavored warm tones)
const CLUSTER_COLORS = [
  "#C8643E",
  "#3D6796",
  "#3F7A4E",
  "#B88A2A",
  "#7B4A8B",
  "#B54241",
  "#516D8E",
  "#7A6A3C",
  "#5D8175",
  "#A05A2C",
];

function colorForCluster(cid: number | null | undefined): string {
  if (cid === null || cid === undefined) return "#94928d";
  return CLUSTER_COLORS[cid % CLUSTER_COLORS.length];
}

function nodeLabel(
  node: GraphResultDetail["nodes"][number],
  graphType: GraphType
): string {
  const props = node.properties ?? {};
  if (graphType === "paper") {
    const title = (props as { title?: string }).title;
    return title ? title.slice(0, 80) : node.id.slice(0, 6);
  }
  if (graphType === "author") {
    return (props as { name?: string }).name ?? node.id.slice(0, 6);
  }
  if (graphType === "keyword") {
    return (props as { display?: string }).display ?? node.id.slice(0, 6);
  }
  return node.id.slice(0, 6);
}

export function GraphViewer({ graphId }: { graphId: string }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["graph", graphId],
    queryFn: () =>
      graphsApi.get(graphId, { nodeLimit: 2000, edgeLimit: 5000 }),
  });

  const containerRef = useRef<HTMLDivElement | null>(null);
  const sigmaRef = useRef<Sigma | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);

  const graph = useMemo(() => {
    if (!data) return null;
    const g = new Graph({ multi: false, type: "undirected" });

    // Compute weighted degree for node sizing
    const degree: Record<string, number> = {};
    for (const e of data.edges) {
      degree[e.source_node_id] = (degree[e.source_node_id] ?? 0) + e.weight;
      degree[e.target_node_id] = (degree[e.target_node_id] ?? 0) + e.weight;
    }
    const maxDeg = Math.max(1, ...Object.values(degree));

    for (const n of data.nodes) {
      const d = degree[n.id] ?? 0;
      g.addNode(n.id, {
        label: nodeLabel(n, data.graph_type),
        size: 2 + 8 * Math.sqrt(d / maxDeg),
        color: colorForCluster(n.cluster_id),
        x: Math.random(),
        y: Math.random(),
        cluster: n.cluster_id,
      });
    }
    for (const e of data.edges) {
      if (g.hasNode(e.source_node_id) && g.hasNode(e.target_node_id)) {
        if (!g.hasEdge(e.source_node_id, e.target_node_id)) {
          g.addEdge(e.source_node_id, e.target_node_id, {
            size: 0.4 + 0.6 * Math.log10(1 + e.weight),
            color: "rgba(31,30,29,0.12)",
          });
        }
      }
    }

    // Layout
    if (g.order > 0) {
      forceAtlas2.assign(g, {
        iterations: g.order > 500 ? 100 : 200,
        settings: {
          gravity: 1,
          scalingRatio: 8,
          slowDown: 5,
          barnesHutOptimize: g.order > 1000,
        },
      });
    }
    return g;
  }, [data]);

  useEffect(() => {
    if (!graph || !containerRef.current) return;
    if (sigmaRef.current) {
      sigmaRef.current.kill();
      sigmaRef.current = null;
    }
    const renderer = new Sigma(graph, containerRef.current, {
      renderLabels: graph.order < 300,
      labelSize: 11,
      labelColor: { color: "#1f1e1d" },
      labelWeight: "500",
      minCameraRatio: 0.05,
      maxCameraRatio: 20,
    });

    renderer.on("enterNode", ({ node }) => setHovered(node));
    renderer.on("leaveNode", () => setHovered(null));

    sigmaRef.current = renderer;
    return () => {
      renderer.kill();
      sigmaRef.current = null;
    };
  }, [graph]);

  if (isLoading) {
    return (
      <Card className="p-8 text-center text-sm text-[var(--color-fg-muted)]">
        그래프 로딩 중…
      </Card>
    );
  }
  if (error || !data) {
    return (
      <Card className="p-6 text-sm text-[var(--color-danger)]">
        그래프를 불러오지 못했습니다.
      </Card>
    );
  }

  const hoveredNode = hovered
    ? data.nodes.find((n) => n.id === hovered)
    : null;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <CardTitle className="text-base">
              {graphTypeLabel[data.graph_type]}
            </CardTitle>
            <Badge variant="neutral">노드 {formatNumber(data.node_count)}</Badge>
            <Badge variant="neutral">엣지 {formatNumber(data.edge_count)}</Badge>
            <Badge variant="accent">
              군집 {formatNumber(data.cluster_count)}
            </Badge>
          </div>
          <div className="text-xs text-[var(--color-fg-muted)]">
            상위 노드 {data.nodes.length} / 엣지 {data.edges.length} (가중치순)
          </div>
        </CardHeader>
        <CardBody className="p-0">
          <div
            ref={containerRef}
            className="h-[640px] w-full bg-[var(--color-surface)]"
          />
        </CardBody>
      </Card>

      {hoveredNode ? (
        <Card>
          <CardBody className="text-sm">
            <div className="text-[11px] uppercase tracking-wider text-[var(--color-fg-subtle)]">
              호버한 노드
            </div>
            <div className="mt-1 font-medium text-[var(--color-fg)]">
              {nodeLabel(hoveredNode, data.graph_type)}
            </div>
            {hoveredNode.cluster_id !== null &&
            hoveredNode.cluster_id !== undefined ? (
              <Badge variant="info" className="mt-2">
                군집 #{hoveredNode.cluster_id}
              </Badge>
            ) : null}
          </CardBody>
        </Card>
      ) : null}
    </div>
  );
}
