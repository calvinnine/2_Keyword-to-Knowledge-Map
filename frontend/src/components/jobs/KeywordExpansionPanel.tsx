"use client";

/**
 * KeywordExpansionPanel
 *
 * Shown after the user types a keyword and clicks "검색어 미리보기".
 * Displays LLM-generated candidate search terms as editable checkboxes.
 * The user can:
 *   - check / uncheck individual terms
 *   - add a custom term via the input at the bottom
 *   - click "분석 시작" to submit the confirmed set
 *
 * Props:
 *   expansion     – result from POST /jobs/expand-keywords
 *   onConfirm(terms) – called with the user-confirmed term list
 *   onBack        – go back to keyword input
 *   isPending     – job creation is in flight
 */

import { useState, useRef, KeyboardEvent } from "react";
import type { KeywordExpansionResult, TermInfo } from "@/lib/types/api";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";

/** Compact number formatter: 16639 → "16K", 1234567 → "1.2M". */
function formatCount(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1).replace(/\.0$/, "") + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1).replace(/\.0$/, "") + "K";
  return String(n);
}

/** Color/label for OA paper-count badge based on relative size. */
function oaBadgeStyle(count: number): { cls: string; title: string } {
  if (count >= 1_000)
    return {
      cls: "bg-[color-mix(in_oklab,var(--color-accent)_15%,transparent)] text-[var(--color-accent)] border-[color-mix(in_oklab,var(--color-accent)_35%,transparent)]",
      title: "OA에 충분히 색인된 검색어 — 권장",
    };
  if (count >= 100)
    return {
      cls: "bg-[var(--color-surface-2)] text-[var(--color-fg-muted)] border-[var(--color-border)]",
      title: "OA에 일부 색인됨 — 사용 가능",
    };
  return {
    cls: "bg-[var(--color-danger-soft)] text-[var(--color-danger)] border-[color-mix(in_oklab,var(--color-danger)_30%,transparent)]",
    title: "OA 매칭 매우 적음 — 결과가 빈약할 수 있음",
  };
}

function TermBadges({ info }: { info: TermInfo | undefined }) {
  if (!info) {
    // No info = OA call failed or no match — show a subtle "미검증" hint
    return (
      <span
        title="OA 검증 실패 또는 매칭 없음"
        className="rounded-full px-1.5 py-0.5 text-[10px] leading-none border border-dashed border-[var(--color-border)] text-[var(--color-fg-subtle)]"
      >
        미검증
      </span>
    );
  }
  const badges: React.ReactNode[] = [];
  if (typeof info.oa_works_count === "number") {
    const { cls, title } = oaBadgeStyle(info.oa_works_count);
    badges.push(
      <span
        key="oa"
        title={`${title} (${info.oa_works_count.toLocaleString()}건)`}
        className={`rounded-full px-1.5 py-0.5 text-[10px] leading-none border ${cls}`}
      >
        OA {formatCount(info.oa_works_count)}
      </span>
    );
  }
  if (info.source === "wikipedia") {
    badges.push(
      <span
        key="wiki"
        title="한국어 위키피디아의 언어간 링크로 추가된 후보"
        className="rounded-full px-1.5 py-0.5 text-[10px] leading-none border border-[var(--color-border)] bg-[var(--color-info-soft,var(--color-surface-2))] text-[var(--color-info,var(--color-fg-muted))]"
      >
        위키
      </span>
    );
  }
  return <>{badges}</>;
}

interface Props {
  expansion: KeywordExpansionResult;
  onConfirm: (terms: string[]) => void;
  onBack: () => void;
  isPending?: boolean;
}

