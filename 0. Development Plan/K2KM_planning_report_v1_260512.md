# 키워드 기반 연구구조 분석·아카이브 플랫폼 구축 기획보고서 (수정안)

## Keyword-to-Knowledge Map (K2KM) + NTIS Comparative Layer

---

# 1. 추진 배경

## 1-1. 문제 인식

현재 대부분의 논문 검색 서비스는 다음 수준에 머물러 있다.

- 논문 목록 검색
- 단순 추천
- 일부 citation graph 시각화
- 저자/키워드 통계 제공

그러나 실제 연구기획·정책기획·전략 분석에서 필요한 것은 단순 검색 결과가 아니다.

실제로 필요한 것은 다음과 같다.

- 특정 키워드 주변의 연구 생태계는 어떻게 형성되는가
- 어떤 논문과 연구자가 구조적으로 중심 역할을 하는가
- 어떤 연구 주제들이 서로 결합되는가
- 글로벌 연구 흐름은 어떤 방향으로 이동하는가
- 우리나라 국가R&D는 글로벌 흐름과 비교해 어디에 위치하는가
- 한국 R&D가 niche로 강하게 점유하는 분야가 존재하는가
- 글로벌 대비 국내 공백 영역은 무엇인가

즉, 필요한 것은 단순 검색이 아니라 “연구 구조 및 국가R&D 구조의 비교 가능한 지도화”이다.

---

## 1-2. 기존 서비스의 한계

### ① 구조보다 검색 중심

Google Scholar, Semantic Scholar 등은 검색 기능은 강력하지만, 연구 구조의 장기적 축적 및 비교분석을 전제로 설계되어 있지 않다.

### ② 분석 결과의 자산화 부족

대부분 결과를 일회성 조회로 제공한다.

부족한 기능:

- 분석 결과 저장
- 재사용
- 버전 관리
- 공개 아카이브화
- 시점별 비교

### ③ 국가R&D 구조와의 연결 부족

기존 scholarly graph 서비스는 논문·citation 중심이다.

그러나 실제 정책·전략 관점에서는 다음 정보가 중요하다.

- 국가R&D 과제
- 정부 투자 구조
- 사업별 연구 흐름
- 국내 연구기관 참여 구조
- 글로벌 연구동향 대비 국내 투자 위치

기존 서비스는 이를 구조적으로 연결하지 못한다.

---

# 2. 프로젝트 목적

본 프로젝트의 목적은 다음과 같다.

## 2-1. 핵심 목적

사용자가 입력한 키워드를 기준으로:

1. 글로벌 scholarly graph를 자동 분석하고,
2. 국내 국가R&D 구조(NTIS)를 연계하여,
3. 글로벌 연구동향 대비 한국 R&D의 위치와 구조를 비교분석하며,
4. 그 결과를 데이터 자산으로 축적·공개하는 시스템을 구축한다.

---

## 2-2. 세부 목적

### ① 글로벌 연구구조 자동 분석

- 대규모 논문 수집
- citation/reference 분석
- 논문·저자·키워드 네트워크 생성
- 중심성·클러스터링 분석

### ② 국내 국가R&D 구조 분석

- NTIS Open API 기반 과제 정보 수집
- 국내 연구자/기관/사업 구조 분석
- 국가R&D 참여 네트워크 구성

### ③ 글로벌 vs 국내 비교분석

- 글로벌 연구 흐름 대비 국내 정렬도 분석
- 한국 R&D niche 탐지
- 글로벌 대비 국내 공백 영역 탐지
- 정책 탐색용 인사이트 생성

### ④ 데이터 자산 구축

- 분석 결과 DB 저장
- 재사용 가능 구조 유지
- 공개 아카이브 구축

### ⑤ 공개 웹서비스 및 브랜딩

- 공개 웹앱 구축
- 블로그형 해설 콘텐츠 생성
- 데이터 기반 연구·정책 분석 역량 브랜딩

---

# 3. 프로젝트 개요

## 3-1. 프로젝트명

### Keyword-to-Knowledge Map (K2KM)

부제: **키워드 기반 글로벌 연구·국가R&D 구조 비교분석 플랫폼**

---

## 3-2. 프로젝트 한 줄 정의

“사용자가 입력한 키워드를 기반으로 글로벌 연구 생태계와 국내 국가R&D 구조를 자동 분석·비교하고, 그 결과를 데이터 자산으로 축적하여 웹앱과 해설 콘텐츠 형태로 제공하는 시스템”

