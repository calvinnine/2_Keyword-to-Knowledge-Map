"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { jobsApi } from "@/lib/api/client";
import { Card } from "@/components/ui/Card";
import { JobStatusBadge } from "./JobStatusBadge";
import { formatDateTime, formatNumber } from "@/lib/utils";

export function JobList() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["jobs"],
    queryFn: () => jobsApi.list({ limit: 50 }),
    refetchInterval: 5_000,
  });

  if (isLoading) {
    return (
      <Card className="p-8 text-center text-sm text-[var(--color-fg-muted)]">
        분석 목록을 불러오는 중…
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="p-6 text-sm text-[var(--color-danger)]">
        목록을 불러오지 못했습니다. 백엔드 서버가 실행 중인지 확인하세요.
        <div className="mt-2 font-mono text-xs opacity-70">
          {error instanceof Error ? error.message : String(error)}
        </div>
      </Card>
    );
  }

  if (!data || data.length === 0) {
    return (
      <Card className="p-10 text-center">
        <p className="text-sm text-[var(--color-fg-muted)]">
          아직 생성된 분석이 없습니다.
        </p>
        <Link
          href="/jobs/new"
          className="mt-4 inline-flex h-9 items-center rounded-[var(--radius-md)] bg-[var(--color-accent)] px-4 text-sm font-medium text-[var(--color-accent-fg)] hover:bg-[var(--color-accent-hover)]"
        >
          첫 분석 시작하기
        </Link>
      </Card>
    );
  }

  return (
    <Card className="overflow-hidden">
      <table className="w-full text-sm">
        <thead className="border-b border-[var(--color-border)] bg-[var(--color-surface-2)] text-[var(--color-fg-muted)]">
          <tr className="text-left">
            <th className="px-5 py-3 font-medium">키워드</th>
            <th className="px-5 py-3 font-medium">상태</th>
            <th className="px-5 py-3 font-medium text-right">수집 / 정규화</th>
            <th className="px-5 py-3 font-medium">생성 시각</th>
          </tr>
        </thead>
        <tbody>
          {data.map((job) => (
            <tr
              key={job.id}
              className="border-b border-[var(--color-border)] last:border-0 hover:bg-[var(--color-surface-2)]"
            >
              <td className="px-5 py-3">
                <Link
                  href={`/jobs/${job.id}`}
                  className="font-medium text-[var(--color-fg)] hover:text-[var(--color-accent)]"
                >
                  {job.keyword}
                </Link>
              </td>
              <td className="px-5 py-3">
                <JobStatusBadge status={job.status} />
              </td>
              <td className="px-5 py-3 text-right font-mono text-xs text-[var(--color-fg-muted)]">
                {formatNumber(job.papers_collected)} /{" "}
                {formatNumber(job.papers_processed)}
              </td>
              <td className="px-5 py-3 text-[var(--color-fg-muted)]">
                {formatDateTime(job.created_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}
