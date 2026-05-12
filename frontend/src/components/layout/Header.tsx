import Link from "next/link";
import { Container } from "./Container";

export function Header() {
  return (
    <header className="border-b border-[var(--color-border)] bg-[var(--color-surface)]/80 backdrop-blur">
      <Container className="flex h-14 items-center justify-between">
        <Link
          href="/"
          className="flex items-center gap-2 text-sm font-semibold tracking-tight text-[var(--color-fg)]"
        >
          <span
            aria-hidden
            className="inline-flex h-6 w-6 items-center justify-center rounded-[6px] bg-[var(--color-accent)] text-[var(--color-accent-fg)] text-[11px] font-bold"
          >
            K
          </span>
          K2KM
          <span className="ml-1 text-[var(--color-fg-subtle)] font-normal">
            · Keyword-to-Knowledge Map
          </span>
        </Link>

        <nav className="flex items-center gap-1 text-sm">
          <Link
            href="/"
            className="rounded-[var(--radius-md)] px-3 py-1.5 text-[var(--color-fg-muted)] hover:bg-[var(--color-surface-2)]"
          >
            분석 목록
          </Link>
          <Link
            href="/jobs/new"
            className="rounded-[var(--radius-md)] bg-[var(--color-accent)] px-3 py-1.5 font-medium text-[var(--color-accent-fg)] hover:bg-[var(--color-accent-hover)]"
          >
            새 분석
          </Link>
        </nav>
      </Container>
    </header>
  );
}
