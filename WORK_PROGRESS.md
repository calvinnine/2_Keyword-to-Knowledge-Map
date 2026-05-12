# K2KM Work Progress

## 현재 단계
MVP Phase 1–5 구현 완료. Groq 인사이트 생성 연동 완료.
SCI/SSCI 분류기, Large Mode(igraph/Leiden), Embedding 유사도 엣지 완료.
Phase 6: NTIS overlay 구현 완료 (API 키 신청 후 활성화).

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

### [2026-05-12] 후처리기 3종 추가

#### ✅ SCI/SSCI 분류기
- `processing/sci_classifier.py`: OpenAlex `fields_of_study` 기반 휴리스틱 분류
  - Level-0 concept → SCIE(자연과학) / SSCI(사회과학) / AHCI(인문학) / ESCI(기타 저널)
  - 비저널(conference, preprint) → None 처리
  - `process.py` 파이프라인 끝에 자동 호출 (best-effort, job 실패 없음)
  - 비고: Clarivate WoS 공식 분류가 아닌 근사치. API 키 확보 시 교체 가능

#### ✅ Large Mode 최적화 (igraph/Leiden)
- `analysis/clustering.py`: 노드 ≥ 5,000 시 Leiden(igraph + leidenalg) 자동 사용
  - 소규모: Louvain (python-louvain), 대규모: Leiden (leidenalg)
  - igraph 미설치 시 Louvain으로 graceful fallback
- `analysis/centrality.py`: 노드 ≥ 5,000 시 igraph로 betweenness/closeness 계산
  - NetworkX 대비 10-100× 빠름 (C 레벨 구현)
  - igraph 미설치 시 NetworkX sampled 방식으로 fallback
- `requirements.txt`: `python-igraph==0.11.8`, `leidenalg==0.10.2` 추가

#### ✅ Embedding Similarity 엣지
- `analysis/paper_graph.py`: abstract 임베딩 기반 의미적 유사도 엣지 추가
  - 모델: `all-MiniLM-L6-v2` (sentence-transformers, ~22M params)
  - 코사인 유사도 ≥ 0.80 인 논문 쌍에 `embedding_similarity` 엣지 생성
  - 대규모 잡은 citation_count 상위 500개 논문으로 제한
  - 노드당 최대 5개 이웃으로 엣지 수 제어
  - sentence-transformers 미설치 시 조용히 건너뜀 (best-effort)
- `requirements.txt`: `sentence-transformers==3.3.1` 추가

---

### [2026-05-12] Phase 6 — NTIS Overlay

#### ✅ Phase 6 — NTIS R&D 과제 연동 + 비교 분석
- `models/ntis.py`: 3개 테이블 정의
  - `NtisProject`: 과제명, 부처, 전문기관, 수행기관, 연구비, 기간, 키워드, 연구자
  - `NtisInstitution`: 수행기관 de-dedup (이름 정규화 후 재사용)
  - `ComparativeResult`: NTIS 과제 ↔ K2KM 논문/저자 매핑
- `alembic/versions/0003_add_ntis.py`: 위 3개 테이블 + 인덱스 마이그레이션
- `collectors/ntis.py`: NTIS Open API collector (기술문서 기반 실제 스펙)
  - 과제검색: `GET /rndopen/openApi/public_project` (XML 응답)
  - 성과검색: `GET /rndopen/openApi/public_result?collection=rpaper` (XML 응답)
  - 연관콘텐츠: `GET /rndopen/openApi/ConnectionContent` (JSON 응답)
  - API 키 없으면 빈 제너레이터 반환 (파이프라인 중단 없음), retry(4회)
- `processing/ntis_ingestion.py`: raw dict → NtisProject / NtisInstitution
  - 실제 XML 필드명 매핑 (ProjectNumber, ProjectTitle_Korean, OrderAgency_Name 등)
  - 수행기관 de-dedup (in-memory cache), 기관 유형 자동 추론
- `analysis/comparative.py`: 4가지 매칭 전략
  1. `keyword_overlap`: NTIS 과제 키워드 ↔ 논문 키워드 Jaccard (≥0.10)
  2. `author_name`: NTIS 연구자 이름 ↔ K2KM 저자 이름 정규화 일치
  3. `institution_name`: NTIS 수행기관 ↔ 저자 소속 토큰 Jaccard (≥0.50)
  4. `paper_outcome_direct`: 성과검색 API 논문 제목 정규화 직접 매핑
- `workers/tasks/ntis_overlay.py`: 독립 Celery task (메인 파이프라인과 별개)
  - 과제 수집 → 성과(논문) 수집 → comparative analysis 순서로 실행
  - API 키 없을 때도 comparative analysis는 실행 (기존 적재분 활용)
