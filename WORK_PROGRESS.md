# K2KM Work Progress

## 현재 단계
MVP Phase 1–4 구현 완료. 프론트엔드 웹앱 배포 준비 완료.
인용수 정밀도 정책: S2 + OA(sanity check) MAX 전략 + influential/breakdown 보조 지표 (2026-05-16).

---

## 세션 히스토리

### [2026-05-16] 인용수 정밀도 강화 — 멀티 ID lookup + influential + journal/preprint breakdown

#### 🔥 발견된 문제 (배경)
1. S2 `DOI:<journal_doi>` 단일 lookup으로는 **arXiv preprint로만 색인된 논문 매칭 실패**:
   - "Simple and Efficient Heterogeneous GNN" (AAAI 2023) → S2는 arXiv DOI(10.48550/arXiv.2207.02547)로 색인. AAAI DOI로 404.
   - 결과: 진짜 233회인 논문이 우리 DB에서 NULL로 표시
2. Google Scholar(741) vs S2(441) vs OA(378) 같은 차이가 **데이터 오염이 아니라 정상 카운팅 시점 차이**인 케이스 존재. 단순히 폐기하면 정상 데이터 손실.
3. 서지학 전문가 검토 의견: `influentialCitationCount`와 citing-paper publicationTypes 활용 권장.

#### 💡 정책 결정 (모두 사용자 합의)
사용자와의 의사결정 매트릭스 결과 (전문가 의견 vs 우리 제안 비교 후):

| 결정 | 채택 | 비고 |
|------|------|------|
| 최종 인용수 산출 | **MAX(S2, OA_sane)** | 자원 제약. 기술부채 기록 |
| 시간역행 검증 | **counts_by_year 집계 sanity check** (pub_year 이전 비중 > 10%면 폐기) | 자원 제약. 기술부채 기록 |
| Preprint 처리 | **corpus 포함 + venue 배지 + 인용 type 분해** (해석 C) | K2KM 핵심 use case |
| `has_references:true` 필터 | **적용** | OpenAlex 검색 시 references 없는 논문 제외 |
| `influentialCitationCount` | **수집·표시** | 전문가 권고 채택 |
| 멀티 ID lookup | **DOI → arXiv DOI → ARXIV** 순차 시도 | 우리 발견 + 전문가 권고 |

#### ✅ 구현 내용
1. **마이그레이션 `0012_citation_quality_columns.py`** — Paper에 4개 컬럼 추가:
   - `influential_citation_count`: S2 AI 판정 핵심 인용수
   - `citation_by_journal`, `citation_by_preprint`: 인용한 논문 venue 타입 분포
   - `citation_source`: 's2' | 'openalex' | NULL (헤드라인 인용수의 출처)
2. **`models/paper.py`**: 위 컬럼 반영 + 상세 주석 (정책 근거)
3. **`processing/citation_enrichment.py` 전면 재작성**:
   - `_candidate_s2_ids()`: paper.doi → OA `ids.arxiv` → paper.arxiv_id 순으로 후보 ID 빌드
   - `_oa_count_passes_sanity()`: counts_by_year 시간역행 비중 > 10%면 폐기
   - `_classify_citations()`: citing paper publicationTypes로 journal/preprint 분류
   - **Two-pass batching**: pass1 라이트 필드(500개/배치) → pass2 citations 필드(25개/배치). S2가 무거운 필드에 빡빡한 rate limit 거는 문제 해결
   - **상위 50편만 breakdown 수행** (rate limit 절약, 롱테일은 비용 대비 효용 낮음)
4. **`collectors/semantic_scholar.py`**:
   - `get_papers_bulk_with_fields()`: 커스텀 fields 지원 + 429 retry-with-exponential-backoff (Celery 동시성 환경에서 silently 실패 방지)
