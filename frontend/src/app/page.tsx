import Link from "next/link";
import { Container } from "@/components/layout/Container";
import { JobList } from "@/components/jobs/JobList";

export default function HomePage() {
  return (
    <Container className="space-y-6">
      <header className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-[var(--color-fg)]">
            분석 목록
          </h1>
          <p className="mt-1 text-sm text-[var(--color-fg-muted)]">
            키워드 기반으로 수집·정규화·그래프 분석을 수행한 분석 자산입니다.
          </p>
        </div>
        <Link
          href="/jobs/new"
          className="inline-flex h-10 items-center rounded-[var(--radius-md)] bg-[var(--color-accent)] px-4 text-sm font-medium text-[var(--color-accent-fg)] hover:bg-[var(--color-accent-hover)]"
        >
          새 분석
        </Link>
      </header>

      <JobList />
    </Container>
  );
}