- `api/v1/endpoints/ntis.py`: 4개 엔드포인트
  - `POST /jobs/{job_id}/ntis-overlay` — 오버레이 task 큐잉
  - `GET  /jobs/{job_id}/ntis` — 과제 목록 + 매칭 집계
  - `GET  /jobs/{job_id}/ntis/projects/{id}` — 과제 상세
  - `GET  /jobs/{job_id}/ntis/comparisons` — 비교 결과 목록 (match_type 필터)
- `config.py`: `NTIS_API_KEY` 설정 추가
- `workers/celery_app.py`: ntis_overlay task 모듈 등록
- 브랜치: `phase-5-claude-insight` (계속 작업)

**활성화 방법**: `.env`에 `NTIS_API_KEY=<발급받은_키>` 추가 후
`POST /api/v1/jobs/{job_id}/ntis-overlay` 호출.

---

### [2026-05-12] Meridian 디자인 시스템 적용 + 버그픽스

#### ✅ SQLAlchemy enum 버그 픽스
- `backend/app/models/job.py`: `Enum(JobStatus, values_callable=lambda x: [e.value for e in x])`
  - PostgreSQL native enum이 uppercase 멤버명 대신 lowercase 값을 사용하도록 수정
  - 기존: `"PENDING"` 삽입 → 오류 / 수정 후: `"pending"` 삽입 → 정상

#### ✅ Meridian Policy Design System 프론트엔드 적용
- `frontend/src/app/globals.css` 전면 교체
  - 폰트: Geist → Pretendard(한국어) + Inter Tight(영문) + JetBrains Mono(코드)
  - 색상: 시에나/크림 팔레트 → Navy Ink + Graphite + Soft Blue Accent(`#6E9BD9`)
  - 라운드: sm=4px · md=6px · lg=8px (기존 6/10/14px)
  - 그림자: 쿨톤 navy-based (기존 warm-tinted)
  - 모션: `cubic-bezier(0.2, 0.8, 0.2, 1)`, 160/240/360ms
- `frontend/src/app/layout.tsx`: Geist 폰트 제거, CSS CDN 폰트로 전환
- `frontend/src/components/ui/Button.tsx`: focus ring Meridian 스펙 (`ring-2 ring-accent ring-offset-2`)
- `frontend/src/components/ui/Input.tsx`: focus ring 동일 적용, radius sm=4px
- `frontend/src/components/ui/Card.tsx`: rest 상태 shadow 제거 (border-only, Meridian 기준)

---

### [2026-05-12] 첫 End-to-End 파이프라인 성공 + Ingestion 버그픽스 3건

#### ✅ 인제션 FK/중복 버그 3건 픽스
- `processing/ingestion.py` `_get_or_create_institution`: `flush()` 추가 — Institution row가 DB에 있어야 `author_affiliations`가 FK 참조 가능
- `processing/ingestion.py` OpenAlex/S2 paper 저장 후 `flush()` 추가 — paper row가 DB에 있어야 child FK 참조 가능
- `_paper_author_seen` + `_paper_keyword_seen` set 추가 — 같은 논문이 OpenAlex+S2 양쪽 수집 시 dedup 후 같은 paper_id로 중복 삽입되는 문제 해결

#### ✅ 첫 End-to-End 실행 성공 (graph neural network, 2023–2024, 100편)
- 수집: OpenAlex+S2 합쳐 200편
- 처리: DOI/title dedup으로 183편 정규화
- 분석: 논문(183n/64e/135c) + 저자(981n/2651e/173c) + 키워드(370n/1096e/241c) 네트워크 생성
- UI에서 4탭(논문·저자·키워드·그래프) 결과 정상 표시
- Sigma.js 인터랙티브 시각화 정상 동작 (Louvain 색상 + PageRank 노드 크기)

#### ⚠️ 발견된 추가 개선사항
- 저자 탭의 `논문 수`·`인용 수` 컬럼이 0으로 표시 — 집계 컬럼이 분석 단계에서 채워지지 않음
- Celery worker가 first-run 시 `analyzing` 상태에서 hang하는 경우 발생 — 직접 실행 시 8초만에 완료. 재현 후 원인 파악 필요
- `eigenvector_centrality_numpy` 경고 — disconnected graph에서 동작 불일치 (현재 처리 무시)

---

## 다음 단계

- [ ] 분석 단계 author 집계 컬럼(`paper_count`, `citation_count`) 채우기
- [ ] Celery worker analyze 단계 hang 원인 분석
- [ ] 추가 테스트 돌리면서 개선사항 발굴
- [ ] 프론트엔드: NTIS 비교 결과 시각화 패널
- [ ] 프론트엔드: 고급 필터링, 결과 내보내기
