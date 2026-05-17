"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  authorsApi,
  graphsApi,
  jobsApi,
  keywordsApi,
  papersApi,
} from "@/lib/api/client";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Tabs } from "@/components/ui/Tabs";
import { Badge } from "@/components/ui/Badge";
import { JobStatusBadge } from "./JobStatusBadge";
import { JobProgressStepper } from "./JobProgressStepper";
import { AuthorRecommendations } from "@/components/authors/AuthorRecommendations";
import { NtisPanel } from "@/components/ntis/NtisPanel";
import { formatDateTime, formatNumber } from "@/lib/utils";
import { PUBLICATION_SCOPE_OPTIONS, WOS_INDEX_OPTIONS } from "@/lib/types/api";
import type { GraphType, Intent } from "@/lib/types/api";

type TabKey = "papers" | "authors" | "keywords" | "graphs" | "ntis";

const intentLabel: Record<Intent, string> = {
  author_influence: "저자 영향력",
  paper_centrality: "논문 중심성",
  keyword_clusters: "키워드 군집",
  general: "일반",
};

const intentDefaultTab: Record<Intent, TabKey> = {
  author_influence: "authors",
  paper_centrality: "papers",
  keyword_clusters: "keywords",
  general: "papers",
};

const graphTypeLabel: Record<GraphType, string> = {
  paper: "논문 네트워크",
  author: "저자 네트워크",
  keyword: "키워드 네트워크",
};

