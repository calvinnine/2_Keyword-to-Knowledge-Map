# 키워드 기반 연구구조 분석·아카이브 플랫폼 구축 기획보고서 v2

## Keyword-to-Knowledge Map (K2KM) + NTIS Comparative Layer

> 본 v2는 기존 v1 기획보고서에 **논문별 품질 보정 지표**, **연구자 역할 기반 추천 모델**, **글로벌 학술 영향력과 국내 R&D 연계성의 이중축 비교 구조**를 반영한 개정안이다.

---

# 0. v2 개정 요약

## 0-1. 개정 목적

v1은 키워드 기반 글로벌 연구구조 분석과 NTIS Overlay 기반 국내 R&D 비교분석 구조를 제시하였다. v2는 여기에 연구자 추천 과정에서 발생할 수 있는 **단순 논문 수 기반 왜곡**을 방지하기 위한 품질 보정 로직을 추가한다.

특히 단순히 관련 논문을 많이 생산한 연구자가 상단에 노출되는 문제를 막기 위해, 논문별 영향력·주제 관련성·네트워크 중심성·최신성·신뢰도 등을 종합한 **Paper Evidence Weight**를 도입한다.

## 0-2. 본문 반영 사항과 부록 분리 사항

| 구분 | 반영 위치 | 내용 |
| --- | --- | --- |
| 본문 반영 | 제10장~제18장 | 서비스 원칙, 연구자 추천 철학, 역할 라벨, 글로벌-국내 2축 비교, UI/로드맵/리스크 반영 |
| 부록 반영 | 붙임 1~8 | 계산식, 가중치, DB 설계, API 설계, 상세 파이프라인, 추천 설명 템플릿, 주의 플래그 |

## 0-3. v2 핵심 변경 사항

1. 단순 논문 수 기반 연구자 추천을 지양한다.
2. 논문별 **Paper Evidence Weight**를 도입한다.
3. 연구자는 단일 순위가 아니라 역할 기반으로 분류한다.
4. 글로벌 연구자와 국내 연구자는 하나의 단일 점수로 비교하지 않는다.
5. **Global Scholarly Impact × Domestic R&D Relevance** 이중축 비교를 적용한다.
6. NTIS는 기존 원칙대로 Global Scholarly Core에 강결합하지 않고 Overlay Layer로 유지한다.
7. 추천 결과에는 반드시 추천 근거와 주의 플래그를 함께 제공한다.

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


# 11. 연구자 추천 및 논문 품질 보정 전략

## 11-1. 문제 인식

K2KM은 특정 키워드 주변의 연구 생태계에서 핵심 논문, 핵심 연구자, 연구 클러스터, 국내 R&D 위치를 파악하기 위한 서비스이다.

따라서 연구자 추천을 단순 논문 수에 기반하여 수행하면 다음과 같은 문제가 발생한다.

| 문제 | 설명 |
| --- | --- |
| 저영향 논문 대량 생산자 유리 | 영향력 낮은 논문을 많이 낸 연구자가 상단에 노출될 수 있음 |
| 신진 연구자 불리 | 논문 수는 적지만 최근 급부상하는 연구자가 묻힐 수 있음 |
| 오래된 권위자 과대평가 | 과거 고인용 논문만으로 현재 연구 흐름을 대표하는 것처럼 보일 수 있음 |
| 분야 편향 | 인용이 많은 분야의 연구자가 다른 분야보다 유리해짐 |
| 주제 이탈 | 입력 키워드와 직접 관련 없는 유명 연구자가 상단에 뜰 수 있음 |
| 정책 활용성 저하 | 국내 R&D와 연결되지 않는 글로벌 유명 연구자가 정책적으로 과대평가될 수 있음 |

따라서 K2KM의 연구자 추천은 “많이 쓴 연구자”를 찾는 기능이 아니라, **특정 키워드의 연구 생태계 안에서 의미 있는 역할을 수행하는 연구자**를 찾는 기능으로 설계한다.

