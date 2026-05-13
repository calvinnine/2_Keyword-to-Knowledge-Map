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
import type { GraphResultDetail, GraphNodeRead, GraphType } from "@/lib/types/api";

const graphTypeLabel: Record<GraphType, string> = {
  paper: "논문 네트워크",
  author: "저자 네트워크",
  keyword: "키워드 네트워크",
};

// Categorical palette for clusters
const CLUSTER_COLORS = [
  "#C8643E", "#3D6796", "#3F7A4E", "#B88A2A", "#7B4A8B",
  "#B54241", "#516D8E", "#7A6A3C", "#5D8175", "#A05A2C",
];

function colorForCluster(cid: number | null | undefined): string {
  if (cid === null || cid === undefined) return "#94928d";
  return CLUSTER_COLORS[cid % CLUSTER_COLORS.length];
}

function nodeLabel(node: GraphNodeRead, graphType: GraphType): string {
  const props = node.properties ?? {};
  if (graphType === "paper") return ((props as { title?: string }).title ?? "").slice(0, 80) || node.id.slice(0, 6);
  if (graphType === "author") return (props as { name?: string }).name ?? node.id.slice(0, 6);
  if (graphType === "keyword") return (props as { display?: string }).display ?? node.id.slice(0, 6);
  return node.id.slice(0, 6);
}

function NodeDetailPanel({
  node,
  graphType,
  onClose,
}: {
  node: GraphNodeRead;
  graphType: GraphType;
  onClose: () => void;
}) {
  const props = node.properties ?? {};
  const label = nodeLabel(node, graphType);

  return (
    <Card>
      <CardBody className="text-sm space-y-2">
        <div className="flex items-start justify-between gap-2">
          <div>
            <div className="text-[11px] uppercase tracking-wider text-[var(--color-fg-subtle)]">
              선택된 노드
            </div>
            <div className="mt-0.5 font-medium text-[var(--color-fg)] leading-snug">
              {label}
            </div>
          </div>
          <button
            onClick={onClose}
            className="shrink-0 text-[var(--color-fg-muted)] hover:text-[var(--color-fg)] text-base leading-none"
            aria-label="닫기"
          >
            ✕
          </button>
        </div>

        <div className="flex flex-wrap gap-2">
          {node.cluster_id !== null && node.cluster_id !== undefined && (
            <Badge variant="info">군집 #{node.cluster_id}</Badge>
          )}
        </div>

        <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
          {graphType === "paper" && (
            <>
              {(props as { year?: number }).year && (
                <>
                  <dt className="text-[var(--color-fg-muted)]">발행 연도</dt>
                  <dd>{(props as { year?: number }).year}</dd>
                </>
              )}
              {(props as { citation_count?: number }).citation_count !== undefined && (
                <>
                  <dt className="text-[var(--color-fg-muted)]">피인용 수</dt>
                  <dd>{formatNumber((props as { citation_count: number }).citation_count)}</dd>
                </>
              )}
            </>
          )}
          {graphType === "author" && (
            <>
              {(props as { paper_count?: number }).paper_count !== undefined && (
                <>
                  <dt className="text-[var(--color-fg-muted)]">논문 수</dt>
                  <dd>{formatNumber((props as { paper_count: number }).paper_count)}</dd>
                </>
              )}
              {(props as { citation_count?: number }).citation_count !== undefined && (
                <>
                  <dt className="text-[var(--color-fg-muted)]">피인용 수</dt>
                  <dd>{formatNumber((props as { citation_count: number }).citation_count)}</dd>
                </>
              )}
            </>
          )}
          {graphType === "keyword" && (
            <>
              {(props as { paper_count?: number }).paper_count !== undefined && (
                <>
                  <dt className="text-[var(--color-fg-muted)]">논문 수</dt>
                  <dd>{formatNumber((props as { paper_count: number }).paper_count)}</dd>
                </>
              )}
            </>
          )}
        </dl>
      </CardBody>
    </Card>
  );
}

