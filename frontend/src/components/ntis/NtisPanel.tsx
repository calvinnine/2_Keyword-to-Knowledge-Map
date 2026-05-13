"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ntisApi } from "@/lib/api/client";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { formatNumber } from "@/lib/utils";
import type { NtisProjectSummary } from "@/lib/types/api";
import { ImpactMatrix } from "./ImpactMatrix";

function formatBudget(won: number | null): string {
  if (won === null) return "—";
  if (won >= 1_000_000_000) return `${(won / 1_000_000_000).toFixed(1)}B원`;
  if (won >= 1_000_000) return `${(won / 1_000_000).toFixed(0)}M원`;
  return `${formatNumber(won)}원`;
}

export function NtisPanel({ jobId }: { jobId: string }) {
  const queryClient = useQueryClient();
  const [triggered, setTriggered] = useState(false);
  const [matrixVisible, setMatrixVisible] = useState(false);

  const overview = useQuery({
    queryKey: ["ntis-overview", jobId],
    queryFn: () => ntisApi.getOverview(jobId),
    // Poll after trigger until projects appear
    refetchInterval: triggered
      ? (q) => ((q.state.data?.ntis_project_count ?? 0) > 0 ? false : 4_000)
      : false,
  });

  const trigger = useMutation({
    mutationFn: () => ntisApi.triggerOverlay(jobId),
    onSuccess: () => {
      setTriggered(true);
      // Start polling
      queryClient.invalidateQueries({ queryKey: ["ntis-overview", jobId] });
    },
  });

  const hasData = (overview.data?.ntis_project_count ?? 0) > 0;

  return (
    <div className="space-y-4">
      {/* Header card */}
      <Card>
        <CardHeader className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <CardTitle className="text-sm">국내 R&D 오버레이 (NTIS)</CardTitle>
            {hasData && (
              <>
                <Badge variant="neutral">
                  과제 {formatNumber(overview.data!.ntis_project_count)}
                </Badge>
                <Badge variant="info">
                  매칭 {formatNumber(overview.data!.comparative_match_count)}
                </Badge>
              </>
            )}
          </div>
          <div className="flex items-center gap-2">
            {hasData && (
              <button
                onClick={() => setMatrixVisible((v) => !v)}
                className="inline-flex h-8 items-center gap-1.5 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 text-xs font-medium text-[var(--color-fg)] hover:bg-[var(--color-surface-2)]"
              >
                {matrixVisible ? "매트릭스 닫기" : "영향력 매트릭스"}
              </button>
            )}
            <button
              onClick={() => trigger.mutate()}
              disabled={trigger.isPending || triggered}
              className="inline-flex h-8 items-center gap-1.5 rounded-[var(--radius-md)] bg-[var(--color-accent)] px-3 text-xs font-medium text-white hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {trigger.isPending || (triggered && !hasData)
                ? "분석 중…"
                : hasData
                ? "재실행"
                : "NTIS 분석 시작"}
            </button>
          </div>
        </CardHeader>
        {!hasData && !trigger.isPending && !triggered && (
          <CardBody className="text-sm text-[var(--color-fg-muted)]">
            NTIS 분석을 실행하면 국내 R&D 과제 데이터를 수집하고 논문·저자와의
            연관성을 계산합니다. NTIS_API_KEY가 설정되지 않으면 키워드·저자·기관
            기반 비교 분석만 실행됩니다.
          </CardBody>
        )}
        {triggered && !hasData && (
          <CardBody className="text-sm text-[var(--color-fg-muted)]">
            NTIS 데이터 수집 중… 잠시 후 자동으로 갱신됩니다.
          </CardBody>
        )}
      </Card>

      {/* Impact matrix */}
      {matrixVisible && hasData && <ImpactMatrix jobId={jobId} />}

      {/* Project list */}
      {hasData && (
        <Card className="overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b border-[var(--color-border)] bg-[var(--color-surface-2)] text-left text-xs uppercase tracking-wider text-[var(--color-fg-muted)]">
              <tr>
                <th className="px-5 py-2.5 font-medium">과제명</th>
                <th className="px-5 py-2.5 font-medium">부처</th>
                <th className="px-5 py-2.5 font-medium">수행기관</th>
                <th className="px-5 py-2.5 font-medium">기간</th>
                <th className="px-5 py-2.5 font-medium text-right">예산</th>
              </tr>
            </thead>
            <tbody>
              {overview.data!.projects.map((p) => (
                <ProjectRow key={p.id} project={p} />
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}

function ProjectRow({ project: p }: { project: NtisProjectSummary }) {
  const period =
    p.start_year && p.end_year
      ? `${p.start_year}–${p.end_year}`
      : p.start_year
      ? `${p.start_year}~`
      : "—";

  return (
    <tr className="border-b border-[var(--color-border)] last:border-0 hover:bg-[var(--color-surface-2)]">
      <td className="px-5 py-2.5 align-top">
        <div className="line-clamp-2 font-medium text-[var(--color-fg)]">
          {p.title ?? "(제목 없음)"}
        </div>
        {p.ntis_project_id && (
          <span className="mt-0.5 font-mono text-[10px] text-[var(--color-fg-subtle)]">
            {p.ntis_project_id}
          </span>
        )}
        {p.keywords && p.keywords.length > 0 && (
          <div className="mt-1 flex flex-wrap gap-1">
            {p.keywords.slice(0, 4).map((k, i) => (
              <span
                key={i}
                className="rounded-full bg-[var(--color-surface-2)] px-2 py-0.5 text-[10px] text-[var(--color-fg-subtle)]"
              >
                {k}
              </span>
            ))}
          </div>
        )}
      </td>
      <td className="px-5 py-2.5 align-top text-[var(--color-fg-muted)]">
        {p.govt_dept ?? "—"}
      </td>
      <td className="px-5 py-2.5 align-top text-[var(--color-fg-muted)]">
        {p.performing_org ?? "—"}
      </td>
      <td className="px-5 py-2.5 align-top text-[var(--color-fg-muted)]">
        {period}
      </td>
      <td className="px-5 py-2.5 align-top text-right font-mono text-[var(--color-fg)]">
        {formatBudget(p.total_budget)}
      </td>
    </tr>
  );
}
