"use client";

import dynamic from "next/dynamic";

// Sigma touches WebGL at import time and must not run on the server.
// Lazy-load the real viewer client-side only.
const GraphViewer = dynamic(
  () => import("./GraphViewer").then((m) => m.GraphViewer),
  {
    ssr: false,
    loading: () => (
      <div className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-8 text-center text-sm text-[var(--color-fg-muted)]">
        그래프 시각화 모듈 로딩 중…
      </div>
    ),
  }
);

export function GraphViewerClient({ graphId }: { graphId: string }) {
  return <GraphViewer graphId={graphId} />;
}