---

## 11-2. 기본 원칙

K2KM의 연구자 추천은 다음 원칙을 따른다.

| 원칙 | 내용 |
| --- | --- |
| 단순 수량 배제 | 논문 수만으로 연구자를 추천하지 않는다. |
| 논문 품질 보정 | 논문별 영향력, 중심성, 신뢰도 지표를 반영한다. |
| 주제 관련성 우선 | 입력 키워드와 관련 없는 고인용 논문은 추천 근거에서 제외한다. |
| 역할 기반 추천 | 연구자를 단일 순위가 아니라 역할 유형으로 분류한다. |
| 국내 R&D 분리 비교 | 글로벌 논문 영향력과 국내 국가R&D 연계성은 같은 점수로 섞지 않는다. |
| 설명 가능성 확보 | 왜 추천됐는지 사용자가 이해할 수 있어야 한다. |
| 과장 방지 | “최고 연구자”가 아니라 “이 구조에서 이런 역할을 하는 연구자”로 표현한다. |

---

## 11-3. Paper Evidence Weight 도입

논문별 품질을 절대평가하지 않고, 해당 키워드 분석에서 특정 논문을 얼마나 중요한 근거로 볼 것인지 계산한다.

이를 **Paper Evidence Weight**라고 정의한다.

Paper Evidence Weight는 다음 요소로 구성한다.

| 구성 요소 | 의미 |
| --- | --- |
| Topical Relevance | 입력 키워드와 논문의 직접 관련성 |
| Normalized Citation Impact | 분야·연도 보정 인용 영향력 |
| Network Centrality | 논문 네트워크 내 구조적 위치 |
| Knowledge Transfer | 단순 인용이 아닌 지식 전이 정도 |
| Recency / Momentum | 최근성 및 최근 인용 증가세 |
| Reliability | 출처·메타데이터·철회 여부 등 신뢰도 |

기본 구조는 다음과 같다.

```text
Paper Evidence Weight
= Topical Relevance
+ Normalized Citation Impact
+ Network Centrality
+ Knowledge Transfer
+ Recency / Momentum
+ Reliability
```

세부 계산식과 기본 가중치는 **붙임 1. Paper Evidence Weight 상세 설계**에 둔다.

---

## 11-4. 논문 수의 제한적 활용

논문 수는 완전히 배제하지 않는다. 다만 연구자의 생산성을 참고하기 위한 보조 지표로만 사용한다.

논문 수는 원값을 그대로 쓰지 않고 로그 처리한다.

```text
Productivity Score = log(1 + related_paper_count)
```

이를 통해 논문 10편과 100편의 차이가 추천 결과에 10배로 반영되는 문제를 방지한다.

또한 연구자 영향력은 모든 논문을 단순 합산하지 않고, 상위 논문 중심으로 집계한다.

```text
Author Impact Score
= 상위 N개 관련 논문의 Paper Evidence Weight 평균
+ 전체 관련 논문의 보정 합산값
+ 최고 영향 논문 점수
```

세부 방식은 **붙임 2. 연구자 점수 집계 상세 설계**에 둔다.

---

## 11-5. 역할 기반 연구자 추천

K2KM은 연구자를 하나의 종합점수로만 줄 세우지 않는다. 연구자는 해당 키워드 생태계에서 수행하는 역할에 따라 분류한다.

| 역할 라벨 | 의미 |
| --- | --- |
| Core Influencer | 해당 키워드 분야에서 영향력 높은 논문을 보유한 핵심 연구자 |
| Bridge Researcher | 서로 다른 연구 클러스터를 연결하는 연구자 |
| Productive Contributor | 관련 논문을 꾸준히 생산한 연구자 |
| Emerging Researcher | 최근 빠르게 부상하는 연구자 |
| Niche Specialist | 특정 세부 클러스터에서 강한 전문성을 보이는 연구자 |
| Domestic R&D Actor | 국내 국가R&D 과제·기관 구조와 관련성이 높은 연구자 |
| Strategic Connector | 글로벌 학술 영향력과 국내 R&D 연계성이 모두 높은 연구자 |