5. **`collectors/openalex.py`**: 검색 filter에 `has_references:true` 추가
6. **`api/v1/endpoints/papers.py`**, **`schemas/paper.py`**: 새 4개 필드 반영
7. **`lib/types/api.ts`**: `citation_source`, `influential_citation_count`, `citation_by_journal`, `citation_by_preprint` 추가
8. **`components/jobs/JobDetail.tsx`**:
   - `VenueBadge` 신규 컴포넌트: 저널/학회/프리프린트/도서/기타 배지 (Meridian 색상)
   - `CitationCell` 신규 컴포넌트: 헤드라인 인용수 + 작은 글씨로 `저널 X · 프리 Y · 핵심 Z` 분해 + tooltip에 출처 정보
   - Papers 탭 + AuthorRow 펼친 영역 모두에 적용

#### 📊 검증 결과 ("graph neural network" 100편 분석)
- citation_source 분포: **s2 127개 / openalex(fallback) 55개 / NULL 1개**
- 가짜 5,375회 케이스: `has_references:true` 필터로 corpus에서 제외됨 (이중 차단)
- Simple Efficient HGNN: AAAI DOI 매칭 실패 → arXiv DOI fallback으로 S2 데이터 회수 성공
- Top 1: GNN Recommender Survey — 743 (S2), 핵심 15, 저널 712 / 프리프린트 27 (95% 저널)
- Top 4: GNN Time Series Survey — 441 (S2), 핵심 8, 저널 419 / 프리 22
- Shirui Pan (Griffith U): 3편 합계 **802회** — 진정한 GNN 분야 영향력 1위 부상

---

## 🔧 기술 부채 / 정밀도 업그레이드 대기

자원·시간 제약으로 단순화한 부분. 정밀 분석 모드 또는 라이선스 확보 시점에 재논의.

### 1. INTERSECTION 전략 (Scopus 급 정밀도)
- 현재: MAX(S2, OA_sane)
- 업그레이드: S2와 OA의 인용 LIST 교집합 (양쪽 source가 공통으로 가진 인용만 인정)
- 비용: 200편당 수만~수십만 추가 API call
- **재논의 시점**: WoS/Scopus 기관 라이선스 검토 시 동시에

### 2. Per-citing-paper publicationType 검증
- 현재: counts_by_year 집계로 시간역행 비율 체크
- 업그레이드: 인용한 논문 각각의 publicationType + publicationDate 확인, preprint면 OK, 일반 출판물인데 시간역행이면 noise로 drop
- 효과: 정상 preprint 케이스는 살리면서 알고리즘 에러는 더 정밀하게 차단
- **재논의 시점**: 정책 보고서 등 매우 정밀한 분석 모드가 필요해질 때 별도 옵션으로

### 3. Google Scholar 하이브리드 fallback
- 현재: S2 미발견 + OA sanity fail → NULL
- 업그레이드: 그래도 NULL인 케이스만 SerpAPI/scholarly로 GS 보강
- 비용: $30-100/mo (유료 서비스 시) 또는 ToS 회색지대 (DIY)
- **재논의 시점**: NULL 비율이 사용자 불만 수준이 될 때

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

### [2026-05-12] Phase 4 — Next.js 프론트엔드 MVP 완성

#### ✅ Phase 4 — 웹앱 UI / 시각화
- **프레임워크**: Next.js 16 (App Router), React 19, TypeScript, Tailwind v4
- **페이지 라우팅**:
  - `/`: 분석 목록 (5초 자동 폴링)
  - `/jobs/new`: 키워드 모드 + 자연어 쿼리 모드 (실시간 미리보기)
  - `/jobs/[id]`: 분석 상세 (진행 상태, 논문/저자/키워드/그래프 탭)
  - `/graphs/[id]`: 그래프 시각화 (Sigma.js + ForceAtlas2 + Louvain 색상)
- **라이브러리**: TanStack Query v5 (데이터 페칭), Sigma.js + Graphology (그래프)
- **UI 컴포넌트**: Card, Button, Input, Tabs, Badge (Claude 제품 스타일 영감)
- **디자인 시스템**: CSS 변수 기반 커스텀 토큰 (색상/라운드/그림자)
- **API 통신**: 타입 안전 fetch 래퍼 (`src/lib/api/client.ts`), Pydantic ↔ TypeScript 스키마 동기화
- **테스트**: 모든 라우트 HTTP 200, 타입 체킹 통과