export function GraphViewer({ graphId }: { graphId: string }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["graph", graphId],
    queryFn: () => graphsApi.get(graphId, { nodeLimit: 2000, edgeLimit: 5000 }),
  });

  const containerRef = useRef<HTMLDivElement | null>(null);
  const sigmaRef = useRef<Sigma | null>(null);
  const [selected, setSelected] = useState<string | null>(null);

  // Filters
  const [activeCluster, setActiveCluster] = useState<number | null>(null);
  const [activeEdgeType, setActiveEdgeType] = useState<string | null>(null);

  const clusterIds = useMemo(() => {
    if (!data) return [];
    const ids = new Set<number>();
    for (const n of data.nodes) {
      if (n.cluster_id !== null && n.cluster_id !== undefined) ids.add(n.cluster_id);
    }
    return Array.from(ids).sort((a, b) => a - b);
  }, [data]);

  const edgeTypes = useMemo(() => {
    if (!data) return [];
    const types = new Set<string>();
    for (const e of data.edges) {
      if (e.edge_type) types.add(e.edge_type);
    }
    return Array.from(types).sort();
  }, [data]);

  const graph = useMemo(() => {
    if (!data) return null;
    const g = new Graph({ multi: false, type: "undirected" });

    // Filter edges by edge type
    const filteredEdges = activeEdgeType
      ? data.edges.filter((e) => e.edge_type === activeEdgeType)
      : data.edges;

    // Filter nodes by cluster
    const filteredNodeIds = activeCluster !== null
      ? new Set(data.nodes.filter((n) => n.cluster_id === activeCluster).map((n) => n.id))
      : null;

    // Compute weighted degree for sizing
    const degree: Record<string, number> = {};
    for (const e of filteredEdges) {
      degree[e.source_node_id] = (degree[e.source_node_id] ?? 0) + e.weight;
      degree[e.target_node_id] = (degree[e.target_node_id] ?? 0) + e.weight;
    }
    const maxDeg = Math.max(1, ...Object.values(degree));

    // Check if all nodes have pre-computed coords
    const hasLayout = data.nodes.length > 0 && data.nodes[0].x_pos !== null;

    for (const n of data.nodes) {
      if (filteredNodeIds && !filteredNodeIds.has(n.id)) continue;
      const d = degree[n.id] ?? 0;
      g.addNode(n.id, {
        label: nodeLabel(n, data.graph_type),
        size: 2 + 8 * Math.sqrt(d / maxDeg),
        color: colorForCluster(n.cluster_id),
        x: hasLayout ? (n.x_pos ?? Math.random()) : Math.random(),
        y: hasLayout ? (n.y_pos ?? Math.random()) : Math.random(),
        cluster: n.cluster_id,
      });
    }

    for (const e of filteredEdges) {
      if (g.hasNode(e.source_node_id) && g.hasNode(e.target_node_id)) {
        if (!g.hasEdge(e.source_node_id, e.target_node_id)) {
          g.addEdge(e.source_node_id, e.target_node_id, {
            size: 0.4 + 0.6 * Math.log10(1 + e.weight),
            color: "rgba(31,30,29,0.12)",
          });
        }
      }
    }

    // Only run ForceAtlas2 if there are no pre-computed coords
    if (g.order > 0 && !hasLayout) {
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
  }, [data, activeCluster, activeEdgeType]);

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

    renderer.on("clickNode", ({ node }) =>
      setSelected((prev) => (prev === node ? null : node))
    );
    renderer.on("clickStage", () => setSelected(null));

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

  const selectedNode = selected ? data.nodes.find((n) => n.id === selected) ?? null : null;
  const backendBase = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";
  const graphApiBase = `${backendBase}/api/v1/graphs/${graphId}`;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <CardTitle className="text-base">
              {graphTypeLabel[data.graph_type]}
            </CardTitle>
            <Badge variant="neutral">노드 {formatNumber(data.node_count)}</Badge>
            <Badge variant="neutral">엣지 {formatNumber(data.edge_count)}</Badge>
            <Badge variant="accent">군집 {formatNumber(data.cluster_count)}</Badge>
          </div>

          {/* Export buttons */}
          <div className="flex items-center gap-2">
            <a
              href={`${graphApiBase}/export/gexf`}
              download
              className="text-xs text-[var(--color-fg-muted)] hover:text-[var(--color-fg)] underline"
            >
              GEXF
            </a>
            <a
              href={`${graphApiBase}/export/csv/nodes`}
              download
              className="text-xs text-[var(--color-fg-muted)] hover:text-[var(--color-fg)] underline"
            >
              CSV (노드)
            </a>
            <a
              href={`${graphApiBase}/export/csv/edges`}
              download
              className="text-xs text-[var(--color-fg-muted)] hover:text-[var(--color-fg)] underline"
            >
              CSV (엣지)
            </a>
          </div>
        </CardHeader>

        {/* Filters */}
        {(clusterIds.length > 0 || edgeTypes.length > 1) && (
          <div className="border-t border-[var(--color-border)] px-4 py-2 flex flex-wrap gap-3 text-xs">
            {clusterIds.length > 0 && (
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="text-[var(--color-fg-muted)]">군집:</span>
                <button
                  onClick={() => setActiveCluster(null)}
                  className={[
                    "rounded px-2 py-0.5 border transition-colors",
                    activeCluster === null
                      ? "border-[var(--color-accent)] bg-[var(--color-accent-soft)] text-[var(--color-accent)]"
                      : "border-[var(--color-border)] text-[var(--color-fg-muted)] hover:border-[var(--color-accent-soft)]",
                  ].join(" ")}
                >
                  전체
                </button>
                {clusterIds.map((cid) => (
                  <button
                    key={cid}
                    onClick={() => setActiveCluster(activeCluster === cid ? null : cid)}
                    className={[
                      "rounded px-2 py-0.5 border transition-colors",
                      activeCluster === cid
                        ? "border-[var(--color-accent)] bg-[var(--color-accent-soft)] text-[var(--color-accent)]"
                        : "border-[var(--color-border)] text-[var(--color-fg-muted)] hover:border-[var(--color-accent-soft)]",
                    ].join(" ")}
                    style={activeCluster === cid ? {} : { borderLeftColor: colorForCluster(cid) }}
                  >
                    #{cid}
                  </button>
                ))}
              </div>
            )}

            {edgeTypes.length > 1 && (
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="text-[var(--color-fg-muted)]">엣지 유형:</span>
                <button
                  onClick={() => setActiveEdgeType(null)}
                  className={[
                    "rounded px-2 py-0.5 border transition-colors",
                    activeEdgeType === null
                      ? "border-[var(--color-accent)] bg-[var(--color-accent-soft)] text-[var(--color-accent)]"
                      : "border-[var(--color-border)] text-[var(--color-fg-muted)] hover:border-[var(--color-accent-soft)]",
                  ].join(" ")}
                >
                  전체
                </button>
                {edgeTypes.map((et) => (
                  <button
                    key={et}
                    onClick={() => setActiveEdgeType(activeEdgeType === et ? null : et)}
                    className={[
                      "rounded px-2 py-0.5 border transition-colors",
                      activeEdgeType === et
                        ? "border-[var(--color-accent)] bg-[var(--color-accent-soft)] text-[var(--color-accent)]"
                        : "border-[var(--color-border)] text-[var(--color-fg-muted)] hover:border-[var(--color-accent-soft)]",
                    ].join(" ")}
                  >
                    {et.replace(/_/g, " ")}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        <CardBody className="p-0">
          <div
            ref={containerRef}
            className="h-[640px] w-full bg-[var(--color-surface)] cursor-pointer"
          />
          <div className="px-4 py-1.5 text-[11px] text-[var(--color-fg-subtle)] border-t border-[var(--color-border)]">
            표시: 노드 {data.nodes.length} / 엣지 {data.edges.length} · 노드를 클릭하면 상세 정보를 확인합니다
          </div>
        </CardBody>
      </Card>

      {selectedNode && (
        <NodeDetailPanel
          node={selectedNode}
          graphType={data.graph_type}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}