각 역할의 세부 판정 조건은 **붙임 3. 연구자 역할 라벨링 상세 기준**에 둔다.

---

## 11-6. 글로벌 연구자와 국내 연구자 비교 원칙

글로벌 연구자와 국내 연구자를 하나의 단일 점수로 비교하지 않는다.

글로벌 학술 생태계에서의 영향력과 국내 국가R&D 구조에서의 관련성은 성격이 다르기 때문이다.

따라서 K2KM은 다음의 이중축 비교 구조를 사용한다.

```text
Y축: Global Scholarly Impact
X축: Domestic R&D Relevance
```

| 유형 | 해석 | 정책 활용 |
| --- | --- | --- |
| 글로벌 높음 + 국내 높음 | 전략적 핵심 연구자 | 자문·기획·협력 우선 후보 |
| 글로벌 높음 + 국내 낮음 | 글로벌 선도 연구자 | 국내 유입·협력 검토 |
| 글로벌 낮음 + 국내 높음 | 국내 실행·정책형 연구자 | 현장성·사업 이해도 높은 후보 |
| 글로벌 낮음 + 국내 낮음 | 낮은 우선순위 | 추가 검토 또는 제외 |

이 구조는 국내 연구자의 정책적 가치를 글로벌 논문 인용 지표만으로 과소평가하지 않기 위한 장치이다.

---

## 11-7. 추천 결과 설명 원칙

K2KM은 연구자를 추천할 때 반드시 추천 근거를 함께 제공한다.

예시:

```text
추천 근거
- 입력 키워드 관련 논문 12편
- 영향력 상위 논문 3편
- 클러스터 A와 B를 연결하는 betweenness 상위권
- 최근 3년 관련 논문 지속 생산
- 국내 NTIS 과제 2건과 주제 유사도 높음
```

다음 표현은 사용하지 않는다.

```text
이 연구자는 세계 최고입니다.
이 연구자가 가장 우수합니다.
이 연구자는 반드시 자문위원으로 위촉해야 합니다.
국내 연구 수준이 낮습니다.
한국은 뒤처져 있습니다.
```

권장 표현은 다음과 같다.

```text
이 연구자는 해당 키워드 네트워크에서 영향력 높은 논문을 보유하고 있습니다.
이 연구자는 서로 다른 연구 클러스터를 연결하는 브리지 역할을 합니다.
이 연구자는 최근 관련 연구 활동이 증가하고 있어 신흥 연구자로 검토할 수 있습니다.
이 연구자는 글로벌 논문 영향력은 제한적이지만, 국내 국가R&D 과제와의 관련성이 높게 나타납니다.
```

상세 설명 템플릿은 **붙임 6. 추천 설명 및 주의 문구 템플릿**에 둔다.

---

## 11-8. 품질 낮은 대량 생산자 방지 장치

단순 논문 수 기반 추천 왜곡을 방지하기 위해 다음 장치를 적용한다.

| 장치 | 설명 |
| --- | --- |
| Relevance Gate | 입력 키워드와 관련성이 낮은 논문은 점수 계산에서 제외 |
| Low-impact Ratio | 저영향 논문 비중이 높은 연구자 감점 |
| Top-N 중심 집계 | 전체 논문이 아니라 상위 관련 논문 중심으로 영향력 계산 |
| 논문 수 로그 보정 | 대량 논문 생산자의 점수 폭주 방지 |
| 역할별 탭 분리 | 영향력, 브리지, 신흥, 국내 R&D 역할을 분리 표시 |
| 주의 플래그 | 저자 매칭 오류, 메타데이터 부족, 과거 영향력 편중 등을 표시 |

세부 기준은 **붙임 4. 품질 왜곡 방지 및 신뢰도 플래그 설계**에 둔다.

---

## 11-9. NTIS Overlay와의 결합

