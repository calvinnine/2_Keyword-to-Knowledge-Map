"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ntisApi } from "@/lib/api/client";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import type { AuthorMatrixItem } from "@/lib/types/api";

// Quadrant colours (same palette as GraphViewer cluster colours)
const QUADRANT_COLORS = {
  TL: "#3D6796", // high domestic, low global   → "Domestic Specialist"
  TR: "#C8643E", // high domestic, high global  → "Strategic Connector"
  BL: "#94928d", // low domestic, low global    → "General Researcher"
  BR: "#3F7A4E", // low domestic, high global   → "Global Scholar"
};

const QUADRANT_LABELS = {
  TL: "국내 전문가",
  TR: "전략적 연결자",
  BL: "일반 연구자",
  BR: "글로벌 학자",
};

function quadrant(gsi: number, drr: number): keyof typeof QUADRANT_COLORS {
  const highGsi = gsi >= 0.5;
  const highDrr = drr >= 0.5;
  if (!highGsi && highDrr) return "TL";
  if (highGsi && highDrr) return "TR";
  if (!highGsi && !highDrr) return "BL";
  return "BR";
}

const W = 560;  // SVG viewport width
const H = 400;  // SVG viewport height
const PAD = { top: 24, right: 24, bottom: 48, left: 56 };

function toX(v: number) {
  return PAD.left + v * (W - PAD.left - PAD.right);
}

function toY(v: number) {
  // Y axis: 0 at bottom, 1 at top → invert
  return H - PAD.bottom - v * (H - PAD.top - PAD.bottom);
}

