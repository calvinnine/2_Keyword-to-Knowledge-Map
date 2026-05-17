import type { JobStatus } from "@/lib/types/api";

/**
 * Visual stepper showing pipeline progress for an analysis job.
 *
 * Stages map to backend JobStatus values:
 *   1. 대기 (pending)
 *   2. 수집 (collecting → collected)
 *   3. 정규화 (processing → processed)
 *   4. 분석 (analyzing)
 *   5. 완료 (completed)
 *
 * Visual rules:
 *   - completed steps   → solid accent dot, accent connector
 *   - current step      → pulsing accent ring (animate-ping overlay)
 *   - upcoming steps    → muted dot, muted connector
 *   - failed/cancelled  → danger styling on the current step, rest stays muted
 */

type StageKey = "pending" | "collect" | "process" | "analyze" | "complete";

const STAGES: { key: StageKey; label: string }[] = [
  { key: "pending",  label: "대기" },
  { key: "collect",  label: "수집" },
  { key: "process",  label: "정규화" },
  { key: "analyze",  label: "분석" },
  { key: "complete", label: "완료" },
];

// For each backend status, which stage is "current" (pulsing)?
const STATUS_TO_CURRENT_INDEX: Record<JobStatus, number> = {
  pending:    0,
  collecting: 1,
  collected:  1,
  processing: 2,
  processed:  2,
  analyzing:  3,
  completed:  4,
  failed:    -1,
  cancelled: -1,
};

/**
 * Human-readable description of what's happening RIGHT NOW.
 * Shown below the stepper as a single line.
 */
function getStatusDescription(
  status: JobStatus,
  papers_collected: number,
  papers_processed: number,
  search_terms: string[],
): string {
  switch (status) {
    case "pending":
      return "분석 요청이 대기 중입니다. 곧 수집을 시작합니다.";
    case "collecting": {
      const termsNote =
        search_terms.length > 1
          ? ` (${search_terms.length}개 검색어 병렬 검색 중)`
          : "";
      return papers_collected > 0
        ? `OpenAlex · Semantic Scholar에서 논문 수집 중${termsNote} — ${papers_collected.toLocaleString()}편 확보`
        : `OpenAlex · Semantic Scholar에서 논문 수집 중${termsNote}…`;
    }
    case "collected":
      return `${papers_collected.toLocaleString()}편 수집 완료 — 정규화 준비 중`;
    case "processing":
      return "중복 논문 제거 및 메타데이터 정규화 중…";
    case "processed":
      return `${papers_processed.toLocaleString()}편 정규화 완료 — 인용·키워드 분석 준비 중`;
    case "analyzing":
      return "인용 네트워크 · 키워드 그래프 · 저자 점수 계산 중…";
    case "completed":
      return "";   // 완료는 별도 메시지 없음 (stepper 자체가 전부 켜짐)
    case "failed":
      return "";   // 실패는 별도 danger 메시지로 처리
    case "cancelled":
      return "";
  }
}

/**
 * When a job has failed/cancelled, JobStatus alone doesn't tell us which
 * stage it died in. Infer from progress counters.
 */
function inferFailureIndex(papers_collected: number, papers_processed: number): number {
  if (papers_processed > 0) return 3;
  if (papers_collected > 0) return 2;
  return 1;
}