NTIS는 Global Scholarly Core에 직접 강결합하지 않는다.

기존 원칙대로 다음 구조를 유지한다.

```text
Global Scholarly Core
+
Domestic NTIS Overlay
+
Comparative Intelligence Layer
```

국내 R&D 관련성은 별도의 지표로 산정한다.

| 구성 요소 | 의미 |
| --- | --- |
| NTIS Project Topical Similarity | 과제명·연구요약과 키워드/글로벌 클러스터의 유사도 |
| Domestic Institution Centrality | 국내 기관 협력 네트워크 내 중심성 |
| Researcher Matching Confidence | 연구자 이름·기관·주제 기반 매칭 신뢰도 |
| Program Relevance | 관련 사업군과의 정책적 연계성 |
| Recent Project Activity | 최근 과제 수행 여부 |

상세 계산식은 **붙임 5. NTIS Overlay 기반 Domestic R&D Relevance 설계**에 둔다.

---

## 11-10. 본문 설계 원칙 요약

```text
K2KM의 연구자 추천은 단순 논문 수 기반 랭킹이 아니라,
입력 키워드와의 관련성, 논문별 영향력, 네트워크 내 구조적 역할,
최근 연구 활동성, 데이터 신뢰도, 국내 국가R&D 연계성을 종합적으로 고려하는
역할 기반 추천 모델로 설계한다.

논문 수는 생산성 참고 지표로만 활용하며,
저영향 논문 대량 생산으로 인한 추천 왜곡을 방지하기 위해
논문별 Paper Evidence Weight, 관련성 threshold, 상위 N개 논문 중심 집계,
Low-impact Ratio 패널티를 적용한다.

연구자는 단일 우수성 순위로 제시하지 않고,
Core Influencer, Bridge Researcher, Emerging Researcher,
Niche Specialist, Domestic R&D Actor, Strategic Connector 등
역할 라벨로 분류한다.

또한 글로벌 연구자와 국내 연구자를 하나의 단일 점수로 비교하지 않고,
Global Scholarly Impact와 Domestic R&D Relevance의 이중 축에서 비교한다.
이를 통해 글로벌 학술 영향력과 국내 국가R&D 정책 활용성을 구분하면서도,
양자를 연결할 수 있는 전략적 후보를 도출한다.
```

---
# 12. 웹앱 전략

## 12-1. 기본 원칙

이 프로젝트는 단순 그래프 시각화 도구가 아니다.

핵심은:

- 구조 요약
- 연구 탐색
- 정책 탐색
- 글로벌 vs 국내 비교분석
- 해설 제공

이다.

---

## 12-2. 주요 화면

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

### ⑥ 연구자 추천 화면

세부:

- Core Influencer
- Bridge Researcher
- Emerging Researcher
- Niche Specialist
- Domestic R&D Actor
- Strategic Connector
- 추천 근거 및 주의 플래그

### ⑦ Global Impact × Domestic R&D Relevance 매트릭스

세부:

- 글로벌 학술 영향력 높은 연구자
- 국내 R&D 연계성 높은 연구자
- 글로벌-국내 연결 후보
- 국내 공백 영역의 해외 협력 후보

### ⑧ 블로그형 설명 페이지

---

# 13. 블로그 전략

## 13-1. 역할 정의

블로그는 “새 분석”이 아니다.

이미 생성된 분석 결과를:

- 쉬운 언어로
- 구조적으로
- 일반인이 이해 가능하게

재구성하는 계층이다.

---

## 13-2. 설명 원칙

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

# 14. 시스템 아키텍처 개요

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

# 15. 대용량 처리 전략

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

# 16. 구현 로드맵

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
- Paper Evidence Weight 계산
- 연구자 역할 라벨링 1차 구현

---

## Phase 4

- 공개 API
- 웹앱 UI
- 그래프 시각화
- 연구자 추천 화면
- 추천 근거 및 주의 플래그 표시
- Global Impact × Domestic R&D Relevance 매트릭스 화면

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
- Domestic R&D Relevance 계산
- Comparative Layer 구축
- niche/gap/alignment 분석
- Strategic Connector 도출
- 국내 R&D 연구자 역할 라벨링

