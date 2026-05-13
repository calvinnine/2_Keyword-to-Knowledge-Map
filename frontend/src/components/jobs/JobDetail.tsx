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
          </div>
          <div className="text-right text-xs text-[var(--color-fg-muted)]">
            <div>생성 {formatDateTime(j.created_at)}</div>
            {j.completed_at ? (
              <div>완료 {formatDateTime(j.completed_at)}</div>
            ) : null}
          </div>
        </CardHeader>
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
          <AuthorRecommendations jobId={jobId} />
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
              </td>
              <td className="px-5 py-2.5 align-top text-[var(--color-fg-muted)]">
                {p.publication_year ?? "—"}
              </td>
              <td className="px-5 py-2.5 align-top text-[var(--color-fg-muted)]">
                {p.venue_name ?? "—"}
              </td>
              <td className="px-5 py-2.5 align-top text-right font-mono text-[var(--color-fg)]">
                {formatNumber(p.citation_count)}
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

  if (disabled)
    return <EmptyPanel text="분석이 완료되면 상위 저자가 표시됩니다." />;
  if (q.isLoading) return <LoadingPanel />;
  if (!q.data?.length) return <EmptyPanel text="저자 결과가 없습니다." />;

  return (
    <Card className="overflow-hidden">
      <table className="w-full text-sm">
        <thead className="border-b border-[var(--color-border)] bg-[var(--color-surface-2)] text-left text-xs uppercase tracking-wider text-[var(--color-fg-muted)]">
          <tr>
            <th className="px-5 py-2.5 font-medium">이름</th>
            <th className="px-5 py-2.5 font-medium text-right">논문 수</th>
            <th className="px-5 py-2.5 font-medium text-right">인용 수</th>
          </tr>
        </thead>
        <tbody>
          {q.data.map((a) => (
            <tr
              key={a.id}
              className="border-b border-[var(--color-border)] last:border-0"
            >
              <td className="px-5 py-2.5 font-medium text-[var(--color-fg)]">
                {a.name}
              </td>
              <td className="px-5 py-2.5 text-right font-mono">
                {formatNumber(a.paper_count)}
              </td>
              <td className="px-5 py-2.5 text-right font-mono">
                {formatNumber(a.citation_count)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
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
