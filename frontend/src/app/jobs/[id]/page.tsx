import Link from "next/link";
import { Container } from "@/components/layout/Container";
import { JobDetail } from "@/components/jobs/JobDetail";

export default async function JobDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <Container className="space-y-6">
      <div className="flex items-center gap-2 text-sm text-[var(--color-fg-muted)]">
        <Link href="/" className="hover:text-[var(--color-fg)]">
          분석 목록
        </Link>
        <span>/</span>
        <span className="font-mono text-xs text-[var(--color-fg)]">
          {id.slice(0, 8)}…
        </span>
      </div>
      <JobDetail jobId={id} />
    </Container>
  );
}