---

# 17. 핵심 리스크 및 대응

| 리스크                       | 대응                        |
| ------------------------- | ------------------------- |
| 데이터 품질 불균일                | source 병합 + null 처리       |
| 키워드 노이즈                   | threshold + 정제            |
| 그래프 과밀                    | sampling/filtering        |
| 과장 해석                     | 패턴/경향 중심 설명               |
| 대량 처리 비용                  | async worker + large mode |
| 연구자 매칭 오류                 | confidence score 기반 처리    |
| NTIS와 scholarly graph 강결합 | overlay 구조 유지             |
| 단순 논문 수 기반 추천 왜곡 | Paper Evidence Weight + Top-N 집계 + Low-impact Ratio 적용 |
| 매튜 효과로 인한 대가 중심 쏠림 | Emerging/Niche/Bridge 역할 탭 분리 |
| 국내 연구자 과소평가 | Global Scholarly Impact와 Domestic R&D Relevance 이중축 비교 |
| 추천 결과 과신 | 추천 근거, 주의 플래그, 매칭 신뢰도 동시 제공 |

---

# 18. 최종 결론

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

v2에서 추가된 연구자 추천 모델의 핵심은 다음과 같다.

> “많이 쓴 연구자”가 아니라, 특정 키워드의 연구 생태계 안에서 “의미 있는 역할을 수행하는 연구자”를 찾는다.

이를 위해 K2KM은 논문별 Paper Evidence Weight, 연구자 역할 라벨링, 국내 R&D Overlay, Global Scholarly Impact × Domestic R&D Relevance 이중축 비교를 결합한다.



---

# 붙임 1. Paper Evidence Weight 상세 설계

## 1-1. 정의

Paper Evidence Weight는 논문 자체의 절대적 우수성을 의미하지 않는다. 특정 키워드 분석에서 해당 논문을 얼마나 중요한 근거로 활용할 것인지 나타내는 분석용 가중치이다.

## 1-2. 기본 계산식

```text
Paper Evidence Weight
=
0.30 × Topical Relevance
+ 0.25 × Normalized Citation Impact
+ 0.20 × Network Centrality
+ 0.10 × Knowledge Transfer
+ 0.10 × Recency / Momentum
+ 0.05 × Reliability
```

MVP에서는 다음과 같이 단순화한다.

```text
Paper Evidence Weight MVP
=
0.35 × Topical Relevance
+ 0.30 × Citation Impact
+ 0.20 × Paper PageRank
+ 0.10 × Recency
+ 0.05 × Reliability
```

## 1-3. Topical Relevance

```text
Topical Relevance
=
0.30 × title_similarity
+ 0.35 × abstract_embedding_similarity
+ 0.15 × keyword_match_score
+ 0.10 × topic_match_score
+ 0.10 × cluster_relevance_score
```

입력 키워드와 관련성이 낮은 논문은 점수 계산에서 제외한다.

추천 threshold는 다음과 같다.

| 모드 | threshold |
| --- | ---: |
| broad search | 0.45 |
| standard search | 0.55 |
| strict search | 0.65 |

## 1-4. Normalized Citation Impact

```text
Normalized Citation Impact
=
0.40 × citation_percentile_score
+ 0.30 × FWCI_score
+ 0.20 × log_cited_by_count
+ 0.10 × citation_velocity
```

단순 인용 수는 분야, 연도, 출판유형에 따라 편향될 수 있으므로 가능하면 분야·연도 보정 지표를 우선한다.

## 1-5. Network Centrality

```text
Network Centrality
=
0.40 × paper_pagerank
+ 0.25 × eigenvector
+ 0.25 × betweenness
+ 0.10 × weighted_degree
```

## 1-6. Knowledge Transfer

