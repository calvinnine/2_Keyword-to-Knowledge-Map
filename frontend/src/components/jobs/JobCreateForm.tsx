"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { jobsApi, ApiError } from "@/lib/api/client";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Input, Label, Textarea } from "@/components/ui/Input";
import { Tabs } from "@/components/ui/Tabs";
import { Badge } from "@/components/ui/Badge";
import { KeywordExpansionPanel } from "@/components/jobs/KeywordExpansionPanel";
import { WOS_INDEX_OPTIONS } from "@/lib/types/api";
import type { Intent, KeywordExpansionResult, ParsedQuery, PublicationScope } from "@/lib/types/api";

type Mode = "keyword" | "query";
type Step = "input" | "expansion"; // two-step flow for keyword mode
type WosIndex = Exclude<PublicationScope, "all" | "wos">;

const intentLabel: Record<Intent, string> = {
  author_influence: "저자 영향력 분석",
  paper_centrality: "논문 중심성 분석",
  keyword_clusters: "키워드 군집 / 동향",
  general: "일반",
};

/** Convert selected indexes to the API scope string. */
function toScopeString(selected: WosIndex[]): string {
  if (selected.length === 0) return "all";
  return selected.join(",");
}

export function JobCreateForm() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("keyword");
  const [step, setStep] = useState<Step>("input");

  // shared params
  // Store as string so the user can transiently clear the field
  // (empty → defaults to 20000 on submit). Pure-number state caused
  // a "stuck 0" because Number("") || 0 collapses empty input to 0.
  const [maxPapers, setMaxPapers] = useState<string>("20000");
  const [yearStart, setYearStart] = useState<string>("");
  const [yearEnd, setYearEnd] = useState<string>("");
  const [selectedIndexes, setSelectedIndexes] = useState<WosIndex[]>([]);

  // keyword mode
  const [keyword, setKeyword] = useState("");
  const [expansion, setExpansion] = useState<KeywordExpansionResult | null>(null);

  // query mode
  const [query, setQuery] = useState("");
  const [parsed, setParsed] = useState<ParsedQuery | null>(null);

  const parseMutation = useMutation({
    mutationFn: () => jobsApi.parseQuery({ query }),
    onSuccess: (data) => setParsed(data),
    onError: () => setParsed(null),
  });

  // Step 1: expand keyword (or NL query → parsed keyword) → show panel
  const expandMutation = useMutation({
    mutationFn: async (): Promise<KeywordExpansionResult> => {
      if (mode === "keyword") {
        return jobsApi.expandKeywords(keyword);
      }
      // NL query mode: parse first, then expand the extracted keyword.
      // Re-parse here (even if blur already triggered it) so the user can
      // submit without waiting for the on-blur side effect.
      const parsedResult = await jobsApi.parseQuery({ query });
      setParsed(parsedResult);
      if (!parsedResult.keyword) {
        throw new Error("질문에서 키워드를 추출하지 못했습니다.");
      }
      return jobsApi.expandKeywords(parsedResult.keyword);
    },
    onSuccess: (data) => {
      setExpansion(data);
      setStep("expansion");
    },
  });

  // Step 2: create job with user-confirmed search terms.
  // For NL mode we go through /from-query so intent / original_query are
  // preserved on AnalysisJob.params (used to pick the default tab).
  const createMutation = useMutation({
    mutationFn: async (confirmedTerms?: string[]) => {
      const yearStartNum = yearStart ? Number(yearStart) : null;
      const yearEndNum = yearEnd ? Number(yearEnd) : null;
      // Empty / invalid input → fall back to default 20,000
      const parsedMax = Number(maxPapers);
      const maxPapersNum =
        Number.isFinite(parsedMax) && parsedMax >= 100 ? parsedMax : 20_000;
      const publication_scope = toScopeString(selectedIndexes);

      if (mode === "keyword") {
        return jobsApi.create({
          keyword,
          max_papers: maxPapersNum,
          year_start: yearStartNum,
          year_end: yearEndNum,
          publication_scope,
          search_terms: confirmedTerms,
        });
      }
      return jobsApi.createFromQuery({
        query,
        max_papers: maxPapersNum,
        year_start: yearStartNum,
        year_end: yearEndNum,
        publication_scope,
        search_terms: confirmedTerms,
      });
    },
    onSuccess: (job) => router.push(`/jobs/${job.id}`),
  });

  const canPreview = mode === "keyword"
    ? keyword.trim().length > 0
    : query.trim().length > 0;

  function toggleIndex(value: WosIndex) {
    setSelectedIndexes((prev) =>
      prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value]
    );
  }

  const isAllSelected = selectedIndexes.length === 0;

  // ── Shared parameter fields (year / scope / max papers) ──
  const sharedFields = (
    <>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <div>
          <Label htmlFor="max_papers" hint="100 – 50,000">
            최대 논문 수
          </Label>
          <Input
            id="max_papers"
            type="number"
            min={100}
            max={50_000}
            step={100}
            value={maxPapers}
            onChange={(e) => setMaxPapers(e.target.value)}
          />
          <p className="mt-1.5 text-[11px] leading-relaxed text-[var(--color-fg-subtle)]">
            OpenAlex 목표 수집량입니다. Semantic Scholar는 검색어당 최대 1,000건,
            두 소스를 합산 후 중복 제거합니다.
          </p>
        </div>
        <div>
          <Label htmlFor="year_start" hint="선택">
            시작 연도
          </Label>
          <Input
            id="year_start"
            type="number"
            min={1900}
            max={2100}
            placeholder="2018"
            value={yearStart}
            onChange={(e) => setYearStart(e.target.value)}
          />
        </div>
        <div>
          <Label htmlFor="year_end" hint="선택">
            종료 연도
          </Label>
          <Input
            id="year_end"
            type="number"
            min={1900}
            max={2100}
            placeholder="2025"
            value={yearEnd}
            onChange={(e) => setYearEnd(e.target.value)}
          />
        </div>
      </div>

      {/* Publication scope */}
      <div>
        <Label hint="Clarivate Web of Science 기준 · 복수 선택 가능">저널 분류 필터</Label>
        <div className="mt-2 flex flex-wrap gap-2">
          <label
            className={[
              "flex cursor-pointer items-center gap-2 rounded-[var(--radius-md)] border px-3 py-2 text-sm transition-colors select-none",
              isAllSelected
                ? "border-[var(--color-accent)] bg-[var(--color-accent-soft)] text-[var(--color-accent)]"
                : "border-[var(--color-border)] bg-[var(--color-surface-2)] text-[var(--color-fg)] hover:border-[var(--color-accent-soft)]",
            ].join(" ")}
          >
            <input
              type="checkbox"
              checked={isAllSelected}
              onChange={() => setSelectedIndexes([])}
              className="accent-[var(--color-accent)]"
            />
            <span className="font-medium">전체</span>
          </label>
          {WOS_INDEX_OPTIONS.map((opt) => {
            const checked = selectedIndexes.includes(opt.value);
            return (
              <label
                key={opt.value}
                className={[
                  "flex cursor-pointer items-center gap-2 rounded-[var(--radius-md)] border px-3 py-2 text-sm transition-colors select-none",
                  checked
                    ? "border-[var(--color-accent)] bg-[var(--color-accent-soft)] text-[var(--color-accent)]"
                    : "border-[var(--color-border)] bg-[var(--color-surface-2)] text-[var(--color-fg)] hover:border-[var(--color-accent-soft)]",
                ].join(" ")}
                title={opt.description}
              >
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => toggleIndex(opt.value)}
                  className="accent-[var(--color-accent)]"
                />
                <span className="font-medium">{opt.label}</span>
              </label>
            );
          })}
        </div>
        {selectedIndexes.length > 0 && (
          <p className="mt-1.5 text-xs text-[var(--color-fg-muted)]">
            선택된 인덱스 등재 저널 논문만 분석합니다. ISSN 매칭이 0건이면
            전체 논문으로 자동 폴백됩니다.
          </p>
        )}
      </div>
    </>
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle>새 분석</CardTitle>
        <CardDescription>
          {step === "expansion"
            ? "검색어 후보를 확인하고 분석을 시작하세요."
            : "키워드를 직접 입력하거나, 자연어 질문을 던지면 자동으로 키워드를 추출합니다."}
        </CardDescription>
        {step === "input" && (
          <div className="mt-3">
            <Tabs
              value={mode}
              onChange={(v) => {
                setMode(v as Mode);
                setExpansion(null);
                setStep("input");
              }}
              items={[
                { value: "keyword", label: "키워드 입력" },
                { value: "query", label: "자연어 질문" },
              ]}
            />
          </div>
        )}
      </CardHeader>

      <CardBody>
        {/* ── EXPANSION STEP (keyword mode only) ── */}
        {step === "expansion" && expansion ? (
          <KeywordExpansionPanel
            expansion={expansion}
            onConfirm={(terms) => createMutation.mutate(terms)}
            onBack={() => {
              setStep("input");
              setExpansion(null);
            }}
            isPending={createMutation.isPending}
          />
        ) : (
          <form
            className="space-y-5"
            onSubmit={(e) => {
              e.preventDefault();
              // Both modes go through the expansion preview step before job creation.
              // Keyword mode expands the keyword directly; query mode parses then expands.
              expandMutation.mutate();
            }}
          >
            {mode === "keyword" ? (
              <div>
                <Label htmlFor="keyword" hint="예: quantum computing">
                  키워드
                </Label>
                <Input
                  id="keyword"
                  value={keyword}
                  onChange={(e) => setKeyword(e.target.value)}
                  placeholder="foundation model"
                  autoFocus
                />
                <p className="mt-1.5 text-[11px] leading-relaxed text-[var(--color-fg-subtle)]">
                  한국어로 입력하면 영문으로 자동 번역됩니다. "검색어 미리보기"를
                  누르면 AI가 관련 검색어 후보를 생성하고, 확인 후 분석을 시작합니다.
                </p>
              </div>
            ) : (
              <div>
                <Label htmlFor="query" hint="예: quantum computing 분야에서 누가 잘해?">
                  자연어 질문
                </Label>
                <Textarea
                  id="query"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onBlur={() => {
                    if (query.trim()) parseMutation.mutate();
                  }}
                  placeholder="최근 5년 동안 digital twin 분야에서 어떤 논문이 중요해?"
                  autoFocus
                />
                <p className="mt-1.5 text-[11px] leading-relaxed text-[var(--color-fg-subtle)]">
                  질문에서 핵심 키워드를 자동 추출하며, 한국어면 영문으로 자동 번역합니다.
                </p>
                {parsed ? (
                  <div className="mt-3 flex flex-wrap items-center gap-2 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface-2)] px-3 py-2 text-xs">
                    <span className="text-[var(--color-fg-muted)]">추출 결과:</span>
                    <Badge variant="accent">{parsed.keyword || "(키워드 없음)"}</Badge>
                    <Badge variant="info">{intentLabel[parsed.intent]}</Badge>
                    {parsed.year_start && parsed.year_end ? (
                      <Badge variant="neutral">
                        {parsed.year_start} – {parsed.year_end}
                      </Badge>
                    ) : null}
                  </div>
                ) : null}
                {parseMutation.isError ? (
                  <p className="mt-2 text-xs text-[var(--color-danger)]">
                    키워드를 추출하지 못했습니다. 좀 더 구체적으로 입력해주세요.
                  </p>
                ) : null}
              </div>
            )}

            {sharedFields}

            {(createMutation.isError || expandMutation.isError) ? (
              <div className="rounded-[var(--radius-md)] border border-[var(--color-danger-soft)] bg-[var(--color-danger-soft)] px-3 py-2 text-xs text-[var(--color-danger)]">
                {createMutation.error instanceof ApiError
                  ? JSON.stringify(createMutation.error.detail)
                  : expandMutation.error instanceof ApiError
                  ? JSON.stringify(expandMutation.error.detail)
                  : String(createMutation.error ?? expandMutation.error)}
              </div>
            ) : null}

            <div className="flex items-center justify-end gap-2 pt-2">
              <Button
                type="button"
                variant="ghost"
                onClick={() => router.push("/")}
              >
                취소
              </Button>
              <Button
                type="submit"
                disabled={!canPreview || expandMutation.isPending || createMutation.isPending}
              >
                {expandMutation.isPending
                  ? "검색어 생성 중…"
                  : createMutation.isPending
                  ? "생성 중…"
                  : "검색어 미리보기 →"}
              </Button>
            </div>
          </form>
        )}
      </CardBody>
    </Card>
  );
}
