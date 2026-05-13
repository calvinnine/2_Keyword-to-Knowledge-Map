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
import { WOS_INDEX_OPTIONS } from "@/lib/types/api";
import type { Intent, ParsedQuery, PublicationScope } from "@/lib/types/api";

type Mode = "keyword" | "query";
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

  // shared params
  const [maxPapers, setMaxPapers] = useState(20_000);
  const [yearStart, setYearStart] = useState<string>("");
  const [yearEnd, setYearEnd] = useState<string>("");
  // Empty array = "전체" (all). One-or-more entries = specific WoS indexes.
  const [selectedIndexes, setSelectedIndexes] = useState<WosIndex[]>([]);

  // keyword mode
  const [keyword, setKeyword] = useState("");

  // query mode
  const [query, setQuery] = useState("");
  const [parsed, setParsed] = useState<ParsedQuery | null>(null);

  const parseMutation = useMutation({
    mutationFn: () => jobsApi.parseQuery({ query }),
    onSuccess: (data) => setParsed(data),
    onError: () => setParsed(null),
  });

  const createMutation = useMutation({
    mutationFn: async () => {
      const yearStartNum = yearStart ? Number(yearStart) : null;
      const yearEndNum = yearEnd ? Number(yearEnd) : null;
      const publication_scope = toScopeString(selectedIndexes);
      if (mode === "keyword") {
        return jobsApi.create({
          keyword,
          max_papers: maxPapers,
          year_start: yearStartNum,
          year_end: yearEndNum,
          publication_scope,
        });
      }
      return jobsApi.createFromQuery({
        query,
        max_papers: maxPapers,
        year_start: yearStartNum,
        year_end: yearEndNum,
        publication_scope,
      });
    },
    onSuccess: (job) => router.push(`/jobs/${job.id}`),
  });

  const canSubmit =
    mode === "keyword" ? keyword.trim().length > 0 : query.trim().length > 0;

  function toggleIndex(value: WosIndex) {
    setSelectedIndexes((prev) =>
      prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value]
    );
  }

  const isAllSelected = selectedIndexes.length === 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle>새 분석</CardTitle>
        <CardDescription>
          키워드를 직접 입력하거나, 자연어 질문을 던지면 자동으로 키워드를 추출합니다.
        </CardDescription>
        <div className="mt-3">
          <Tabs
            value={mode}
            onChange={(v) => setMode(v as Mode)}
            items={[
              { value: "keyword", label: "키워드 입력" },
              { value: "query", label: "자연어 질문" },
            ]}
          />
        </div>
      </CardHeader>
      <CardBody>
        <form
          className="space-y-5"
          onSubmit={(e) => {
            e.preventDefault();
            createMutation.mutate();
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
                한국어로 입력하면 학술 DB 검색에 적합한 영문 키워드로 자동 번역됩니다
                (예: “양자컴퓨팅” → “Quantum Computing”). OpenAlex·Semantic Scholar는
                대부분 영문 메타데이터로 색인되어 있어 영문 변환이 검색 정확도를 크게 높입니다.
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
                질문에서 핵심 키워드를 자동 추출하며, 추출된 키워드가 한국어면 영문으로
                자동 번역해 검색합니다 (학술 DB는 대부분 영문 색인).
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
                onChange={(e) => setMaxPapers(Number(e.target.value) || 0)}
              />
              <p className="mt-1.5 text-[11px] leading-relaxed text-[var(--color-fg-subtle)]">
                입력한 수치는 OpenAlex(최대 50,000건)의 목표값으로 사용됩니다.
                Semantic Scholar는 API 자체 한계로 키워드당 최대 1,000건까지만 보조 수집되며,
                두 소스를 합쳐 DOI·제목 기준 중복 제거 후 분석에 투입됩니다.
                따라서 1,000을 초과하는 값을 넣어도 안전하지만, 매우 일반적인 키워드는
                중복 비율이 높아 실제 정규화 논문 수가 목표치보다 적을 수 있습니다.
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

          {/* Publication scope — checkbox multi-select */}
          <div>
            <Label hint="Clarivate Web of Science 기준 · 복수 선택 가능">저널 분류 필터</Label>
            <div className="mt-2 flex flex-wrap gap-2">
              {/* 전체 — deselects all indexes */}
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

              {/* Individual WoS index checkboxes */}
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
                선택된 인덱스에 등재된 저널 논문만 분석에 포함됩니다.
                ISSN 매칭이 0건이면 전체 논문으로 자동 폴백됩니다(국문 저널·프리프린트가 다수일 때).
              </p>
            )}
          </div>

          {createMutation.isError ? (
            <div className="rounded-[var(--radius-md)] border border-[var(--color-danger-soft)] bg-[var(--color-danger-soft)] px-3 py-2 text-xs text-[var(--color-danger)]">
              {createMutation.error instanceof ApiError
                ? JSON.stringify(createMutation.error.detail)
                : String(createMutation.error)}
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
              disabled={!canSubmit || createMutation.isPending}
            >
              {createMutation.isPending ? "생성 중…" : "분석 시작"}
            </Button>
          </div>
        </form>
      </CardBody>
    </Card>
  );
}