```text
Knowledge Transfer
=
0.50 × influential_citation_score
+ 0.30 × citing_cluster_diversity
+ 0.20 × reference_diversity
```

## 1-7. Recency / Momentum

```text
Recency / Momentum
=
0.35 × publication_recency
+ 0.35 × recent_citation_velocity
+ 0.20 × cluster_growth_score
+ 0.10 × emerging_topic_flag
```

## 1-8. Reliability

```text
Reliability
=
0.30 × venue_confidence
+ 0.25 × metadata_completeness
+ 0.25 × source_type_score
+ 0.20 × non_retracted_flag
```

---

# 붙임 2. 연구자 점수 집계 상세 설계

## 2-1. 기본 구조

```text
Author Paper Contribution
=
Paper Evidence Weight
× Author Contribution Weight
× Topical Relevance Gate
```

## 2-2. 저자 기여도 가중치

| 조건 | 가중치 |
| --- | ---: |
| 1저자 | 1.00 |
| 교신저자 | 1.00 |
| 단독저자 | 1.20 |
| 중간저자 | 0.50 |
| 마지막저자 | 0.70~1.00 |
| 저자 순서 정보 없음 | 1 / 저자 수 |
| 대형 공동저자 논문 | log 또는 sqrt로 희석 |

대형 공동저자 논문은 다음과 같이 보정한다.

```text
Adjusted Contribution Weight
=
Base Contribution Weight / sqrt(number_of_authors)
```

또는:

```text
Adjusted Contribution Weight
=
Base Contribution Weight / log(1 + number_of_authors)
```

## 2-3. 연구자 영향력 점수

모든 논문을 단순 합산하지 않고 상위 논문 중심으로 집계한다.

```text
Author Impact Score
=
0.60 × Top-N Paper Average
+ 0.25 × Weighted Sum of All Related Papers
+ 0.15 × Best Paper Score
```

기본값:

```text
Top-N = min(10, related_paper_count)
```

## 2-4. 글로벌 학술 영향력

```text
Global Scholarly Impact
=
0.30 × Author Topical Relevance
+ 0.30 × Author Impact Score
+ 0.20 × Author Structural Score
+ 0.10 × Author Momentum Score
+ 0.10 × Author Reliability Score
```

## 2-5. 저자 구조적 점수

```text
Author Structural Score
=
0.35 × author_pagerank
+ 0.30 × author_betweenness
+ 0.20 × author_eigenvector
+ 0.15 × weighted_degree
```

---

# 붙임 3. 연구자 역할 라벨링 상세 기준

## 3-1. Core Influencer

조건:

```text
Author Impact Score 상위 10%
AND Paper Evidence Weight 상위 논문 2편 이상
AND Topical Relevance 일정 기준 이상
```

설명:

```text
해당 키워드와 관련된 고영향 논문을 보유하고 있으며,
관련 연구 클러스터 내 영향력이 높게 나타나는 연구자입니다.
```

## 3-2. Bridge Researcher

조건:

```text
Author Betweenness 상위 10%
AND 2개 이상 클러스터에 관련 논문 존재
```

설명:

```text
서로 다른 연구 클러스터를 연결하는 위치에 있는 연구자입니다.
융합 주제 또는 분야 간 연결 가능성을 탐색할 때 유용합니다.
```

## 3-3. Productive Contributor

조건:

```text
관련 논문 수 상위 10%
AND 평균 Paper Evidence Weight가 하위권이 아님
```

주의:

```text
단순 논문 수만 많고 영향력 지표가 낮으면 Productive Contributor로도 표시하지 않음.
```

## 3-4. Emerging Researcher

조건:

```text
최근 3~5년 관련 논문 수 증가
OR 최근 citation velocity 증가
OR emerging cluster 내 중심성 상승
```

## 3-5. Niche Specialist

조건:

```text
전체 글로벌 영향력은 중간 이하일 수 있음
BUT 특정 세부 클러스터 내 집중도 높음
AND 해당 클러스터의 niche score 높음
```