export function JobDetail({ jobId }: { jobId: string }) {
  const job = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => jobsApi.get(jobId),
    refetchInterval: (q) => {
      const s = q.state.data?.status;
      return s === "completed" || s === "failed" || s === "cancelled"
        ? false
        : 3_000;
    },
  });

  const initialTab: TabKey =
    (job.data?.params?.intent as Intent | undefined) &&
    intentDefaultTab[job.data!.params!.intent as Intent]
      ? intentDefaultTab[job.data!.params!.intent as Intent]
      : "papers";
  const [tab, setTab] = useState<TabKey>(initialTab);

  if (job.isLoading) {
    return (
      <Card className="p-8 text-center text-sm text-[var(--color-fg-muted)]">
        로딩 중…
      </Card>
    );
  }

  if (job.error || !job.data) {
    return (
      <Card className="p-6 text-sm text-[var(--color-danger)]">
        잡을 불러오지 못했습니다.
      </Card>
    );
  }

  const j = job.data;
  const intent = j.params?.intent as Intent | undefined;
  const originalQuery = j.params?.original_query as string | undefined;
  const originalKeyword = j.params?.original_keyword as string | undefined;
  const isAnalyzed = j.status === "completed";
  const scopeLabel = (() => {
    const raw = j.publication_scope ?? "all";
    if (raw === "all") return "전체";
    if (raw === "wos") return "WoS 전체";
    // comma-separated multi-select, e.g. "scie,ssci"
    const allOptions = [...PUBLICATION_SCOPE_OPTIONS, ...WOS_INDEX_OPTIONS];
    return raw
      .split(",")
      .map((s) => allOptions.find((o) => o.value === s.trim())?.label ?? s.toUpperCase())
      .join(" + ");
  })();

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <CardTitle className="truncate text-lg">{j.keyword}</CardTitle>
              <JobStatusBadge status={j.status} />
              {intent ? (
                <Badge variant="info">{intentLabel[intent]}</Badge>
              ) : null}
            </div>
            {originalQuery ? (
              <p className="mt-1 text-xs italic text-[var(--color-fg-muted)]">
                질의: “{originalQuery}”
              </p>
            ) : null}
            {originalKeyword && !originalQuery ? (
              <p className="mt-1 text-xs italic text-[var(--color-fg-muted)]">
                입력: “{originalKeyword}” → 영문 번역 적용
              </p>
            ) : null}
          </div>
          <div className="text-right text-xs text-[var(--color-fg-muted)]">
            <div>생성 {formatDateTime(j.created_at)}</div>
            {j.completed_at ? (
              <div>완료 {formatDateTime(j.completed_at)}</div>
            ) : null}
          </div>
        </CardHeader>
        <JobProgressStepper
          status={j.status}
          papers_collected={j.papers_collected}
          papers_processed={j.papers_processed}
        />
        <CardBody className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm md:grid-cols-5">
          <Stat label="최대 논문" value={formatNumber(j.max_papers)} />
          <Stat
            label="연도"
            value={
              j.year_start || j.year_end
                ? `${j.year_start ?? "—"} – ${j.year_end ?? "—"}`
                : "전체 기간"
            }
          />
          <Stat label="논문 범위" value={scopeLabel} />
          <Stat label="수집됨" value={formatNumber(j.papers_collected)} />
          <Stat label="정규화됨" value={formatNumber(j.papers_processed)} />
        </CardBody>
        {j.error_message ? (
          <div className="border-t border-[var(--color-border)] bg-[var(--color-danger-soft)] px-5 py-3 text-xs text-[var(--color-danger)]">
            {j.error_message}
          </div>
        ) : null}
      </Card>

      {j.insight ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <span>AI 인사이트</span>
              <Badge variant="accent">Groq</Badge>
            </CardTitle>
          </CardHeader>
          <CardBody className="text-sm leading-relaxed text-[var(--color-fg)]">
            {j.insight.split("\n\n").map((para, i) => (
              <p key={i} className={i > 0 ? "mt-3" : ""}>
                {para}
              </p>
            ))}
          </CardBody>
        </Card>
      ) : null}

      <div className="flex items-center justify-between">
        <Tabs
          value={tab}
          onChange={(v) => setTab(v as TabKey)}
          items={[
            { value: "papers", label: "논문" },
            { value: "authors", label: "저자" },
            { value: "keywords", label: "키워드" },
            { value: "graphs", label: "그래프" },
            { value: "ntis", label: "NTIS" },
          ]}
        />
        {!isAnalyzed ? (
          <span className="text-xs text-[var(--color-fg-muted)]">
            분석 완료 시 결과가 채워집니다.
          </span>
        ) : null}
      </div>

      {tab === "papers" && <PapersPanel jobId={jobId} disabled={!isAnalyzed} />}
      {tab === "authors" && (
        <div className="space-y-4">
          <AuthorsPanel jobId={jobId} disabled={!isAnalyzed} />
        </div>
      )}
      {tab === "keywords" && (
        <KeywordsPanel jobId={jobId} disabled={!isAnalyzed} />
      )}
      {tab === "graphs" && <GraphsPanel jobId={jobId} disabled={!isAnalyzed} />}
      {tab === "ntis" && (
        isAnalyzed
          ? <NtisPanel jobId={jobId} />
          : <Card className="p-8 text-center text-sm text-[var(--color-fg-muted)]">
              분석이 완료된 후 NTIS 오버레이를 실행할 수 있습니다.
            </Card>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-wider text-[var(--color-fg-subtle)]">
        {label}
      </div>
      <div className="mt-0.5 font-medium text-[var(--color-fg)]">{value}</div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helpers: venue badge + citation cell (used by Papers tab + AuthorRow expand)
// ---------------------------------------------------------------------------

function VenueBadge({
  type,
  size = "sm",
}: {
  type: string | null;
  size?: "sm" | "xs";
}) {
  if (!type) return null;
  // OpenAlex `type` values we typically see: article, preprint, book-chapter, etc.
  const t = type.toLowerCase();
  let label = "기타";
  let cls = "border-[var(--color-border)] text-[var(--color-fg-subtle)]";
  if (t === "preprint" || t.includes("preprint")) {
    label = "프리프린트";
    cls =
      "border-[var(--color-warning-soft)] bg-[var(--color-warning-soft)] text-[var(--color-warning)]";
  } else if (
    t === "article" ||
    t === "journal-article" ||
    t === "journal" ||
    t.includes("journal")
  ) {
    label = "저널";
    cls =
      "border-[var(--color-accent-soft)] bg-[var(--color-accent-soft)] text-[var(--color-accent)]";
  } else if (t === "conference" || t === "proceedings-article") {
    label = "학회";
    cls =
      "border-[var(--color-info-soft)] bg-[var(--color-info-soft)] text-[var(--color-info)]";
  } else if (t === "book" || t.includes("book")) {
    label = "도서";
  }
  const sizeCls =
    size === "xs"
      ? "text-[9px] px-1 py-0"
      : "text-[10px] px-1.5 py-0.5";
  return (
    <span
      className={`shrink-0 rounded-[var(--radius-sm)] border ${cls} ${sizeCls} font-medium`}
      title={`venue_type: ${type}`}
    >
      {label}
    </span>
  );
}

function CitationCell({
  paper,
  compact = false,
}: {
  paper: import("@/lib/types/api").PaperListItem;
  compact?: boolean;
}) {
  const {
    citation_count,
    citation_source,
    influential_citation_count,
    citation_by_journal,
    citation_by_preprint,
  } = paper;

  if (citation_count === null) {
    return (
      <span
        className={`font-mono text-[var(--color-fg-subtle)] ${
          compact ? "text-xs" : "text-sm"
        }`}
        title="S2·OpenAlex 모두에서 신뢰 가능한 인용수를 얻지 못했습니다"
      >
        —
      </span>
    );
  }

  const j = citation_by_journal;
  const p = citation_by_preprint;
  const hasBreakdown = j !== null || p !== null;
  // The breakdown labels what TYPE of papers cited this one.
  // It is sampled from S2's citation list and may not sum to citation_count.
  const breakdownSum = (j ?? 0) + (p ?? 0);
  const breakdownGap = hasBreakdown && breakdownSum < citation_count
    ? citation_count - breakdownSum
    : 0;

  // Tooltip explains the metrics so users don't expect them to sum.
  const tooltipParts: string[] = [];
  tooltipParts.push(
    citation_source === "s2"
      ? "출처: Semantic Scholar"
      : citation_source === "openalex"
      ? "출처: OpenAlex (sanity check 통과)"
      : "출처: 미상"
  );
  if (hasBreakdown) {
    tooltipParts.push(
      `인용한 논문 분포: 저널/학회 ${j ?? 0}편, 프리프린트 ${p ?? 0}편` +
        (breakdownGap > 0 ? `, 기타·미분류 ${breakdownGap}편` : "")
    );
  }
  if (influential_citation_count !== null) {
    tooltipParts.push(
      `핵심 인용 (S2 AI 판정, 총 인용의 부분집합): ${influential_citation_count}`
    );
  }
  const tooltip = tooltipParts.join("\n");

  const showDetail =
    !compact && (hasBreakdown || influential_citation_count !== null);

  return (
    <div className="inline-block text-right" title={tooltip}>
      <div
        className={`font-mono ${compact ? "text-xs" : "text-sm"} text-[var(--color-fg)]`}
      >
        {formatNumber(citation_count)}
      </div>
      {showDetail ? (
        <div className="mt-0.5 space-y-0 text-[10px] leading-tight text-[var(--color-fg-subtle)]">
          {hasBreakdown ? (
            <div className="whitespace-nowrap">
              저널 {j ?? 0} · Pre {p ?? 0}
              {breakdownGap > 0 ? <> · 기타 {breakdownGap}</> : null}
            </div>
          ) : null}
          {influential_citation_count !== null ? (
            <div className="whitespace-nowrap">
              (핵심 {influential_citation_count})
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Panels
// ---------------------------------------------------------------------------

function PapersPanel({ jobId, disabled }: { jobId: string; disabled: boolean }) {
  const q = useQuery({
    queryKey: ["papers", jobId],
    queryFn: () => papersApi.listForJob(jobId, 50),
    enabled: !disabled,
  });

  if (disabled)
    return <EmptyPanel text="분석이 완료되면 상위 논문이 표시됩니다." />;
  if (q.isLoading) return <LoadingPanel />;
  if (!q.data?.length) return <EmptyPanel text="논문 결과가 없습니다." />;

  return (
    <Card className="overflow-hidden">
      <table className="w-full text-sm">
        <thead className="border-b border-[var(--color-border)] bg-[var(--color-surface-2)] text-left text-xs uppercase tracking-wider text-[var(--color-fg-muted)]">
          <tr>
            <th className="px-5 py-2.5 font-medium">제목</th>
            <th className="px-5 py-2.5 font-medium">연도</th>
            <th className="px-5 py-2.5 font-medium">출판처</th>
            <th className="px-5 py-2.5 font-medium text-right">인용</th>
          </tr>
        </thead>
        <tbody>
          {q.data.map((p) => (
            <tr
              key={p.id}
              className="border-b border-[var(--color-border)] last:border-0"
            >
              <td className="px-5 py-2.5 align-top">
                <div className="flex items-start gap-2">
                  <div className="flex-1">
                    <div className="line-clamp-2 font-medium text-[var(--color-fg)]">
                      {p.title ?? "(제목 없음)"}
                    </div>
                    {p.doi ? (
                      <a
                        href={`https://doi.org/${p.doi}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="mt-0.5 inline-block font-mono text-[11px] text-[var(--color-fg-subtle)] hover:text-[var(--color-accent)]"
                      >
                        {p.doi}
                      </a>
                    ) : null}
                  </div>
                  <VenueBadge type={p.venue_type} />
                </div>
              </td>
              <td className="px-5 py-2.5 align-top text-[var(--color-fg-muted)]">
                {p.publication_year ?? "—"}
              </td>
              <td className="px-5 py-2.5 align-top text-[var(--color-fg-muted)]">
                {p.venue_name ?? "—"}
              </td>
              <td className="px-5 py-2.5 align-top text-right">
                <CitationCell paper={p} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

function AuthorsPanel({ jobId, disabled }: { jobId: string; disabled: boolean }) {
  const q = useQuery({
    queryKey: ["authors", jobId],
    queryFn: () => authorsApi.listForJob(jobId, 50),
    enabled: !disabled,
  });

  // Single-expand accordion: only one author's paper list is shown at a time.
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (disabled)
    return <EmptyPanel text="분석이 완료되면 상위 저자가 표시됩니다." />;
  if (q.isLoading) return <LoadingPanel />;
  if (!q.data?.length) return <EmptyPanel text="저자 결과가 없습니다." />;

  return (
    <Card className="overflow-hidden">
      <table className="w-full text-sm">
        <thead className="border-b border-[var(--color-border)] bg-[var(--color-surface-2)] text-left text-xs uppercase tracking-wider text-[var(--color-fg-muted)]">
          <tr>
            <th className="px-5 py-2.5 font-medium">이름 · 소속</th>
            <th className="px-5 py-2.5 font-medium text-right">논문 수</th>
            <th className="px-5 py-2.5 font-medium text-right">인용 수</th>
          </tr>
        </thead>
        <tbody>
          {q.data.map((a) => {
            const affLabel =
              a.latest_institution_name ??
              (a.latest_raw_affiliation
                ? a.latest_raw_affiliation.length > 80
                  ? a.latest_raw_affiliation.slice(0, 77) + "…"
                  : a.latest_raw_affiliation
                : null);
            const isExpanded = expandedId === a.id;
            return (
              <AuthorRow
                key={a.id}
                jobId={jobId}
                author={a}
                affLabel={affLabel}
                isExpanded={isExpanded}
                onToggle={() => setExpandedId(isExpanded ? null : a.id)}
              />
            );
          })}
        </tbody>
      </table>
    </Card>
  );
}

function AuthorRow({
  jobId,
  author,
  affLabel,
  isExpanded,
  onToggle,
}: {
  jobId: string;
  author: import("@/lib/types/api").AuthorListItem;
  affLabel: string | null;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  // Lazy-load papers only when expanded (and cache via React Query).
  const papersQ = useQuery({
    queryKey: ["author-papers", jobId, author.id],
    queryFn: () => papersApi.listForJob(jobId, 100, 0, author.id),
    enabled: isExpanded,
  });

  return (
    <>
      <tr
        className={
          "border-b border-[var(--color-border)] cursor-pointer transition-colors hover:bg-[var(--color-surface-2)] " +
          (isExpanded ? "bg-[var(--color-surface-2)]" : "")
        }
        onClick={onToggle}
        aria-expanded={isExpanded}
      >
        <td className="px-5 py-2.5">
          <div className="flex items-center gap-2">
            <span
              className={
                "inline-block text-[var(--color-fg-subtle)] transition-transform " +
                (isExpanded ? "rotate-90" : "")
              }
              aria-hidden
            >
              ▸
            </span>
            <div>
              <div className="font-medium text-[var(--color-fg)]">{author.name}</div>
              {affLabel ? (
                <div
                  className="mt-0.5 text-xs text-[var(--color-fg-muted)]"
                  title={author.latest_raw_affiliation ?? undefined}
                >
                  {affLabel}
                </div>
              ) : (
                <div className="mt-0.5 text-xs text-[var(--color-fg-subtle)]">
                  소속 정보 없음
                </div>
              )}
            </div>
          </div>
        </td>
        <td className="px-5 py-2.5 text-right font-mono align-top">
          {formatNumber(author.paper_count)}
        </td>
        <td className="px-5 py-2.5 text-right font-mono align-top">
          {formatNumber(author.citation_count)}
        </td>
      </tr>
      {isExpanded ? (
        <tr className="border-b border-[var(--color-border)] bg-[var(--color-bg)]">
          <td colSpan={3} className="px-5 py-3">
            {papersQ.isLoading ? (
              <div className="text-xs text-[var(--color-fg-muted)]">
                논문 불러오는 중…
              </div>
            ) : !papersQ.data?.length ? (
              <div className="text-xs text-[var(--color-fg-muted)]">
                관련 논문이 없습니다.
              </div>
            ) : (
              <table className="w-full text-xs">
                <thead className="text-[var(--color-fg-subtle)]">
                  <tr>
                    <th className="px-2 py-1 text-left font-medium">제목</th>
                    <th className="px-2 py-1 text-left font-medium">저널</th>
                    <th className="px-2 py-1 text-right font-medium w-16">연도</th>
                    <th className="px-2 py-1 text-right font-medium w-20">인용</th>
                  </tr>
                </thead>
                <tbody>
                  {papersQ.data.map((p) => (
                    <tr
                      key={p.id}
                      className="border-t border-[var(--color-border)]"
                    >
                      <td className="px-2 py-1.5 align-top text-[var(--color-fg)]">
                        <div className="flex items-start gap-1.5">
                          <div className="flex-1">
                            {p.title ?? "—"}
                            {p.doi ? (
                              <div className="mt-0.5 font-mono text-[10px] text-[var(--color-fg-subtle)]">
                                {p.doi}
                              </div>
                            ) : null}
                          </div>
                          <VenueBadge type={p.venue_type} size="xs" />
                        </div>
                      </td>
                      <td className="px-2 py-1.5 align-top text-[var(--color-fg-muted)]">
                        {p.venue_name ?? "—"}
                      </td>
                      <td className="px-2 py-1.5 align-top text-right font-mono text-[var(--color-fg-muted)]">
                        {p.publication_year ?? "—"}
                      </td>
                      <td className="px-2 py-1.5 align-top text-right">
                        <CitationCell paper={p} compact />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </td>
        </tr>
      ) : null}
    </>
  );
}

function KeywordsPanel({ jobId, disabled }: { jobId: string; disabled: boolean }) {
  const q = useQuery({
    queryKey: ["keywords", jobId],
    queryFn: () => keywordsApi.listForJob(jobId, 100),
    enabled: !disabled,
  });

  if (disabled)
    return <EmptyPanel text="분석이 완료되면 상위 키워드가 표시됩니다." />;
  if (q.isLoading) return <LoadingPanel />;
  if (!q.data?.length) return <EmptyPanel text="키워드 결과가 없습니다." />;

  return (
    <Card className="p-5">
      <div className="flex flex-wrap gap-2">
        {q.data.map((k) => (
          <span
            key={k.id}
            className="inline-flex items-center gap-1.5 rounded-full border border-[var(--color-border)] bg-[var(--color-surface-2)] px-3 py-1 text-xs"
          >
            <span className="font-medium text-[var(--color-fg)]">{k.display}</span>
            <span className="font-mono text-[10px] text-[var(--color-fg-subtle)]">
              {formatNumber(k.paper_count)}
            </span>
          </span>
        ))}
      </div>
    </Card>
  );
}

function GraphsPanel({ jobId, disabled }: { jobId: string; disabled: boolean }) {
  const q = useQuery({
    queryKey: ["graphs", jobId],
    queryFn: () => graphsApi.listForJob(jobId),
    enabled: !disabled,
  });

  if (disabled)
    return <EmptyPanel text="분석이 완료되면 그래프가 생성됩니다." />;
  if (q.isLoading) return <LoadingPanel />;
  if (!q.data?.length) return <EmptyPanel text="아직 그래프가 없습니다." />;

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
      {q.data.map((g) => (
        <Card key={g.id} className="overflow-hidden">
          <CardHeader>
            <CardTitle className="text-sm">{graphTypeLabel[g.graph_type]}</CardTitle>
          </CardHeader>
          <CardBody className="space-y-3">
            <div className="grid grid-cols-3 gap-2 text-center">
              <MiniStat label="노드" value={formatNumber(g.node_count)} />
              <MiniStat label="엣지" value={formatNumber(g.edge_count)} />
              <MiniStat label="군집" value={formatNumber(g.cluster_count)} />
            </div>
            <Link
              href={`/graphs/${g.id}`}
              className="inline-flex h-9 w-full items-center justify-center rounded-[var(--radius-md)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] text-sm font-medium text-[var(--color-fg)] hover:bg-[var(--color-surface-2)]"
            >
              시각화 열기
            </Link>
          </CardBody>
        </Card>
      ))}
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface-2)] py-2">
      <div className="text-[10px] uppercase tracking-wider text-[var(--color-fg-subtle)]">
        {label}
      </div>
      <div className="mt-0.5 font-mono text-sm text-[var(--color-fg)]">
        {value}
      </div>
    </div>
  );
}

function LoadingPanel() {
  return (
    <Card className="p-8 text-center text-sm text-[var(--color-fg-muted)]">
      불러오는 중…
    </Card>
  );
}

function EmptyPanel({ text }: { text: string }) {
  return (
    <Card className="p-8 text-center text-sm text-[var(--color-fg-muted)]">
      {text}
    </Card>
  );
}
