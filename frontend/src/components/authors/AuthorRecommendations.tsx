"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { authorsApi } from "@/lib/api/client";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { formatNumber } from "@/lib/utils";
import { ROLE_LABELS } from "@/lib/types/api";
import type { AuthorRecommendation, RoleLabel } from "@/lib/types/api";

const ROLE_DESCRIPTIONS: Record<RoleLabel, string> = {
  "Core Influencer": "해당 키워드와 관련된 고영향 논문 보유",
  "Bridge Researcher": "서로 다른 연구 클러스터를 연결",
  "Productive Contributor": "관련 논문을 꾸준히 생산",
  "Emerging Researcher": "최근 빠르게 부상 중인 연구자",
  "Niche Specialist": "특정 세부 클러스터 집중 전문가",
  "Domestic R&D Actor": "국내 R&D와 관련성이 높은 연구자",
};

const CAUTION_LABELS: Record<string, string> = {
  OLD_IMPACT_ONLY: "최근 활동 낮음",
  HIGH_LOW_IMPACT_RATIO: "저영향 논문 비중 높음",
  LOW_METADATA_COMPLETENESS: "메타데이터 부족",
  POSSIBLE_NAME_COLLISION: "동명이인 가능성",
};

function ScoreBar({ value }: { value: number | null }) {
  if (value === null) return null;
  const pct = Math.round(value * 100);
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 flex-1 rounded-full bg-[var(--color-border)]">
        <div
          className="h-full rounded-full bg-[var(--color-accent)]"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-8 text-right text-[11px] tabular-nums text-[var(--color-fg-muted)]">
        {pct}
      </span>
    </div>
  );
}

function AuthorCard({ author }: { author: AuthorRecommendation }) {
  return (
    <div className="rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3 space-y-2">
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="font-medium text-[var(--color-fg)] text-sm leading-snug">
            {author.name}
          </div>
          {author.primary_country_name && (
            <div className="text-xs text-[var(--color-fg-muted)]">
              {author.primary_country_name}
            </div>
          )}
        </div>
        <div className="text-xs text-[var(--color-fg-muted)] shrink-0 tabular-nums">
          논문 {formatNumber(author.related_paper_count)}
        </div>
      </div>

      {/* Role badges */}
      <div className="flex flex-wrap gap-1">
        {author.role_labels.map((r) => (
          <Badge key={r} variant="accent" className="text-[11px]">
            {r}
          </Badge>
        ))}
      </div>

      {/* Scores */}
      <div className="space-y-1 text-xs">
        <div className="flex items-center gap-2">
          <span className="w-20 shrink-0 text-[var(--color-fg-muted)]">영향력</span>
          <ScoreBar value={author.global_scholarly_impact} />
        </div>
        <div className="flex items-center gap-2">
          <span className="w-20 shrink-0 text-[var(--color-fg-muted)]">네트워크</span>
          <ScoreBar value={author.structural_score} />
        </div>
        <div className="flex items-center gap-2">
          <span className="w-20 shrink-0 text-[var(--color-fg-muted)]">최신성</span>
          <ScoreBar value={author.momentum_score} />
        </div>
      </div>

      {/* Caution flags */}
      {author.caution_flags.length > 0 && (
        <div className="flex flex-wrap gap-1 pt-0.5">
          {author.caution_flags.map((f) => (
            <span
              key={f}
              className="rounded bg-[var(--color-warning-soft,#fef3c7)] px-1.5 py-0.5 text-[10px] text-[var(--color-warning,#92400e)]"
              title={f}
            >
              주의 · {CAUTION_LABELS[f] ?? f}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export function AuthorRecommendations({ jobId }: { jobId: string }) {
  const [activeRole, setActiveRole] = useState<RoleLabel | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ["author-recommendations", jobId, activeRole],
    queryFn: () => authorsApi.recommendations(jobId, activeRole ?? undefined, 50),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">연구자 추천</CardTitle>
        <p className="mt-0.5 text-xs text-[var(--color-fg-muted)]">
          단순 논문 수가 아닌 영향력·구조적 역할·최신성을 종합 평가합니다.
        </p>
      </CardHeader>

      {/* Role filter tabs */}
      <div className="border-t border-[var(--color-border)] px-4 py-2 flex flex-wrap gap-2">
        <button
          onClick={() => setActiveRole(null)}
          className={[
            "rounded px-2.5 py-1 text-xs border transition-colors",
            activeRole === null
              ? "border-[var(--color-accent)] bg-[var(--color-accent-soft)] text-[var(--color-accent)]"
              : "border-[var(--color-border)] text-[var(--color-fg-muted)] hover:border-[var(--color-accent-soft)]",
          ].join(" ")}
        >
          전체
        </button>
        {ROLE_LABELS.map((role) => (
          <button
            key={role}
            onClick={() => setActiveRole(activeRole === role ? null : role)}
            className={[
              "rounded px-2.5 py-1 text-xs border transition-colors",
              activeRole === role
                ? "border-[var(--color-accent)] bg-[var(--color-accent-soft)] text-[var(--color-accent)]"
                : "border-[var(--color-border)] text-[var(--color-fg-muted)] hover:border-[var(--color-accent-soft)]",
            ].join(" ")}
            title={ROLE_DESCRIPTIONS[role]}
          >
            {role}
          </button>
        ))}
      </div>

      <CardBody className="space-y-2 pt-2">
        {isLoading && (
          <p className="text-sm text-[var(--color-fg-muted)]">분석 중…</p>
        )}
        {error && (
          <p className="text-sm text-[var(--color-danger)]">
            추천 정보를 불러오지 못했습니다.
          </p>
        )}
        {!isLoading && data && data.length === 0 && (
          <p className="text-sm text-[var(--color-fg-muted)]">
            {activeRole
              ? `'${activeRole}' 역할의 연구자가 없습니다.`
              : "분석이 완료되면 추천 결과가 표시됩니다."}
          </p>
        )}
        {data?.map((author) => (
          <AuthorCard key={author.author_id} author={author} />
        ))}
      </CardBody>
    </Card>
  );
}