export function ImpactMatrix({ jobId }: { jobId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["ntis-matrix", jobId],
    queryFn: () => ntisApi.getMatrix(jobId),
  });

  const [hovered, setHovered] = useState<AuthorMatrixItem | null>(null);

  if (isLoading) {
    return (
      <Card className="p-8 text-center text-sm text-[var(--color-fg-muted)]">
        매트릭스 로딩 중…
      </Card>
    );
  }

  if (!data || data.length === 0) {
    return (
      <Card className="p-8 text-center text-sm text-[var(--color-fg-muted)]">
        매트릭스 데이터가 없습니다. NTIS 분석 후 다시 확인하세요.
      </Card>
    );
  }

  // Only plot points that have both scores
  const points = data.filter(
    (d) => d.global_scholarly_impact !== null && d.domestic_rnd_relevance !== null
  ) as (AuthorMatrixItem & { global_scholarly_impact: number; domestic_rnd_relevance: number })[];

  return (
    <Card>
      <CardHeader className="flex items-center justify-between gap-4">
        <CardTitle className="text-sm">글로벌 영향력 × 국내 R&D 연관도 매트릭스</CardTitle>
        <div className="flex flex-wrap gap-2">
          {(Object.keys(QUADRANT_COLORS) as (keyof typeof QUADRANT_COLORS)[]).map((q) => (
            <span key={q} className="flex items-center gap-1 text-[11px] text-[var(--color-fg-muted)]">
              <span
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{ background: QUADRANT_COLORS[q] }}
              />
              {QUADRANT_LABELS[q]}
            </span>
          ))}
        </div>
      </CardHeader>
      <CardBody className="p-0 pb-4">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="w-full"
          style={{ maxHeight: 420 }}
        >
          {/* Quadrant background shading */}
          {/* Top-right (Strategic Connector) — subtle highlight */}
          <rect
            x={toX(0.5)} y={toY(1)}
            width={toX(1) - toX(0.5)} height={toY(0.5) - toY(1)}
            fill={QUADRANT_COLORS.TR}
            fillOpacity={0.06}
          />

          {/* Axis lines */}
          <line
            x1={PAD.left} y1={PAD.top}
            x2={PAD.left} y2={H - PAD.bottom}
            stroke="var(--color-border-strong)" strokeWidth={1}
          />
          <line
            x1={PAD.left} y1={H - PAD.bottom}
            x2={W - PAD.right} y2={H - PAD.bottom}
            stroke="var(--color-border-strong)" strokeWidth={1}
          />

          {/* Midpoint crosshair */}
          <line
            x1={toX(0.5)} y1={PAD.top}
            x2={toX(0.5)} y2={H - PAD.bottom}
            stroke="var(--color-border)" strokeWidth={1} strokeDasharray="4 3"
          />
          <line
            x1={PAD.left} y1={toY(0.5)}
            x2={W - PAD.right} y2={toY(0.5)}
            stroke="var(--color-border)" strokeWidth={1} strokeDasharray="4 3"
          />

          {/* Y-axis ticks + labels */}
          {[0, 0.25, 0.5, 0.75, 1.0].map((v) => (
            <g key={v}>
              <line
                x1={PAD.left - 4} y1={toY(v)}
                x2={PAD.left} y2={toY(v)}
                stroke="var(--color-border-strong)" strokeWidth={1}
              />
              <text
                x={PAD.left - 6} y={toY(v)}
                textAnchor="end" dominantBaseline="middle"
                fontSize={9} fill="var(--color-fg-subtle)"
              >
                {v.toFixed(2)}
              </text>
            </g>
          ))}

          {/* X-axis ticks + labels */}
          {[0, 0.25, 0.5, 0.75, 1.0].map((v) => (
            <g key={v}>
              <line
                x1={toX(v)} y1={H - PAD.bottom}
                x2={toX(v)} y2={H - PAD.bottom + 4}
                stroke="var(--color-border-strong)" strokeWidth={1}
              />
              <text
                x={toX(v)} y={H - PAD.bottom + 12}
                textAnchor="middle" fontSize={9} fill="var(--color-fg-subtle)"
              >
                {v.toFixed(2)}
              </text>
            </g>
          ))}

          {/* Axis labels */}
          <text
            x={(PAD.left + W - PAD.right) / 2} y={H - 6}
            textAnchor="middle" fontSize={10} fill="var(--color-fg-muted)"
          >
            글로벌 영향력 (GSI)
          </text>
          <text
            x={10} y={(PAD.top + H - PAD.bottom) / 2}
            textAnchor="middle" fontSize={10} fill="var(--color-fg-muted)"
            transform={`rotate(-90, 10, ${(PAD.top + H - PAD.bottom) / 2})`}
          >
            국내 R&D 연관도
          </text>

          {/* Data points */}
          {points.map((d) => {
            const cx = toX(d.global_scholarly_impact);
            const cy = toY(d.domestic_rnd_relevance);
            const q = quadrant(d.global_scholarly_impact, d.domestic_rnd_relevance);
            const isHovered = hovered?.author_id === d.author_id;
            return (
              <circle
                key={d.author_id}
                cx={cx} cy={cy}
                r={isHovered ? 7 : 5}
                fill={QUADRANT_COLORS[q]}
                fillOpacity={isHovered ? 1 : 0.75}
                stroke={isHovered ? "var(--color-fg)" : "none"}
                strokeWidth={1.5}
                style={{ cursor: "pointer", transition: "r 0.1s" }}
                onMouseEnter={() => setHovered(d)}
                onMouseLeave={() => setHovered(null)}
              />
            );
          })}
        </svg>

        {/* Hover tooltip */}
        {hovered && (
          <div className="mx-5 mt-2 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface-2)] px-4 py-3 text-sm">
            <div className="font-medium text-[var(--color-fg)]">{hovered.name}</div>
            <div className="mt-1 flex flex-wrap gap-3 text-xs text-[var(--color-fg-muted)]">
              <span>GSI: <strong>{hovered.global_scholarly_impact?.toFixed(3) ?? "—"}</strong></span>
              <span>국내 R&D: <strong>{hovered.domestic_rnd_relevance?.toFixed(3) ?? "—"}</strong></span>
              <span>논문: <strong>{hovered.paper_count}</strong></span>
              <span>인용: <strong>{hovered.citation_count.toLocaleString()}</strong></span>
            </div>
            {hovered.role_labels && hovered.role_labels.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {hovered.role_labels.map((r) => (
                  <Badge key={r} variant="info" className="text-[10px]">
                    {r}
                  </Badge>
                ))}
              </div>
            )}
          </div>
        )}

        <p className="mt-2 px-5 text-[11px] text-[var(--color-fg-subtle)]">
          {points.length}명의 저자가 표시됨. 점에 마우스를 올리면 상세 정보를 확인합니다.
        </p>
      </CardBody>
    </Card>
  );
}