---

# 4. 기대 효과

## 4-1. 기능적 효과

### 글로벌 연구 지형 자동 파악

- 핵심 논문
- 핵심 연구자
- 핵심 키워드
- 연구 흐름
- 연구 군집 구조

자동 도출 가능.

### 국내 국가R&D 구조 파악

- 주요 과제
- 주요 기관
- 사업 구조
- 연구 참여 구조
- 국내 연구 집중 영역

도출 가능.

---

## 4-2. 전략적 효과

### 정책 탐색 도구화

다음 활용 가능:

- 기술 트렌드 탐색
- 정책 방향 탐색
- 국가R&D 투자 구조 분석
- 융합 분야 탐지
- emerging topic 탐색
- 국내 공백 영역 탐지

---

## 4-3. 개인 브랜딩 효과

본 프로젝트는 단순 웹앱 개발이 아니라:

- AI 기반 연구구조 분석
- 글로벌·국내 R&D 비교분석
- 데이터 기반 정책 탐색
- 구조적 인사이트 생성

역량을 보여주는 공개 포트폴리오 역할을 수행한다.

---

# 5. 핵심 개념

## 5-1. 입력 단위

### Keyword

예:

- foundation model
- digital twin
- AI governance
- scientific discovery

사용자는 자연어 질문이 아니라 keyword를 입력한다.

---

## 5-2. 출력 단위

### Research Structure + Comparative Intelligence

출력 결과:

- 논문 네트워크
- 저자 네트워크
- 키워드 네트워크
- 글로벌 클러스터
- 국내 국가R&D 구조
- 글로벌 vs 국내 비교분석
- 정책 탐색 인사이트
- 블로그형 설명

---

# 6. 시스템 기본 원칙

## 6-1. 분석 결과는 데이터 자산이다

모든 분석 결과는:

- 저장
- 재사용
- 재분석
- 버전 관리
- 공개 게시

가능해야 한다.

---

## 6-2. 네트워크는 분리한다

다음 네트워크를 독립 구성한다.

### ① 논문 네트워크

노드: 논문

### ② 저자 네트워크

노드: 저자

### ③ 키워드 네트워크

노드: 키워드

### ④ 국가R&D 프로젝트 네트워크

노드: 국가R&D 과제

### ⑤ 기관 협력 네트워크

노드: 기관

혼합 그래프를 기본 구조로 사용하지 않는다.

---

## 6-3. 표시 데이터와 분석 데이터 분리

### 표시용 데이터

원문 메타데이터:

- 논문 키워드
- 제목
- 초록
- 저자
- 저널
- NTIS 과제명
- 사업명

### 분석용 데이터

파생 데이터:

- embedding
- similarity
- co-occurrence
- cluster mapping

---

## 6-4. Claude는 오케스트레이터다

Claude는:

- 검색 전략 생성
- 데이터 수집 계획 수립
- 분석 흐름 지휘
- 게시 구조 생성
- 블로그 초안 생성

을 담당한다.

실제 계산·저장·분석은:

- Backend
- Worker
- DB
- 분석 엔진

이 수행한다.

---

## 6-5. NTIS는 Overlay Layer다

NTIS 데이터를 scholarly graph에 직접 강결합하지 않는다.

구조:

```text
Global Scholarly Core
    +
Domestic NTIS Overlay
    +
Comparative Intelligence Layer
```

이유:

- identifier 체계 다름
- 기관명 표준화 필요
- 연구자 매칭 불확실성 존재
- 데이터 갱신 주기 차이 존재

---

# 7. 데이터 소스 전략

## 7-1. 글로벌 scholarly graph 계층

### OpenAlex

역할:

- 대규모 논문 수집
- works metadata
- authors/institutions
- filtering
- pagination

### Semantic Scholar

역할:

- citation/reference 보강
- 저자 메타 보강
- citation network 강화

---

## 7-2. 국내 국가R&D 계층

### NTIS Open API

역할:

- 국가R&D 과제 정보 수집
- 국내 연구자/기관 구조 분석
- 국가R&D 참여 네트워크 구축
- 글로벌 연구동향과 비교분석

활용 정보 예시:

- 과제명
- 사업명
- 수행기관
- 참여 연구자
- 연구분야
- 과제기간
- 연구요약
- 성과정보

