# K2KM Work Progress

## 현재 단계
MVP Phase 1–3 구현 완료. GitHub 레포 셋업 완료.

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
- wrapup 규칙: commit까지, push는 수동

---

## 다음 단계 (Phase 4+)

- [ ] **Phase 4**: Next.js 프론트엔드 (디자인 시스템 링크 참고)
- [ ] **Phase 5**: Claude orchestration (분석 결과 해석/요약)
- [ ] **Phase 6**: NTIS overlay (ntis_projects, ntis_institutions, comparative_results)
- [ ] SCI/SSCI registry 후처리기 (`papers.sci_classification` 채우기)
- [ ] Large Mode 최적화 (igraph/Leiden swap-in)
- [ ] Embedding similarity 엣지 추가
