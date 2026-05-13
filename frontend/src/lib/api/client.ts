/**
 * K2KM backend API client.
 *
 * Configurable base URL via NEXT_PUBLIC_API_BASE (default: http://localhost:8000).
 * Throws ApiError on non-2xx responses.
 */

import type {
  AuthorListItem,
  AuthorMatrixItem,
  AuthorRead,
  AuthorRecommendation,
  GraphResultDetail,
  GraphResultRead,
  JobCreatePayload,
  JobFromQueryPayload,
  JobListItem,
  JobRead,
  JobStatus,
  KeywordRead,
  NtisOverlayTriggerResponse,
  NtisOverview,
  PaperListItem,
  PaperRead,
  ParsedQuery,
} from "@/lib/types/api";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export class ApiError extends Error {
  readonly status: number;
  readonly detail: unknown;

  constructor(status: number, detail: unknown, message?: string) {
    super(message ?? `API error ${status}`);
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    let detail: unknown = null;
    try {
      detail = await res.json();
    } catch {
      detail = await res.text();
    }
    throw new ApiError(res.status, detail);
  }
  // Some endpoints return 204; guard.
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// ---------------------------------------------------------------------------
// Jobs
// ---------------------------------------------------------------------------

export const jobsApi = {
  list: (params?: { status?: JobStatus; limit?: number; offset?: number }) => {
    const q = new URLSearchParams();
    if (params?.status) q.set("status", params.status);
    if (params?.limit) q.set("limit", String(params.limit));
    if (params?.offset) q.set("offset", String(params.offset));
    const qs = q.toString();
    return request<JobListItem[]>(`/api/v1/jobs${qs ? `?${qs}` : ""}`);
  },

  get: (jobId: string) => request<JobRead>(`/api/v1/jobs/${jobId}`),

  create: (payload: JobCreatePayload) =>
    request<JobRead>(`/api/v1/jobs`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  createFromQuery: (payload: JobFromQueryPayload) =>
    request<JobRead>(`/api/v1/jobs/from-query`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  parseQuery: (payload: JobFromQueryPayload) =>
    request<ParsedQuery>(`/api/v1/jobs/parse-query`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  cancel: (jobId: string) =>
    request<JobRead>(`/api/v1/jobs/${jobId}/cancel`, { method: "POST" }),
};

// ---------------------------------------------------------------------------
// Papers / Authors / Keywords
// ---------------------------------------------------------------------------

export const papersApi = {
  listForJob: (jobId: string, limit = 100, offset = 0) =>
    request<PaperListItem[]>(
      `/api/v1/jobs/${jobId}/papers?limit=${limit}&offset=${offset}`
    ),
  get: (paperId: string) => request<PaperRead>(`/api/v1/papers/${paperId}`),
};

export const authorsApi = {
  listForJob: (jobId: string, limit = 100, offset = 0) =>
    request<AuthorListItem[]>(
      `/api/v1/jobs/${jobId}/authors?limit=${limit}&offset=${offset}`
    ),
  get: (authorId: string) => request<AuthorRead>(`/api/v1/authors/${authorId}`),
  recommendations: (jobId: string, role?: string, limit = 50) => {
    const q = new URLSearchParams({ limit: String(limit) });
    if (role) q.set("role", role);
    return request<AuthorRecommendation[]>(
      `/api/v1/jobs/${jobId}/author-recommendations?${q}`
    );
  },
};

export const keywordsApi = {
  listForJob: (jobId: string, limit = 100, offset = 0) =>
    request<KeywordRead[]>(
      `/api/v1/jobs/${jobId}/keywords?limit=${limit}&offset=${offset}`
    ),
};

// ---------------------------------------------------------------------------
// Graphs
// ---------------------------------------------------------------------------

export const graphsApi = {
  listForJob: (jobId: string) =>
    request<GraphResultRead[]>(`/api/v1/jobs/${jobId}/graphs`),
  get: (
    graphId: string,
    opts?: { nodeLimit?: number; edgeLimit?: number }
  ) => {
    const q = new URLSearchParams();
    if (opts?.nodeLimit !== undefined)
      q.set("node_limit", String(opts.nodeLimit));
    if (opts?.edgeLimit !== undefined)
      q.set("edge_limit", String(opts.edgeLimit));
    const qs = q.toString();
    return request<GraphResultDetail>(
      `/api/v1/graphs/${graphId}${qs ? `?${qs}` : ""}`
    );
  },
};

export const healthApi = {
  check: () =>
    request<{ status: string; env: string }>(`/api/v1/health`),
};

// ---------------------------------------------------------------------------
// NTIS
// ---------------------------------------------------------------------------

export const ntisApi = {
  triggerOverlay: (jobId: string) =>
    request<NtisOverlayTriggerResponse>(`/api/v1/jobs/${jobId}/ntis-overlay`, {
      method: "POST",
    }),

  getOverview: (jobId: string) =>
    request<NtisOverview>(`/api/v1/jobs/${jobId}/ntis`),

  getMatrix: (jobId: string, limit = 200) =>
    request<AuthorMatrixItem[]>(
      `/api/v1/jobs/${jobId}/ntis/matrix?limit=${limit}`
    ),
};
