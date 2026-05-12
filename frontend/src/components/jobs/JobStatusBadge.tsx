import { Badge } from "@/components/ui/Badge";
import type { JobStatus } from "@/lib/types/api";

const config: Record<
  JobStatus,
  { label: string; variant: "neutral" | "success" | "warning" | "danger" | "info" | "accent" }
> = {
  pending: { label: "대기", variant: "neutral" },
  collecting: { label: "수집 중", variant: "info" },
  collected: { label: "수집 완료", variant: "info" },
  processing: { label: "정규화 중", variant: "warning" },
  processed: { label: "정규화 완료", variant: "warning" },
  analyzing: { label: "분석 중", variant: "accent" },
  completed: { label: "완료", variant: "success" },
  failed: { label: "실패", variant: "danger" },
  cancelled: { label: "취소", variant: "neutral" },
};

export function JobStatusBadge({ status }: { status: JobStatus }) {
  const c = config[status] ?? { label: status, variant: "neutral" as const };
  return <Badge variant={c.variant}>{c.label}</Badge>;
}