export function KeywordExpansionPanel({
  expansion,
  onConfirm,
  onBack,
  isPending = false,
}: Props) {
  const { original_keyword, translated_keyword, search_terms, term_info } = expansion;
  const info: Record<string, TermInfo> = term_info ?? {};

  // All terms start checked
  const [checked, setChecked] = useState<Set<string>>(
    new Set(search_terms)
  );
  const [customInput, setCustomInput] = useState("");
  const [customTerms, setCustomTerms] = useState<string[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  const allTerms = [...search_terms, ...customTerms];
  const selected = allTerms.filter((t) => checked.has(t));

  function toggle(term: string) {
    setChecked((prev) => {
      const next = new Set(prev);
      if (next.has(term)) next.delete(term);
      else next.add(term);
      return next;
    });
  }

  function addCustom() {
    const val = customInput.trim();
    if (!val || checked.has(val) || customTerms.includes(val)) return;
    setCustomTerms((prev) => [...prev, val]);
    setChecked((prev) => new Set([...prev, val]));
    setCustomInput("");
    inputRef.current?.focus();
  }

  function onKey(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      addCustom();
    }
  }

  function removeCustom(term: string) {
    setCustomTerms((prev) => prev.filter((t) => t !== term));
    setChecked((prev) => {
      const next = new Set(prev);
      next.delete(term);
      return next;
    });
  }

  const canSubmit = selected.length > 0 && !isPending;

  return (
    <div className="space-y-5">
      {/* Header: show translation note if applicable */}
      <div className="rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface-2)] px-4 py-3 text-sm space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[var(--color-fg-muted)] text-xs">입력</span>
          <Badge variant="neutral">{original_keyword}</Badge>
          {translated_keyword && (
            <>
              <span className="text-[var(--color-fg-subtle)] text-xs">→ 번역</span>
              <Badge variant="accent">{translated_keyword}</Badge>
            </>
          )}
        </div>
        <p className="text-[11px] text-[var(--color-fg-subtle)]">
          아래 검색어로 OpenAlex · Semantic Scholar를 동시에 검색합니다.
          각 검색어 옆 배지는 OpenAlex 색인량(<span className="font-medium">OA 12K</span> = 1만 2천 건),
          한국어 위키피디아 언어간 링크로 추가된 후보는 <span className="font-medium">위키</span>로 표시됩니다.
          체크를 해제하거나 직접 추가할 수 있어요.
        </p>
      </div>

      {/* Term checkboxes */}
      <div className="space-y-2">
        <p className="text-xs font-medium text-[var(--color-fg-muted)] uppercase tracking-wide">
          검색어 후보 ({selected.length}/{allTerms.length} 선택됨)
        </p>
        <div className="space-y-1.5">
          {allTerms.map((term, idx) => {
            const isCustom = customTerms.includes(term);
            const isChecked = checked.has(term);
            return (
              <label
                key={term}
                className={[
                  "flex items-center gap-3 rounded-[var(--radius-md)] border px-3 py-2.5 cursor-pointer transition-colors select-none",
                  isChecked
                    ? "border-[var(--color-accent)] bg-[var(--color-accent-soft)]"
                    : "border-[var(--color-border)] bg-[var(--color-surface-2)] hover:border-[var(--color-border-strong)]",
                ].join(" ")}
              >
                <input
                  type="checkbox"
                  checked={isChecked}
                  onChange={() => toggle(term)}
                  className="accent-[var(--color-accent)] h-4 w-4 shrink-0"
                />
                <span
                  className={[
                    "flex-1 text-sm font-medium",
                    isChecked
                      ? "text-[var(--color-accent)]"
                      : "text-[var(--color-fg)]",
                  ].join(" ")}
                >
                  {term}
                </span>
                <span className="flex items-center gap-1.5">
                  {!isCustom && <TermBadges info={info[term]} />}
                  {idx === 0 && !isCustom && (
                    <span className="text-[10px] text-[var(--color-fg-subtle)] border border-[var(--color-border)] rounded px-1.5 py-0.5">
                      primary
                    </span>
                  )}
                  {isCustom && (
                    <>
                      <span className="text-[10px] text-[var(--color-fg-subtle)] border border-[var(--color-border)] rounded px-1.5 py-0.5">
                        직접 입력
                      </span>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.preventDefault();
                          removeCustom(term);
                        }}
                        className="text-[var(--color-fg-subtle)] hover:text-[var(--color-danger)] text-xs leading-none"
                        aria-label="삭제"
                      >
                        ✕
                      </button>
                    </>
                  )}
                </span>
              </label>
            );
          })}
        </div>
      </div>

      {/* Custom term input */}
      <div className="flex gap-2">
        <input
          ref={inputRef}
          type="text"
          value={customInput}
          onChange={(e) => setCustomInput(e.target.value)}
          onKeyDown={onKey}
          placeholder="검색어 직접 추가 (Enter)"
          className="flex-1 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface-2)] px-3 py-2 text-sm text-[var(--color-fg)] placeholder:text-[var(--color-fg-subtle)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)] focus:border-[var(--color-accent)] transition-colors"
        />
        <Button
          type="button"
          variant="ghost"
          onClick={addCustom}
          disabled={!customInput.trim()}
        >
          추가
        </Button>
      </div>

      {/* Actions */}
      <div className="flex items-center justify-between pt-1">
        <Button type="button" variant="ghost" onClick={onBack}>
          ← 키워드 수정
        </Button>
        <Button
          type="button"
          disabled={!canSubmit}
          onClick={() => onConfirm(selected)}
        >
          {isPending
            ? "생성 중…"
            : `${selected.length}개 검색어로 분석 시작`}
        </Button>
      </div>
    </div>
  );
}