---

### [2026-05-13] 로컬 테스트 라운드 — 분석 파이프라인 버그 일괄 수정 + KO→EN 자동 번역

#### ✅ 분석 파이프라인 버그 5종 수정
- **그래프 0 노드 버그**: `paper_graph.py` / `author_graph.py` / `keyword_graph.py` —
  `publication_scope` 필터가 0건 매치 시(국문 저널·프리프린트로 `sci_classification=None`) 전체 논문으로 자동 폴백.
  `_paper_id_subquery(job_id, scope)` → `_paper_id_subquery(db, job_id, scope)`로 시그니처 변경.
- **`np.float64` InvalidSchemaName**: `layout.py` — `spring_layout` 결과를 `float()`로 명시 변환해 psycopg2에 native Python float 전달.
- **DOI 전역 unique 충돌**: 마이그레이션 `0010_fix_paper_doi_unique_per_job.py` 추가 —
  `papers.doi` 전역 UNIQUE 제거 → 부분 unique 인덱스 `(doi, job_id) WHERE doi IS NOT NULL` 및 `(title_normalized, job_id) WHERE doi IS NULL`로 변경. 동일 키워드 재실행 / 키워드 간 중복 논문 허용.
- **`MultipleResultsFound`**: `process.py` 태스크 / `resolve_openalex_citations` — `PaperSource` 조회에 `Paper.job_id` 조인 필터 추가.
- **저자명 기관 오염**: `normalizer.py` `normalize_author_name` — `/` 포함, 6 토큰 초과, 기관 접미사(`대학교`/`연구원`/`학과`/`院`/`所`) 끝나는 문자열을 저자에서 제외.
- **키워드 `paper_count=0`**: `ingestion.py`에 `update_keyword_stats()` 추가 + `process.py` 태스크에서 호출.

#### ✅ Semantic Scholar 페이징 한도 처리
- S2 `paper/search`의 hidden hard limit (`offset + limit ≤ 1000`) 미처리로 `max_papers > 1000` 잡이 400 에러로 실패하던 버그 수정.
- `_S2_MAX_RESULTS = 1000` 상수 도입 + offset 사전 차단 + 잔여 400 응답 try/except 방어. 잡 실패 대신 정상 종료.

#### ✅ 한국어 → 영어 키워드 자동 번역
- `app/nlp/translate.py` 신규 — `contains_hangul()` / `translate_keyword_to_english()`.
- Groq `llama-3.1-8b-instant` 사용, 키워드/자연어/parse-query 미리보기 3개 엔드포인트에 적용.
- 원본은 `job.params.original_keyword`에 보존, `JobDetail`에 “입력: ‘양자컴퓨팅’ → 영문 번역 적용” 표시.
- GROQ 미설정·실패 시 원본 그대로 사용 (fallback safe).

#### ✅ UX 안내 문구
- `JobCreateForm`: 키워드/자연어 입력 필드에 한→영 자동 번역 안내, `max_papers` 동작 설명(OpenAlex 주력 / S2 1,000 보조), 저널 필터에 ISSN 0건 매치 시 폴백 안내.

#### ✅ Docker / DB 운영
- `docker-compose.yml` `api`·`worker`에 `environment:` 블록 추가 (컨테이너 내부에서 `db`·`redis` 서비스명 사용).
- 마이그레이션 0010까지 적용. 테스트 잡 “quantum computing” 100건 → paper graph 176 nodes / 181 edges, author 1085 / 14803, keyword 375 / 1761로 정상 동작 확인.

### [2026-05-13] NTIS 오버레이 최적화 + IP 에러 처리 + 배포 구조 논의

#### ✅ NTIS 병렬 fetch 최적화
- `collectors/ntis.py` — `ThreadPoolExecutor(max_workers=4)` 병렬 페이지 fetch 도입.
  페이지 1을 동기 fetch해 `TOTALHITS` 파악 후, 나머지 페이지를 4-way 병렬 수집.
  500개 과제 기준 약 4× 속도 향상. `httpx.Limits` 커넥션 풀 설정.

