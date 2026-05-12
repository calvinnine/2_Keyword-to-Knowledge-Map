import Link from "next/link";
import { Container } from "@/components/layout/Container";
import { GraphViewerClient } from "@/components/graphs/GraphViewerClient";

export default async function GraphPage({
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
          graph/{id.slice(0, 8)}…
        </span>
      </div>
      <GraphViewerClient graphId={id} />
    </Container>
  );
}