export function JobProgressStepper({
  status,
  papers_collected = 0,
  papers_processed = 0,
  search_terms = [],
}: {
  status: JobStatus;
  papers_collected?: number;
  papers_processed?: number;
  /** Expanded search terms stored in job.params.search_terms */
  search_terms?: string[];
}) {
  const isFailed = status === "failed" || status === "cancelled";
  const currentIdx = isFailed
    ? inferFailureIndex(papers_collected, papers_processed)
    : STATUS_TO_CURRENT_INDEX[status];

  const statusDesc = isFailed
    ? ""
    : getStatusDescription(status, papers_collected, papers_processed, search_terms);

  const isInProgress =
    !isFailed && status !== "completed" && status !== "pending";

  return (
    <div className="px-5 py-4 border-b border-[var(--color-border)] space-y-3">
      {/* ── Stepper dots ── */}
      <div className="flex items-center justify-between">
        {STAGES.map((stage, idx) => {
          const isLast = idx === STAGES.length - 1;
          const isDone     = status === "completed" ? true : idx < currentIdx;
          const isCurrent  = !isFailed && idx === currentIdx;
          const isFailedHere = isFailed && idx === currentIdx;

          return (
            <div key={stage.key} className="flex flex-1 items-center last:flex-none">
              <div className="flex flex-col items-center gap-1.5">
                <StepDot done={isDone} current={isCurrent} failed={isFailedHere} />
                <span
                  className={
                    "text-[11px] font-medium whitespace-nowrap " +
                    (isCurrent
                      ? "text-[var(--color-accent)]"
                      : isDone
                      ? "text-[var(--color-fg)]"
                      : isFailedHere
                      ? "text-[var(--color-danger)]"
                      : "text-[var(--color-fg-subtle)]")
                  }
                >
                  {stage.label}
                </span>
              </div>
              {!isLast ? (
                <div className="mx-2 -mt-5 h-px flex-1 relative">
                  <div className="absolute inset-0 bg-[var(--color-border)]" />
                  {isDone ? (
                    <div className="absolute inset-0 bg-[var(--color-accent)]" />
                  ) : null}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>

      {/* ── Status description line ── */}
      {isFailed ? (
        <p className="text-center text-xs text-[var(--color-danger)]">
          {status === "failed" ? "파이프라인이 실패했습니다." : "취소되었습니다."}
        </p>
      ) : statusDesc ? (
        <p className="text-center text-xs text-[var(--color-fg-muted)]">
          {statusDesc}
        </p>
      ) : null}

      {/* ── Expanded search terms (shown during collection) ── */}
      {(status === "collecting" || status === "collected" || status === "pending") &&
        search_terms.length > 1 ? (
        <div className="flex flex-wrap justify-center gap-1.5 pt-0.5">
          {search_terms.map((term, i) => (
            <span
              key={term}
              className={[
                "rounded-full px-2.5 py-0.5 text-[11px] font-medium border",
                i === 0
                  ? "border-[var(--color-accent)] text-[var(--color-accent)] bg-[var(--color-accent-soft)]"
                  : "border-[var(--color-border)] text-[var(--color-fg-muted)] bg-[var(--color-surface-2)]",
              ].join(" ")}
            >
              {term}
            </span>
          ))}
        </div>
      ) : null}

      {/* ── Auto-refresh note (in-progress only) ── */}
      {isInProgress && (
        <p className="text-center text-[10px] text-[var(--color-fg-subtle)]">
          자동으로 새로고침됩니다
        </p>
      )}
    </div>
  );
}

function StepDot({
  done,
  current,
  failed,
}: {
  done: boolean;
  current: boolean;
  failed: boolean;
}) {
  if (failed) {
    return (
      <div className="relative h-3 w-3">
        <span className="absolute inset-0 rounded-full bg-[var(--color-danger)]" />
      </div>
    );
  }
  if (current) {
    return (
      <div className="relative h-3 w-3">
        <span
          aria-hidden
          className="absolute inset-0 rounded-full bg-[var(--color-accent)] opacity-60 animate-ping"
        />
        <span className="absolute inset-0 rounded-full bg-[var(--color-accent)] ring-2 ring-[var(--color-accent-soft)]" />
      </div>
    );
  }
  if (done) {
    return <div className="h-3 w-3 rounded-full bg-[var(--color-accent)]" />;
  }
  return (
    <div className="h-3 w-3 rounded-full border border-[var(--color-border-strong)] bg-[var(--color-surface)]" />
  );
}