#### ✅ NTIS API 에러 감지 및 전파
- NTIS는 HTTP 200에 `<error>접근 허용 IP가 아닙니다.</error>` 바디를 반환하는 독특한 패턴.
  `NtisApiError` 예외 클래스 신규 추가, `_fetch_xml`에서 root tag == "error" 검사.
  `tenacity` 데코레이터에 `retry_if_not_exception_type(NtisApiError)` 추가 — 영구 에러는 재시도 안 함.

#### ✅ NTIS 에러 → 프론트엔드 표시
- `ntis_overlay.py` — `try/except NtisApiError` 블록으로 에러 메시지 포착, `job.params["ntis_last_run"]["error"]`에 저장.
- `ntis.py` 엔드포인트 — `NtisOverviewResponse.last_run_error` 필드 추가, params에서 조회해 반환.
- `api.ts` — `NtisOverview.last_run_error?: string | null` 타입 추가.
- `NtisPanel.tsx` — `apiError` 표시 블록 + "IP 등록 안내" 조건부 설명 문구.

#### ✅ NTIS 한국어 키워드 우선 사용
- `ntis_overlay.py` — `keyword = (job.params or {}).get("original_keyword") or job.keyword`.
  한→영 번역된 잡에서도 NTIS 수집 시 원본 한국어 키워드 사용.

#### ✅ NTIS comparative analysis 최적화
- `comparative.py` — `select(Author).where(Author.id.in_(job_author_ids))`로 잡 내 저자만 로드 (전체 로드 제거).
- affiliation 토큰화 사전 계산, bulk insert (`db.execute(insert(ComparativeResult), rows)`).

#### 📌 배포 구조 논의 (결론: 나중에)
- NTIS API는 등록 IP에서만 호출 가능 → 프로덕션 배포 시 Railway/Render 서버 IP를 NTIS에 등록 필요.
- Vercel은 K2KM 백엔드 불가 (Celery + PostgreSQL 필요). Railway/Render 권장.
- 사용자 요청: "나중에 서비스 배포할 때 알려줘" — 배포 시점에 안내 예정.

---

### [2026-05-16] OpenAlex 인용수 폐기 + Semantic Scholar 인용수 primary 전환

#### 🔥 발견된 문제 (배경)
"graph neural network 2023–2024" 100편 분석 결과, 상위 인용 논문이 비정상이었음:
- **"Targeted Branching for the Maximum Independent Set Problem Using Graph Neural Networks"** (LIPIcs SEA 2024, DOI: `10.4230/lipics.sea.2024.20`)
- OpenAlex에서 `cited_by_count: 5375` 반환
- **Google Scholar 실측치: 7회 인용**
- OpenAlex `counts_by_year`를 보면 **publication_year=2024인데 인용수가 2017년부터 누적**: 2017(1), 2018(43), 2019(198), 2020(396), 2021(755), 2022(1053), 2023(1274), 2024(1021), 2025(604), 2026(30)
- 시간 역행 → 명백히 OpenAlex가 **다른 work의 citation graph를 잘못 연결**한 데이터 오염

영향:
- 상위 저자 4명(Silva·Rodrigues·Teixeira·Amorim, University of Aveiro) 모두 가짜 5,375회 인용으로 표시
- PageRank, 인사이트 생성, "영향력 있는 연구자 식별" 모든 분석이 왜곡됨
- K2KM의 핵심 가치(인용 기반 영향력 분석)가 무너짐 → 수정 불가피

#### 💡 의사결정 과정
**옵션 A**: Sanity check (publication_year 이전 counts_by_year 발견 시 폐기)
- 단점: OpenAlex가 다른 부분에서 또 어떤 오염을 내놓을지 알 수 없음 → 임시방편

**옵션 B**: Google Scholar로 전환
- 단점: 공식 API 없음 / scraping은 ToS 위반 / Rate limit 빡빡 / DOI·ORCID 표준 메타데이터 누락
- 결론: production 운영 불가

