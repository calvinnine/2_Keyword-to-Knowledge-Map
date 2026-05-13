// Type definitions mirroring backend Pydantic schemas.
// Keep in sync with backend/app/schemas/*.

export type JobStatus =
  | "pending"
  | "collecting"
  | "collected"
  | "processing"
  | "processed"
  | "analyzing"
  | "completed"
  | "failed"
  | "cancelled";

export type GraphType = "paper" | "author" | "keyword";

export type Intent =
  | "author_influence"
  | "paper_centrality"
  | "keyword_clusters"
  | "general";

export interface JobListItem {
  id: string;
  keyword: string;
  status: JobStatus;
  max_papers: number;
  papers_collected: number;
  papers_processed: number;
  created_at: string;
  updated_at: string;
}

export type PublicationScope = "all" | "wos" | "scie" | "ssci" | "ahci" | "esci";

/** Selectable WoS index checkboxes (excludes "all" / "wos" meta-options). */
export const WOS_INDEX_OPTIONS: {
  value: Exclude<PublicationScope, "all" | "wos">;
  label: string;
  description: string;
}[] = [
  { value: "scie", label: "SCIE", description: "자연과학 핵심 저널" },
  { value: "ssci", label: "SSCI", description: "사회과학 핵심 저널" },
  { value: "ahci", label: "AHCI", description: "인문학 핵심 저널" },
  { value: "esci", label: "ESCI", description: "신진 학술지" },
];

/** All options including meta-values, used for display labels. */
export const PUBLICATION_SCOPE_OPTIONS: {
  value: PublicationScope;
  label: string;
  description: string;
}[] = [
  { value: "all",  label: "전체",     description: "수집된 모든 논문" },
  { value: "wos",  label: "WoS 전체", description: "SCIE + SSCI + AHCI + ESCI 등재 저널" },
  ...WOS_INDEX_OPTIONS,
];

export interface JobRead extends JobListItem {
  year_start: number | null;
  year_end: number | null;
  publication_types: string[] | null;
  publication_scope: PublicationScope;
  error_message: string | null;
  completed_at: string | null;
  params: Record<string, unknown> | null;
  insight: string | null;
}

export interface JobCreatePayload {
  keyword: string;
  max_papers?: number;
  year_start?: number | null;
  year_end?: number | null;
  publication_types?: string[] | null;
  publication_scope?: string;
}

export interface JobFromQueryPayload {
  query: string;
  max_papers?: number;
  year_start?: number | null;
  year_end?: number | null;
  publication_types?: string[] | null;
  publication_scope?: string;
}

export interface ParsedQuery {
  keyword: string;
  intent: Intent;
  year_start: number | null;
  year_end: number | null;
  raw_query: string;
}

export interface PaperListItem {
  id: string;
  doi: string | null;
  title: string | null;
  publication_year: number | null;
  venue_name: string | null;
  venue_type: string | null;
  citation_count: number;
  openalex_id: string | null;
}

export interface PaperRead extends PaperListItem {
  abstract: string | null;
  publication_date: string | null;
  semantic_scholar_id: string | null;
  pubmed_id: string | null;
  arxiv_id: string | null;
  is_open_access: boolean | null;
  language: string | null;
  fields_of_study: string[] | null;
  sci_classification: string | null;
  reference_count: number;
  created_at: string;
  updated_at: string;
}

export interface AuthorListItem {
  id: string;
  name: string;
  openalex_id: string | null;
  paper_count: number;
  citation_count: number;
}

export interface AuthorRead extends AuthorListItem {
  semantic_scholar_id: string | null;
  orcid: string | null;
  primary_country_code: string | null;
  primary_country_name: string | null;
  created_at: string;
}

export interface KeywordRead {
  id: string;
  normalized: string;
  display: string;
  paper_count: number;
  created_at: string;
}

export const ROLE_LABELS = [
  "Core Influencer",
  "Bridge Researcher",
  "Productive Contributor",
  "Emerging Researcher",
  "Niche Specialist",
  "Domestic R&D Actor",
  "Strategic Connector",
] as const;

export type RoleLabel = (typeof ROLE_LABELS)[number];

export interface AuthorRecommendation {
  author_id: string;
  name: string;
  primary_country_code: string | null;
  primary_country_name: string | null;
  openalex_id: string | null;
  related_paper_count: number;
  global_scholarly_impact: number | null;
  author_impact_score: number | null;
  structural_score: number | null;
  momentum_score: number | null;
  low_impact_ratio: number | null;
  role_labels: string[];
  caution_flags: string[];
}

export interface GraphResultRead {
  id: string;
  job_id: string;
  graph_type: GraphType;
  node_count: number;
  edge_count: number;
  cluster_count: number;
  stats: Record<string, unknown> | null;
  created_at: string;
}

export interface GraphNodeRead {
  id: string;
  paper_id: string | null;
  author_id: string | null;
  keyword_id: string | null;
  cluster_id: number | null;
  properties: Record<string, unknown> | null;
  x_pos: number | null;
  y_pos: number | null;
}

export interface GraphEdgeRead {
  id: string;
  source_node_id: string;
  target_node_id: string;
  weight: number;
  edge_type: string | null;
}

export interface GraphResultDetail extends GraphResultRead {
  nodes: GraphNodeRead[];
  edges: GraphEdgeRead[];
  build_params: Record<string, unknown> | null;
}

// ---------------------------------------------------------------------------
// NTIS
// ---------------------------------------------------------------------------

export interface NtisProjectSummary {
  id: string;
  ntis_project_id: string | null;
  title: string | null;
  govt_dept: string | null;
  research_agency: string | null;
  performing_org: string | null;
  total_budget: number | null;
  start_year: number | null;
  end_year: number | null;
  status: string | null;
  keywords: string[] | null;
}

export interface NtisOverview {
  job_id: string;
  ntis_project_count: number;
  comparative_match_count: number;
  projects: NtisProjectSummary[];
  last_run_error?: string | null;
}

export interface NtisOverlayTriggerResponse {
  job_id: string;
  task_id: string;
  message: string;
}

export interface AuthorMatrixItem {
  author_id: string;
  name: string;
  global_scholarly_impact: number | null;
  domestic_rnd_relevance: number | null;
  role_labels: string[] | null;
  paper_count: number;
  citation_count: number;
}
