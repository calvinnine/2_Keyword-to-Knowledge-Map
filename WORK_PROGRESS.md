# K2KM Work Progress

## 현재 단계
MVP Phase 1–5 구현 완료. Groq 인사이트 생성 연동 완료.

---

## 세션 히스토리

### [2026-05-12] MVP Phase 1–3 + NL Parser + GitHub 셋업

#### ✅ Phase 1 — 프로젝트 스캐폴드 / API / 수집기
- FastAPI 백엔드 구조 (`app/`, `api/v1/`, `workers/`) 생성
- Docker Compose (PostgreSQL 16, Redis 7, API 서버, Celery Worker)
- SQLAlchemy 모델 16종: `AnalysisJob`, `RawPayload`, `Paper`, `PaperSource`, `PaperAuthor`, `PaperKeyword`, `Citation`, `Author`, `AuthorAffiliation`, `Institution`, `Keyword`, `GraphResult`, `GraphNode`, `GraphEdge`, `ClusterResult`, `CentralityResult`
- Alembic 마이그레이션 `0001_initial.py`
- OpenAlex connector (cursor-based pagination, retry, polite-pool)
- Semantic Scholar connector (offset pagination, bulk fetch)
- FastAPI 엔드포인트 9종 (jobs/papers/authors/keywords/graphs)

#### ✅ Phase 2 — 정규화 / Dedup / 적재
- `normalizer.py`: DOI 정규화, title fingerprint, keyword 정규화, OpenAlex inverted abstract 디코더
- `dedup.py`: DOI-first → title-normalization fallback 중복 제거
- `affiliation.py`: affiliation → country 추출 (nationality 미추론)
- `ingestion.py`: raw payload → canonical entity 변환 (OpenAlex / S2 양쪽 처리)
- `Author.primary_country_code`: affiliation majority vote로 저자 주 활동국 집계

#### ✅ Phase 3 — 그래프 분석
- `paper_graph.py`: citation + co-citation + bibliographic coupling
- `author_graph.py`: co-authorship (weight = 공동 논문 수)
- `keyword_graph.py`: co-occurrence (weight = 동시 등장 논문 수)
- `centrality.py`: PageRank, Eigenvector, Degree, Weighted Degree, Betweenness (large graph 샘플링), Closeness
- `clustering.py`: Louvain community detection
- Celery 파이프라인: `collect → process → analyze` chain

#### ✅ 자연어 입력 지원
- `nlp/query_parser.py`: 한국어/영어 휴리스틱 파서
  - 키워드 추출, intent 분류 (author_influence / paper_centrality / keyword_clusters / general)
  - 연도 힌트 파싱 (최근 N년, YYYY-YYYY, YYYY년)
- `POST /api/v1/jobs/from-query`: NL → keyword 변환 후 동일 파이프라인
- `POST /api/v1/jobs/parse-query`: 변환 결과 미리보기
- pytest 30개 통과

#### ✅ GitHub 셋업
- `calvinnine/2_Keyword-to-Knowledge-Map` public 레포 생성
- 68개 파일 초기 커밋 push
- 브랜치 전략: main은 문서/설정만, 기능은 임시 브랜치에서 작업

### [2026-05-12] Phase 4 — Next.js 프론트엔드 MVP

#### ✅ Phase 4 — 웹앱 UI / 시각화
- **프레임워크**: Next.js 16 (App Router), React 19, TypeScript, Tailwind v4
- **페이지**: `/` 분석 목록(5초 폴링), `/jobs/new` 키워드+NL 모드, `/jobs/[id]` 분석 상세, `/graphs/[id]` 그래프 시각화
- **그래프**: Sigma.js + Graphology + ForceAtlas2 레이아웃, Louvain 군집 색상
- **API 통신**: TanStack Query v5, 타입 안전 fetch 래퍼
- **디자인**: CSS 변수 기반 커스텀 토큰 (Claude 스타일 영감)
- 브랜치: `phase-4-frontend-mvp`

### [2026-05-12] Phase 5 — Groq 인사이트 생성

#### ✅ Phase 5 — LLM 분석 인사이트
- `analysis/insight.py`: 그래프 분석 완료 후 Groq API로 한국어 연구 인사이트 자동 생성
  - 논문 네트워크 상위 논문(PageRank), 저자 네트워크 핵심 저자, 키워드 트렌드 요약
  - API 키 없으면 조용히 건너뜀 (best-effort, job 실패 없음)
- `alembic/versions/0002_add_job_insight.py`: `analysis_jobs.insight` 컬럼 추가
- LLM: Groq (`llama3-70b-8192`) — OpenAI-compatible API, 외부 배포 무료 티어
  - `INSIGHT_BASE_URL` 설정으로 다른 제공자로 교체 가능
- 프론트엔드: `JobDetail.tsx` 분석 완료 잡에 "AI 인사이트" 카드 표시
- 브랜치: `phase-5-claude-insight`

---

## 다음 단계 (Phase 6+)

- [ ] **Phase 6**: NTIS overlay (ntis_projects, ntis_institutions, comparative_results)
- [ ] SCI/SSCI registry 후처리기 (`papers.sci_classification` 채우기)
- [ ] Large Mode 최적화 (igraph/Leiden swap-in)
- [ ] Embedding similarity 엣지 추가
- [ ] 프론트엔드: 다크 모드, 고급 필터링, 결과 내보내기
