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
  { key: "pending", label: "대기" },
  { key: "collect", label: "수집" },
  { key: "process", label: "정규화" },
  { key: "analyze", label: "분석" },
  { key: "complete", label: "완료" },
];

// For each backend status, which stage is "current" (pulsing)?
// All earlier stages become "completed"; later stages stay "upcoming".
const STATUS_TO_CURRENT_INDEX: Record<JobStatus, number> = {
  pending: 0,
  collecting: 1,
  collected: 1,   // collection just finished but next step not yet picked up
  processing: 2,
  processed: 2,
  analyzing: 3,
  completed: 4,
  failed: -1,     // handled separately, see inferFailureIndex
  cancelled: -1,
};

/**
 * When a job has failed/cancelled, JobStatus alone doesn't tell us which
 * stage it died in. Infer from progress counters: if some papers got
 * processed, failure was during analyze; if some collected, failure was
 * during normalisation; otherwise it died at collection (or before).
 */
function inferFailureIndex(papers_collected: number, papers_processed: number): number {
  if (papers_processed > 0) return 3; // 분석 단계
  if (papers_collected > 0) return 2; // 정규화 단계
  return 1; // 수집 단계 (or earlier — but 대기 failure is unusual)
}

export function JobProgressStepper({
  status,
  papers_collected = 0,
  papers_processed = 0,
}: {
  status: JobStatus;
  papers_collected?: number;
  papers_processed?: number;
}) {
  const isFailed = status === "failed" || status === "cancelled";
  const currentIdx = isFailed
    ? inferFailureIndex(papers_collected, papers_processed)
    : STATUS_TO_CURRENT_INDEX[status];

  return (
    <div className="px-5 py-4 border-b border-[var(--color-border)]">
      <div className="flex items-center justify-between">
        {STAGES.map((stage, idx) => {
          const isLast = idx === STAGES.length - 1;
          // State of THIS step:
          //   - completed (done): index strictly before currentIdx, OR status==completed
          //   - current (pulsing): exactly at currentIdx, not failed
          //   - failed here: at currentIdx when status is failed/cancelled
          //   - upcoming: index after currentIdx
          const isDone =
            status === "completed" ? true : idx < currentIdx;
          const isCurrent = !isFailed && idx === currentIdx;
          const isFailedHere = isFailed && idx === currentIdx;

          return (
            <div key={stage.key} className="flex flex-1 items-center last:flex-none">
              {/* Dot + label */}
              <div className="flex flex-col items-center gap-1.5">
                <StepDot
                  done={isDone}
                  current={isCurrent}
                  failed={isFailedHere}
                />
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
              {/* Connector line (not after last item) */}
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
      {isFailed ? (
        <p className="mt-3 text-center text-xs text-[var(--color-danger)]">
          {status === "failed" ? "파이프라인이 실패했습니다." : "취소되었습니다."}
        </p>
      ) : status !== "completed" ? (
        <p className="mt-3 text-center text-xs text-[var(--color-fg-muted)]">
          진행 중입니다. 자동 새로고침되며, 단계가 바뀔 때마다 표시됩니다.
        </p>
      ) : null}
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
        {/* Pulsing halo */}
        <span
          aria-hidden
          className="absolute inset-0 rounded-full bg-[var(--color-accent)] opacity-60 animate-ping"
        />
        {/* Solid core */}
        <span className="absolute inset-0 rounded-full bg-[var(--color-accent)] ring-2 ring-[var(--color-accent-soft)]" />
      </div>
    );
  }
  if (done) {
    return (
      <div className="h-3 w-3 rounded-full bg-[var(--color-accent)]" />
    );
  }
  // upcoming
  return (
    <div className="h-3 w-3 rounded-full border border-[var(--color-border-strong)] bg-[var(--color-surface)]" />
  );
}
