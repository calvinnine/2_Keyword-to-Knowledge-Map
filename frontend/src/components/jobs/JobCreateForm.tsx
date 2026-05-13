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
import type { Intent, ParsedQuery } from "@/lib/types/api";

type Mode = "keyword" | "query";

const intentLabel: Record<Intent, string> = {
  author_influence: "저자 영향력 분석",
  paper_centrality: "논문 중심성 분석",
  keyword_clusters: "키워드 군집 / 동향",
  general: "일반",
};

export function JobCreateForm() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("keyword");

  // shared params
  const [maxPapers, setMaxPapers] = useState(20_000);
  const [yearStart, setYearStart] = useState<string>("");
  const [yearEnd, setYearEnd] = useState<string>("");

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
      if (mode === "keyword") {
        return jobsApi.create({
          keyword,
          max_papers: maxPapers,
          year_start: yearStartNum,
          year_end: yearEndNum,
        });
      }
      return jobsApi.createFromQuery({
        query,
        max_papers: maxPapers,
        year_start: yearStartNum,
        year_end: yearEndNum,
      });
    },
    onSuccess: (job) => router.push(`/jobs/${job.id}`),
  });

  const canSubmit =
    mode === "keyword" ? keyword.trim().length > 0 : query.trim().length > 0;

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