참고 URL:

- [https://www.ntis.go.kr/rndopen/api/mng/apiMain.do](https://www.ntis.go.kr/rndopen/api/mng/apiMain.do)
- [https://www.ntis.go.kr/rndopen/menual/openapi\_menual.pdf](https://www.ntis.go.kr/rndopen/menual/openapi_menual.pdf)
- [https://www.ntis.go.kr/rndopen/api/mng/apiDetail.do](https://www.ntis.go.kr/rndopen/api/mng/apiDetail.do)
- [https://www.ntis.go.kr/rndopen/api/test/apiDetailTest.do](https://www.ntis.go.kr/rndopen/api/test/apiDetailTest.do)
- [https://www.ntis.go.kr/rndopen/rqst/cmbn/cmbnPrctuseApplsInsertForm.do](https://www.ntis.go.kr/rndopen/rqst/cmbn/cmbnPrctuseApplsInsertForm.do)

---

# 8. 사용자 입력 설계

## 8-1. 검색 건수

### 기본값

20,000건

### 최소값

100

### 최대 상한

50,000

### 이유

- 대규모 구조 분석 가능
- 성능 한계 고려
- 무제한 수집 방지

---

## 8-2. 출판년도 조건

입력:

- 시작년도
- 종료년도

규칙:

- 둘 다 없음 → 전체 기간
- 시작만 있음 → 시작년도 \~ 현재
- 종료만 있음 → 최초 \~ 종료년도
- 둘 다 있음 → 해당 구간

---

## 8-3. 출판물 유형 조건

사용자 선택:

- SCI/SSCI급 저널
- SCIE급 저널
- 학회 프로시딩

기본값:

- 전체 선택

주의:

- SCI/SSCI/SCIE는 별도 registry 기반 후처리 분류
- conference는 source/publication type 기반 판정

---

## 8-4. 저자 메타정보

수집:

- 저자명
- 소속기관
- 소속기관 국가

비수집:

- nationality(국적)

주의: “국적” 대신 “소속기관 기준 국가” 사용.

---

# 9. 분석 구조

# 9-1. 글로벌 scholarly graph

## 논문 네트워크

노드:

- 논문

엣지:

- direct citation
- co-citation
- bibliographic coupling
- semantic similarity(optional)

---

## 저자 네트워크

노드:

- 저자

엣지:

- 공동저술
- citation-induced relation

---

## 키워드 네트워크

노드:

- 키워드

엣지:

- co-occurrence
- embedding similarity

---

# 9-2. NTIS 국가R&D 분석 계층

## 프로젝트 네트워크

노드:

- 국가R&D 과제

엣지:

- 공통 연구분야
- 공통 연구자
- 공통 기관

---

## 기관 협력 네트워크

노드:

- 기관

엣지:

- 공동 과제 참여
- 동일 사업 참여

---

# 9-3. Comparative Intelligence Layer

## 비교분석 항목

### ① Niche 분석

한국 R&D가 글로벌 대비 상대적으로 강하게 집중하는 영역 탐지.

예시:

```text
Niche Score =
국내 해당 클러스터 비중 /
글로벌 해당 클러스터 비중
```

---

### ② 글로벌 정렬도 분석

국내 국가R&D 구조가 글로벌 연구 흐름과 얼마나 유사한지 분석.

예시:

- cosine similarity
- distribution similarity
- cluster overlap

---

### ③ 공백 영역 탐지

글로벌에서는 빠르게 성장하지만 국내 과제·투자가 부족한 영역 탐지.

예시:

```text
Gap Score =
Global Momentum - Domestic Presence
```

---

### ④ 국내 R&D 수준 분석

정량:

- 국내 과제 수
- 참여 연구자 수
- 참여 기관 수
- 글로벌 대비 논문 비중
- 최근 증가율

정성:

- 글로벌 핵심 클러스터와의 정렬도
- emerging topic 참여 여부
- 특정 기관 집중 여부

주의: “절대 평가”가 아니라 “경향/후보/정렬도” 수준으로 표현.

---

# 10. 중심성 분석 전략

## 10-1. 기본 원칙

사용자에게 raw metric을 직접 나열하지 않는다.

반드시:

### 의미 그룹 → 세부 지표

2-step 구조로 제공한다.

---

## 10-2. 지표 구조

| 의미  | 지표                      |
| --- | ----------------------- |
| 영향력 | PageRank, Eigenvector   |
| 허브  | Degree, Weighted Degree |
| 브리지 | Betweenness             |
| 접근성 | Closeness               |

---

# 11. 웹앱 전략

## 11-1. 기본 원칙

이 프로젝트는 단순 그래프 시각화 도구가 아니다.

핵심은:

- 구조 요약
- 연구 탐색
- 정책 탐색
- 글로벌 vs 국내 비교분석
- 해설 제공

이다.

---

## 11-2. 주요 화면

### ① 분석 목록

### ② 키워드 상세

### ③ 글로벌 Research Map

### ④ Domestic R&D Map

### ⑤ Global vs Korea Comparison

세부:

- Niche Areas
- Gap Areas
- Alignment Score
- Key Institutions
- Key Researchers

### ⑥ 블로그형 설명 페이지

---

# 12. 블로그 전략

## 12-1. 역할 정의

블로그는 “새 분석”이 아니다.

이미 생성된 분석 결과를:

- 쉬운 언어로
- 구조적으로
- 일반인이 이해 가능하게

재구성하는 계층이다.

---

## 12-2. 설명 원칙

좋은 표현:

- 중심 경향
- 브리지 역할
- 하위 군집
- 연결 패턴
- 정렬 경향
- niche 후보
- 공백 가능성

나쁜 표현:

- 절대적으로 우수하다
- 세계 최고 수준이다
- 반드시 핵심이다

---

# 13. 시스템 아키텍처 개요

## Frontend

- Next.js
- TypeScript
- Cytoscape.js/Sigma.js

## Backend

- FastAPI
- Worker
- Redis

## Database

- PostgreSQL

## Analysis Engine

- NetworkX
- igraph(확장 시)
- sentence-transformers
- clustering libraries

## Data Collectors

- OpenAlex Connector
- Semantic Scholar Connector
- NTIS Connector

---

# 14. 대용량 처리 전략

## 데이터 규모별 모드

| 규모             | 모드       |
| -------------- | -------- |
| 100\~5,000     | Small    |
| 5,001\~20,000  | Standard |
| 20,001\~50,000 | Large    |

---

## Large Mode 특징

- 비동기 분석
- 그래프 샘플링
- summary-first UI
- threshold filtering

---

# 15. 구현 로드맵

## Phase 1

- DB 설계
- FastAPI 구조
- OpenAlex connector
- Semantic Scholar connector

---

## Phase 2

- dedup
- canonical normalization
- publication classifier
- affiliation 처리

---

## Phase 3

- graph 생성
- centrality
- clustering
- metadata 저장

---

## Phase 4

- 공개 API
- 웹앱 UI
- 그래프 시각화

---

## Phase 5

- Claude orchestration
- 블로그 초안 생성
- 운영 workflow

---

## Phase 6 (NTIS Overlay)

- NTIS Connector
- 국내 R&D 구조 분석
- 연구자/기관 매칭
- Comparative Layer 구축
- niche/gap/alignment 분석

---

# 16. 핵심 리스크 및 대응

| 리스크                       | 대응                        |
| ------------------------- | ------------------------- |
| 데이터 품질 불균일                | source 병합 + null 처리       |
| 키워드 노이즈                   | threshold + 정제            |
| 그래프 과밀                    | sampling/filtering        |
| 과장 해석                     | 패턴/경향 중심 설명               |
| 대량 처리 비용                  | async worker + large mode |
| 연구자 매칭 오류                 | confidence score 기반 처리    |
| NTIS와 scholarly graph 강결합 | overlay 구조 유지             |

---

# 17. 최종 결론

본 프로젝트는 단순 논문 검색 서비스가 아니다.

핵심은:

> “키워드를 기반으로 글로벌 연구 생태계와 국내 국가R&D 구조를 자동 분석·비교하고, 그 결과를 데이터 자산으로 축적·공개하는 시스템”

이다.

이 프로젝트가 성공하면:

- 글로벌 연구구조 아카이브
- 국가R&D 비교분석 플랫폼
- 정책 탐색 도구
- 블로그형 연구 해설 시스템
- 데이터 기반 인사이트 플랫폼
- 개인 브랜딩 포트폴리오

로 발전할 수 있다.

즉, 이 프로젝트의 본질은:

### “검색”이 아니라

### “연구 구조와 국가R&D 구조의 비교 가능한 지도화 및 자산화”

에 있다.

