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

export interface JobRead extends JobListItem {
  year_start: number | null;
  year_end: number | null;
  publication_types: string[] | null;
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
}

export interface JobFromQueryPayload {
  query: string;
  max_papers?: number;
  year_start?: number | null;
  year_end?: number | null;
  publication_types?: string[] | null;
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