**옵션 C (채택)**: Semantic Scholar를 인용수 primary로 승격
- S2는 paper의 reference text를 직접 파싱 → 인용수 정확
- 우리 S2 API key 보유, `/paper/batch` endpoint (최대 500개/req) 활용 가능
- DOI 기반 lookup → OpenAlex 메타데이터와 자연스러운 매칭
- Rate limit: API key 사용 시 1 req/sec — 200편 lookup이 1 batch request로 끝나 충분

#### ✅ 구현 내용
1. **`models/paper.py`**: `citation_count`를 `int | None`으로 변경 (`Integer, nullable=True, default=None`)
   - NULL = "Semantic Scholar로 검증되지 않음"을 의미
2. **`alembic/versions/0011_paper_citation_count_nullable.py`**: 마이그레이션 추가 (NOT NULL → nullable, default 제거)
3. **`processing/citation_enrichment.py` 신규**: S2 `/paper/batch`로 일괄 검증
   - 동작: job 내 모든 DOI 보유 paper → DOI:<doi> 형태로 batch lookup → S2 `citationCount` 적용
   - S2에 없거나 응답 누락 → 명시적으로 `citation_count = NULL` (오염된 OA 값 폐기)
   - DOI 없는 paper도 NULL (검증 불가)
   - Best-effort: S2 장애 시 job 실패 안 시킴
4. **`processing/ingestion.py`**: OpenAlex ingestion 시 `citation_count=None`로 강제 (OA 값 신뢰 안 함). S2 search 결과는 NULL 안전한 값만 일시 저장 (enrichment가 덮어씀).
5. **`workers/tasks/process.py`**: SCI 분류 직후 + author/keyword 집계 직전에 `enrich_citations_from_s2()` 호출
   - 집계가 정확한 인용수 위에서 돌도록 순서 중요
6. **`schemas/paper.py`**, **`lib/types/api.ts`**: `citation_count: int | None` 반영
7. **`api/v1/endpoints/papers.py`**: `ORDER BY citation_count DESC NULLS LAST` — NULL은 항상 뒤로
8. **`components/jobs/JobDetail.tsx`**: NULL → `—` 표시 + tooltip ("Semantic Scholar로 검증되지 않음")

#### 📋 정책 정리 (코드 주석에도 반영)
- **`citation_count`의 single source of truth**: Semantic Scholar
- **OpenAlex의 역할**: 검색·메타데이터(저자·소속·키워드)·SCI 분류용. **인용수는 무시**
- **NULL의 의미**: "값을 못 구함" — 0회와 구분
- **장기 전략**: WoS 라이선스 확보 시 추가 cross-check layer로 도입 가능

#### ⚠️ 알려진 한계
- S2 커버리지: 한국·중국 학회지 일부 누락 → 더 많이 NULL로 표시될 가능성. 이는 "거짓 데이터 표시"보다 안전한 실패
- Author/Keyword 집계는 `coalesce(sum(citation_count), 0)` → NULL은 0으로 합산. 영향력 평가 시 보수적 추정 (오버스테이트 안 됨)

---

## 다음 단계 (Phase 5+)

- [ ] **Phase 5**: Claude orchestration + 블로그 초안 생성
- [x] **Phase 6**: NTIS overlay (ntis_projects, ntis_institutions, comparative_results) ✅ 구현 완료
- [ ] S2 enrichment 검증: 같은 키워드 재실행 시 가짜 5,375회 사라지는지 확인
- [ ] 저자 탭 라벨 명확화: "논문 수" → "관련 논문" / "인용 수" → "관련 인용 합계"
- [ ] OpenAlex `works_count`·`cited_by_count` (저자별 통산 통계) 추가 캡처 — "이번 분석 vs 통산" 비교용
- [ ] WoS 라이선스 / OpenCitations 추가 검증 layer 검토
- [ ] NTIS 프로덕션 배포 가이드 (Railway/Render IP → ntis.go.kr 재신청)
- [ ] SCI/SSCI registry 후처리기 (`papers.sci_classification` 채우기)
- [ ] Large Mode 최적화 (igraph/Leiden swap-in)
- [ ] Embedding similarity 엣지 추가
- [ ] 프론트엔드: 다크 모드, 고급 필터링, 결과 내보내기