## 3-6. Domestic R&D Actor

조건:

```text
NTIS 관련 과제 참여
OR 국내 기관 네트워크 중심성 높음
OR 국내 과제 요약과 글로벌 클러스터 유사도 높음
```

## 3-7. Strategic Connector

조건:

```text
Global Scholarly Impact 높음
AND Domestic R&D Relevance 높음
```

---

# 붙임 4. 품질 왜곡 방지 및 신뢰도 플래그 설계

## 4-1. Low-impact Ratio

```text
Low-impact Ratio
=
하위 30% Paper Evidence Weight 논문 수
/
전체 관련 논문 수
```

| Low-impact Ratio | 처리 |
| ---: | --- |
| 0.0 ~ 0.3 | 감점 없음 |
| 0.3 ~ 0.5 | 약한 감점 |
| 0.5 ~ 0.7 | 중간 감점 |
| 0.7 이상 | 강한 감점 |

## 4-2. Quality-adjusted Productivity

```text
Quality-adjusted Productivity
=
log(1 + related_paper_count)
× average_paper_evidence_weight
```

## 4-3. Caution Flags

| 플래그 | 조건 |
| --- | --- |
| LOW_AUTHOR_CONFIDENCE | 저자 매칭 신뢰도 낮음 |
| LOW_METADATA_COMPLETENESS | 초록·DOI·소속 등 부족 |
| HIGH_LOW_IMPACT_RATIO | 저영향 논문 비중 높음 |
| OLD_IMPACT_ONLY | 최근 활동성 낮음 |
| LOW_TOPICAL_RELEVANCE | 일부 고인용 논문의 키워드 관련성 낮음 |
| DOMESTIC_MATCH_UNCERTAIN | NTIS 연구자 매칭 불확실 |
| VENUE_UNCERTAIN | 출처 신뢰도 낮음 |
| POSSIBLE_NAME_COLLISION | 동명이인 가능성 높음 |

---

# 붙임 5. NTIS Overlay 기반 Domestic R&D Relevance 설계

## 5-1. 기본 구조

```text
Domestic R&D Relevance
=
0.30 × NTIS Project Topical Similarity
+ 0.25 × Domestic Institution Centrality
+ 0.20 × Researcher Matching Confidence
+ 0.15 × Program Relevance
+ 0.10 × Recent Project Activity
```

## 5-2. NTIS Project Topical Similarity

```text
NTIS Project Topical Similarity
=
embedding_similarity(과제명 + 연구요약, 글로벌 클러스터 설명)
```

또는:

```text
embedding_similarity(과제명 + 연구요약, 사용자 입력 키워드)
```

## 5-3. Author Matching Confidence

```text
Author Matching Confidence
=
0.30 × persistent_id_match
+ 0.20 × affiliation_consistency
+ 0.20 × coauthor_pattern_similarity
+ 0.15 × topic_profile_similarity
+ 0.10 × publication_time_consistency
+ 0.05 × name_string_similarity
```

| 점수 | 등급 | 처리 |
| ---: | --- | --- |
| 0.85 이상 | High | 자동 매칭 |
| 0.70 ~ 0.85 | Medium | 추천에는 사용하되 주의 표시 |
| 0.50 ~ 0.70 | Low | 내부 분석만 사용, UI 표시 제한 |
| 0.50 미만 | Reject | 매칭 제외 |

---

# 붙임 6. 추천 설명 및 주의 문구 템플릿

## 6-1. 추천 설명 템플릿

```text
{연구자명}은/는 {키워드} 관련 연구 생태계에서 {역할라벨}로 분류됩니다.

주요 근거는 다음과 같습니다.
1. 입력 키워드와 관련성이 높은 논문 {n}편 보유
2. 영향력 상위 논문 {m}편 포함
3. {클러스터명} 클러스터 내 중심성 높음
4. 최근 {기간} 동안 관련 연구 활동 {증가/유지/감소}
5. 국내 R&D 연계성은 {높음/보통/낮음}

따라서 이 연구자는 {정책기획/기술동향분석/협력후보탐색/국내역량분석} 관점에서 검토할 수 있습니다.
```

