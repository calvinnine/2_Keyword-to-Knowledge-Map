import Link from "next/link";
import { Container } from "@/components/layout/Container";
import { JobCreateForm } from "@/components/jobs/JobCreateForm";

export default function NewJobPage() {
  return (
    <Container className="max-w-3xl space-y-6">
      <div className="flex items-center gap-2 text-sm text-[var(--color-fg-muted)]">
        <Link href="/" className="hover:text-[var(--color-fg)]">
          분석 목록
        </Link>
        <span>/</span>
        <span className="text-[var(--color-fg)]">새 분석</span>
      </div>
      <JobCreateForm />
    </Container>
  );
}