## 6-2. 주의 문구 예시

```text
주의
- 이 연구자는 과거 고영향 논문이 추천 점수에 크게 반영되었습니다.
- 최근 5년 활동성은 상대적으로 낮습니다.
```

```text
주의
- 국내 NTIS 연구자 매칭 신뢰도가 보통 수준입니다.
- 동일 이름 연구자가 존재할 가능성이 있습니다.
```

---

# 붙임 7. DB 및 API 설계 초안

## 7-1. 주요 테이블

```text
analysis_runs
keywords
papers
authors
paper_authors
institutions
venues
paper_metrics
author_metrics
paper_network_edges
author_network_edges
clusters
cluster_memberships
ntis_projects
ntis_project_researchers
ntis_project_institutions
domestic_mappings
recommendation_results
recommendation_explanations
```

## 7-2. paper_metrics

| 컬럼 | 설명 |
| --- | --- |
| paper_id | 논문 ID |
| analysis_run_id | 분석 ID |
| topical_relevance | 키워드 관련성 |
| cited_by_count | 피인용 수 |
| fwci | FWCI |
| citation_percentile | 분야·연도 보정 percentile |
| influential_citation_count | 영향력 있는 인용 수 |
| pagerank | 논문 PageRank |
| betweenness | 논문 Betweenness |
| evidence_weight | 최종 Paper Evidence Weight |
| reliability_score | 신뢰도 점수 |

## 7-3. author_metrics

| 컬럼 | 설명 |
| --- | --- |
| author_id | 저자 ID |
| analysis_run_id | 분석 ID |
| related_paper_count | 관련 논문 수 |
| productivity_score | 생산성 점수 |
| author_impact_score | 영향력 점수 |
| structural_score | 구조적 점수 |
| momentum_score | 최신성 점수 |
| reliability_score | 신뢰도 점수 |
| global_scholarly_impact | 글로벌 학술 영향력 |
| domestic_rnd_relevance | 국내 R&D 관련성 |
| low_impact_ratio | 저영향 논문 비율 |

## 7-4. 추천 연구자 조회 API

```http
GET /api/analysis-runs/{analysis_run_id}/recommended-authors
```

쿼리 예시:

```text
role=core_influencer
limit=20
country=KR
cluster_id=cluster_03
```

응답 예시:

```json
{
  "role": "core_influencer",
  "authors": [
    {
      "author_id": "auth_001",
      "name": "Example Researcher",
      "primary_institution": "Example University",
      "country": "US",
      "role_labels": ["Core Influencer", "Bridge Researcher"],
      "global_scholarly_impact": 0.87,
      "domestic_rnd_relevance": 0.12,
      "matching_confidence": 0.94,
      "evidence_summary": {
        "related_paper_count": 18,
        "top_paper_count": 4,
        "top_clusters": ["AI policy", "algorithmic accountability"],
        "recent_activity": "high"
      }
    }
  ]
}
```

---

# 붙임 8. 최종 설계 요약

```text
1. 단순 논문 수 추천은 폐기한다.
2. 논문별 Paper Evidence Weight를 도입한다.
3. 연구자 점수는 상위 논문 중심으로 집계한다.
4. 논문 수는 log 보정된 생산성 지표로만 사용한다.
5. 연구자는 단일 순위가 아니라 역할 라벨로 분류한다.
6. 글로벌 영향력과 국내 R&D 연계성은 2축으로 분리한다.
7. NTIS는 강결합하지 않고 Overlay Layer로 유지한다.
8. 추천 결과에는 반드시 설명과 주의 플래그를 제공한다.
```

K2KM은 “많이 쓴 연구자”를 찾는 서비스가 아니라, 특정 키워드의 연구 생태계 안에서 “의미 있는 역할을 수행하는 연구자”를 찾아주는 전략 지도 서비스이다.
