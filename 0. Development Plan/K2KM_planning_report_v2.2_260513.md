# 키워드 기반 연구구조 분석·아카이브 플랫폼 구축 기획보고서 v2.2

## Keyword-to-Knowledge Map (K2KM) + NTIS Comparative Layer

> 본 v2.2는 기존 v2.1 기획보고서에 **분석 결과 공개 범위 및 민감도 관리 원칙**, **연구비·기관·연구자 정보의 접근 등급 체계**, **MVP/고도화 권한 모델**을 추가 반영한 개정안이다.

---

# 0. v2.2 개정 요약

## 0-1. 개정 목적

v1은 키워드 기반 글로벌 연구구조 분석과 NTIS Overlay 기반 국내 R&D 비교분석 구조를 제시하였다. v2는 여기에 연구자 추천 과정에서 발생할 수 있는 **단순 논문 수 기반 왜곡**을 방지하기 위한 품질 보정 로직을 추가하였다.

v2.1은 v2의 연구자 추천·품질 보정 모델을 유지하면서, 실제 웹서비스 구현 단계에서 필요한 **그래프 시각화 구현 전략**을 추가하였다. 특히 Gephi 데스크톱 소스를 웹앱에 직접 이식하는 방식은 지양하고, K2KM 전용 웹 그래프 뷰어는 **sigma.js + graphology** 기반으로 구현하며, Gephi 생태계와의 호환성은 **GEXF/JSON Export**로 확보하는 방향을 반영하였다.

v2.2는 v2.1의 기본 구조를 유지하면서, 공개 웹서비스로 운영할 때 발생할 수 있는 **개인·기관·연구비 정보의 민감도 문제**를 반영한다. 이를 위해 분석 결과를 Public, Registered, Verified Professional, Admin/Internal, Hidden/System-only의 접근 등급으로 구분하고, 연구자 순위·상세 점수·개인별 연구비 연결값 등은 공개하지 않는 원칙을 추가한다.

## 0-2. 본문 반영 사항과 부록 분리 사항

| 구분 | 반영 위치 | 내용 |
| --- | --- | --- |
| 본문 반영 | 제10장~제19장 | 서비스 원칙, 연구자 추천 철학, 역할 라벨, 글로벌-국내 2축 비교, 웹 그래프 시각화 전략, 공개 범위 및 민감도 관리, UI/로드맵/리스크 반영 |
| 부록 반영 | 붙임 1~10 | 계산식, 가중치, DB 설계, API 설계, 상세 파이프라인, 추천 설명 템플릿, 주의 플래그, 그래프 시각화 구현 상세, 접근 등급 매핑 |

## 0-3. v2.1 핵심 변경 사항

1. 단순 논문 수 기반 연구자 추천을 지양한다.
2. 논문별 **Paper Evidence Weight**를 도입한다.
3. 연구자는 단일 순위가 아니라 역할 기반으로 분류한다.
4. 글로벌 연구자와 국내 연구자는 하나의 단일 점수로 비교하지 않는다.
5. **Global Scholarly Impact × Domestic R&D Relevance** 이중축 비교를 적용한다.
6. NTIS는 기존 원칙대로 Global Scholarly Core에 강결합하지 않고 Overlay Layer로 유지한다.
7. 추천 결과에는 반드시 추천 근거와 주의 플래그를 함께 제공한다.
8. K2KM 웹 그래프 뷰어는 **sigma.js + graphology** 기반으로 구현한다.
9. Gephi 데스크톱 소스를 웹앱에 직접 이식하지 않는다.
10. Gephi 호환성은 **GEXF Export**, JSON Export, 분석 검증용 활용으로 확보한다.
11. 대형 그래프는 브라우저에서 실시간 레이아웃을 계산하지 않고, Backend/Worker에서 좌표를 사전 계산해 제공한다.
12. 연구자·기관·연구비 관련 정보는 공개 민감도에 따라 접근 등급을 구분한다.
13. 연구자 상세 점수, 절대 순위, 개인별 연구비 연결값은 공개하지 않는다.
14. 연구비는 단순 총액 순위가 아니라 국내 R&D 포지셔닝을 설명하는 보조 신호로 사용한다.
15. MVP에서는 Public, Admin/Internal, Hidden/System-only 중심으로 단순 운영하고, 고도화 단계에서 Registered와 Verified Professional 등급을 도입한다.

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
- 해설 요약 리포트 생성 및 향후 공개 콘텐츠 확장
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
- 해설 요약 리포트

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
- 해설 요약 리포트 생성

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

### ④ 국내 R&D 포지셔닝 분석

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

### ⑧ 해설 요약 리포트 페이지

---

## 12-3. 그래프 시각화 구현 전략

K2KM의 웹 그래프 시각화는 Gephi 데스크톱 애플리케이션 소스를 직접 웹앱에 이식하는 방식으로 구현하지 않는다.

Gephi는 대규모 네트워크 분석과 시각화에 강점이 있는 데스크톱 기반 도구로, 내부 분석·검증·파일 호환성 측면에서는 유용하지만, Next.js 기반 공개 웹서비스의 프론트엔드 렌더링 엔진으로 직접 사용하는 것은 적합하지 않다.

따라서 K2KM은 다음 원칙을 따른다.

```text
웹 렌더링 엔진
→ sigma.js + graphology 채택

분석·레이아웃 계산
→ Backend / Worker / NetworkX / igraph에서 수행

Gephi 활용
→ GEXF Export, 내부 검증, 고급 분석자용 다운로드 지원
```

### 12-3-1. 그래프 시각화 기술 선택

| 구분 | 판단 | 비고 |
| --- | --- | --- |
| gephi/gephi 데스크톱 소스 직접 이식 | 비추천 | Java/OpenGL/NetBeans 기반으로 웹 프론트엔드와 결합 비용이 큼 |
| gephi-lite Fork | 조건부 가능 | 웹 기반이지만 K2KM 서비스 구조에 맞게 대폭 수정 필요 |
| sigma.js + graphology 직접 적용 | 추천 | React/Next.js 웹앱에 적합하며 대규모 네트워크 탐색 UI 구현에 유리 |
| Cytoscape.js | 보조 검토 | 생물정보·관계망 UI에 강점, 대형 그래프 성능은 별도 검토 필요 |
| Gephi Export | 추천 | GEXF 파일 제공을 통해 외부 분석 도구와 호환성 확보 |

### 12-3-2. K2KM 그래프 뷰어의 역할

K2KM의 그래프 뷰어는 단순히 노드와 엣지를 화면에 그리는 도구가 아니다.

주요 역할은 다음과 같다.

- 연구 클러스터 구조 탐색
- 핵심 논문과 브리지 논문 확인
- 연구자 역할 라벨과 네트워크 위치 연결
- 글로벌 연구구조와 국내 NTIS Overlay 비교
- Niche, Gap, Alignment 영역 시각화
- 추천 근거를 그래프 상에서 검증 가능하게 제공

### 12-3-3. 그래프별 화면 구성

| 화면 | 그래프 | 노드 | 엣지 | 주요 기능 |
| --- | --- | --- | --- | --- |
| Global Research Map | 논문 네트워크 | 논문 | citation, co-citation, bibliographic coupling, semantic similarity | 핵심 논문, 클러스터, 연구 흐름 확인 |
| Author Map | 저자 네트워크 | 연구자 | 공동저술, citation-induced relation, cluster co-presence | Core/Bridge/Emerging 연구자 탐색 |
| Keyword Map | 키워드 네트워크 | 키워드 | co-occurrence, embedding similarity | 세부 주제와 융합 주제 확인 |
| Domestic R&D Map | NTIS 과제 네트워크 | 과제 | 공통 연구분야, 공통 기관, 공통 연구자 | 국내 과제 구조 확인 |
| Institution Map | 기관 네트워크 | 기관 | 공동논문, 공동과제, 동일사업 참여 | 국내외 기관 협력 구조 확인 |
| Global vs Korea Map | 비교 레이어 | 클러스터/기관/연구자 | 유사도, 정렬도, 공백 관계 | Niche, Gap, Alignment 분석 |

### 12-3-4. 대형 그래프 렌더링 원칙

대형 그래프는 브라우저에서 모든 계산을 수행하지 않는다.

```text
Backend / Worker
- 그래프 생성
- 중심성 계산
- 클러스터링
- 레이아웃 좌표 계산
- 노드 크기·색상·라벨 우선순위 계산

Frontend
- 렌더링
- 필터링
- 검색
- 하이라이트
- 상세 패널 표시
```

특히 20,000건 이상의 Large Mode에서는 다음 원칙을 적용한다.

- 전체 그래프를 한 번에 보여주지 않는다.
- Summary-first UI를 우선 제공한다.
- 클러스터별 Drill-down 방식을 적용한다.
- 노드 표시 threshold를 둔다.
- 엣지 타입별 필터를 제공한다.
- 중요 노드와 대표 엣지를 우선 렌더링한다.
- 전체 데이터는 Export로 제공하고, 화면에는 탐색 가능한 축약 그래프를 제공한다.

### 12-3-5. Export 전략

K2KM은 웹에서 직접 탐색할 수 있는 그래프뿐 아니라 외부 분석 도구에서 재사용 가능한 파일을 제공한다.

| Export 형식 | 용도 |
| --- | --- |
| JSON | K2KM 웹앱 재사용, API 연계 |
| GEXF | Gephi Desktop, Gephi Lite 등 외부 그래프 도구 호환 |
| CSV Nodes/Edges | 연구자·기관·논문 네트워크 후처리 |
| PNG/SVG | 보고서·블로그 삽입용 정적 이미지 |

Gephi는 K2KM의 웹 렌더링 엔진이 아니라, 고급 사용자가 K2KM 분석 결과를 추가 탐색할 수 있도록 지원하는 **외부 호환 도구**로 위치시킨다.

---


# 13. 공개 범위 및 민감도 관리

## 13-1. 기본 원칙

K2KM은 공개 웹서비스를 지향하지만, 모든 분석 결과를 동일한 수준으로 공개하지 않는다.

특히 연구자, 국내 기관, 연구비, 연구자-과제 매칭 정보는 맥락 없이 공개될 경우 개인·기관 평가나 순위화로 오해될 수 있다. 따라서 K2KM은 분석 결과를 공개 민감도에 따라 구분하고, 사용자 유형에 따라 접근 범위를 달리한다.

핵심 원칙은 다음과 같다.

| 원칙 | 내용 |
| --- | --- |
| 순위화 방지 | 연구자·기관의 절대 순위와 종합점수는 공개하지 않는다. |
| 설명 중심 공개 | 역할 라벨, 추천 근거, 클러스터 맥락, 주의 플래그 중심으로 제공한다. |
| 개인 정보 신중 처리 | 국내 연구자 관련 정보는 공개 범위를 제한한다. |
| 연구비 오해 방지 | 연구비는 성과평가가 아니라 투자 집중도와 포지셔닝 분석의 보조 신호로 사용한다. |
| 단계적 접근 | 일반 공개, 인증 사용자, 검증 전문가, 내부 관리자, 시스템 내부값을 구분한다. |
| 한계 명시 | 매칭 오류, 데이터 누락, 해석 한계를 함께 표시한다. |

---

## 13-2. 접근 등급 체계

K2KM의 분석 결과는 다음 5개 접근 등급으로 구분한다.

| 등급 | 의미 | 접근 주체 | 예시 |
| --- | --- | --- | --- |
| Public | 누구나 볼 수 있는 공개 정보 | 일반 방문자 | 글로벌 연구 클러스터, 논문 네트워크 요약, Gap/Niche/Alignment 요약 |
| Registered | 로그인 사용자에게 제공하는 정보 | 가입·인증 사용자 | 분석 저장, 재분석 이력, 고급 필터, 일부 Export 기능 |
| Verified Professional | 업무 목적이 확인된 사용자에게 제공하는 정보 | 정책기획자, 연구기획자, 전문기관 실무자 등 | 국내 기관/사업 단위 상세 분석, 국내 연구자 후보, 연구비 비중 정보 |
| Admin/Internal | 서비스 운영자와 내부 검증자만 확인하는 정보 | 운영자, 관리자 | 상세 점수, 연구자 매칭 신뢰도, 오류 후보 데이터, 연구비 원자료 |
| Hidden/System-only | 화면에는 표시하지 않고 계산에만 사용하는 정보 | 시스템 내부 | 내부 ranking score, 알고리즘 중간값, 개인별 연구비 연결값 |

`Limited`라는 모호한 표현은 사용하지 않는다. 제한 공개가 필요한 경우에는 Registered, Verified Professional, Admin/Internal 중 하나로 명확히 구분한다.

---

## 13-3. MVP 접근 등급

MVP 단계에서는 권한 체계를 지나치게 복잡하게 구현하지 않는다.

MVP에서는 다음 3단계로 시작한다.

| MVP 등급 | 의미 | 처리 |
| --- | --- | --- |
| Public | 일반 공개 | 클러스터, 요약, 공개 가능한 그래프와 해설 제공 |
| Admin/Internal | 운영자 확인 | 상세 점수, 매칭 신뢰도, 연구비 원자료, 오류 검토 |
| Hidden/System-only | 시스템 계산 전용 | 내부 종합점수, ranking score, 개인별 연구비 연결값 |

서비스 고도화 단계에서 Registered와 Verified Professional 등급을 추가한다.

---

## 13-4. 연구비 지표 공개 원칙

연구비는 국내 R&D 포지셔닝 분석에서 중요한 정보이지만, 단순 총액은 연구의 전략적 중요도나 글로벌 정렬도를 직접 의미하지 않는다.

연구비는 사업 유형, 장비·인프라성 과제, 실증 과제, 정책연구, 기초연구, 계속과제 여부에 따라 규모가 크게 달라진다. 따라서 연구비를 단순 합산하거나 기관·사업별 순위로 제시하면 투자 구조 분석이 아니라 성과평가 또는 서열화처럼 해석될 위험이 있다.

K2KM에서 연구비는 다음 원칙에 따라 사용한다.

| 정보 | 접근 등급 | 원칙 |
| --- | --- | --- |
| 클러스터별 투자 집중도 요약 | Public | 국내 R&D가 어떤 클러스터에 상대적으로 집중되어 있는지 설명 |
| 연구비 비중/구간 | Verified Professional | 맥락을 이해할 수 있는 정책·연구기획 사용자에게 제공 |
| 사업별 연구비 총액 | Admin/Internal 또는 Verified Professional | 공개 시 사업 평가처럼 보일 수 있으므로 제한 |
| 기관별 연구비 총액 | Admin/Internal | 기관 서열화 가능성이 있어 일반 공개하지 않음 |
| 연구자별 연구비 연결 | Hidden/System-only 또는 Admin/Internal | 개인 평가로 오해될 수 있어 공개하지 않음 |
| 투자 대비 성과 | 제공하지 않음 | K2KM의 목적을 벗어나므로 산출하지 않음 |

권장 표현:

```text
이 클러스터는 국내 R&D 과제와 투자 집중도가 상대적으로 높게 나타납니다.
```

금지 표현:

```text
A기관은 이 분야에서 연구비를 가장 많이 받았습니다.
B사업은 투자 대비 성과가 낮습니다.
```

향후 dBrain 등 재정·사업 구조 데이터와 연동하는 경우, 연구비는 단순 총액이 아니라 다음과 같은 보정 지표로 고도화한다.

```text
Funding Signal
= 클러스터별 투자 비중
+ 최근 증가율
+ 사업유형 보정
+ 대형과제 영향 완화
+ 연도·부처·과제규모 보정
```

---

## 13-5. 국내 기관 정보 공개 원칙

국내 기관 정보는 공개 과제와 공개 논문을 기반으로 하더라도, 기관 평가나 서열화로 오해될 수 있으므로 지표별 공개 범위를 구분한다.

| 정보 | 접근 등급 | 비고 |
| --- | --- | --- |
| 주요 국내 기관명 | Public 가능 | 공개 과제 기반이면 표시 가능 |
| 기관 유형별 분포 | Public | 대학, 출연연, 기업, 정부기관 등 집계 중심 |
| 기관 협력 네트워크 | Public 가능 | 구조 설명 중심으로 제공 |
| 기관별 과제 수 | Public 또는 Registered | 해석 주의 문구와 함께 제공 |
| 기관별 연구비 총액 | Admin/Internal 우선 | dBrain 연동 전에는 특히 신중 처리 |
| 기관별 세부 점수 | Admin/Internal | 기관 서열화 방지를 위해 비공개 |
| 기관별 투자 대비 성과 | 제공하지 않음 | 평가 목적이 아니므로 산출하지 않음 |

국내 기관 정보는 다음 방식으로 제시한다.

```text
공개 화면:
- 이 클러스터에 어떤 유형의 기관이 참여하는가
- 주요 참여기관은 어디인가
- 기관 간 협력 구조는 어떤가

비공개 또는 내부 화면:
- 기관별 종합점수
- 기관별 연구비 순위
- 기관별 민감 지표
```

---

## 13-6. 국내 연구자 정보 공개 원칙

국내 연구자 정보는 가장 민감한 정보로 분류한다.

연구자 이름, 과제 참여, 연구비 연결, 역할 라벨, 매칭 신뢰도는 공개 방식에 따라 개인 평가나 순위화로 오해될 수 있다. 특히 NTIS 연구자 매칭은 동명이인, 소속 변경, 기관명 표기 차이로 인해 오류 가능성이 있으므로 신중하게 처리한다.

| 정보 | 접근 등급 | 비고 |
| --- | --- | --- |
| 글로벌 연구자 이름 | Public 가능 | 공개 논문 기반 |
| 국내 연구자 이름 | Verified Professional 또는 Admin/Internal | 일반 공개는 신중 처리 |
| 국내 연구자 역할 라벨 | Verified Professional | 정책·사업기획 목적 사용자에게 제공 |
| 국내 연구자 상세 점수 | Admin/Internal | 공개하지 않음 |
| 국내 연구자 순위 | 제공 금지 | 정렬 탐색은 가능하나 순위 표현 금지 |
| 국내 연구자 매칭 신뢰도 | Admin/Internal | 내부 검증용 |
| 국내 연구자 대표 논문/과제 | Verified Professional 가능 | 추천 근거와 주의 플래그 동시 표시 |
| 개인별 연구비 연결 | Hidden/System-only 권장 | 개인 평가로 오해될 수 있어 공개하지 않음 |

연구자 탐색 화면에서는 다음 표현을 사용하지 않는다.

```text
연구자 순위
Top 10 연구자
1위, 2위, 3위
최고 전문가
```

대신 다음 표현을 사용한다.

```text
연구자 탐색
관련 연구자 보기
영향력 지표 높은 순으로 보기
최근 활동성 높은 순으로 보기
국내 R&D 연계성 높은 순으로 보기
브리지 역할이 큰 연구자 보기
```

즉, K2KM은 연구자를 줄 세우지 않고, 사용자가 지표별로 탐색할 수 있는 구조를 제공한다.

---

## 13-7. 연구자 추천 결과 공개 원칙

연구자 추천 결과는 다음 범위 내에서 제공한다.

### 공개 가능

- 역할 라벨
- 대표 논문
- 주요 클러스터
- 추천 근거 요약
- 주의 플래그
- 최근 활동성 등급
- 국내 R&D 연계성의 정성 등급

### 비공개 또는 내부용

- 종합점수 원값
- 연구자 간 절대 순위
- 매칭 신뢰도 원값
- 내부 ranking score
- 연구자별 연구비 연결값
- Low-impact penalty 원값

추천 결과는 다음과 같이 표현한다.

```text
이 연구자는 해당 키워드와 관련된 연구 생태계에서 Bridge Researcher로 분류됩니다.
주요 근거는 관련 논문, 클러스터 연결성, 최근 활동성입니다.
단, 국내 R&D 매칭 결과는 추가 검토가 필요합니다.
```

---

## 13-8. 공개 범위 요약

| 정보 유형 | Public | Registered | Verified Professional | Admin/Internal | Hidden/System-only |
| --- | --- | --- | --- | --- | --- |
| 글로벌 연구 클러스터 | O | O | O | O | - |
| 논문 네트워크 요약 | O | O | O | O | - |
| 글로벌 핵심 논문 | O | O | O | O | - |
| 국내 R&D 포지셔닝 요약 | O | O | O | O | - |
| Gap/Niche/Alignment 요약 | O | O | O | O | - |
| 기관 유형별 분포 | O | O | O | O | - |
| 국내 주요 기관명 | △ | O | O | O | - |
| 기관별 연구비 총액 | - | - | △ | O | - |
| 국내 연구자 후보 | - | - | O | O | - |
| 연구자 역할 라벨 | △ | △ | O | O | - |
| 연구자 상세 점수 | - | - | - | O | - |
| 연구자 절대 순위 | - | - | - | - | 제공 금지 |
| 매칭 신뢰도 원값 | - | - | - | O | O |
| 내부 ranking score | - | - | - | - | O |
| 개인별 연구비 연결값 | - | - | - | △ | O |

범례:

```text
O: 제공
△: 제한 또는 요약 제공
-: 제공하지 않음
```

---

## 13-9. 기획상 의미

이 접근 등급 체계의 목적은 정보를 숨기기 위한 것이 아니다.

K2KM의 목적은 연구자·기관·사업을 평가하거나 줄 세우는 것이 아니라, 특정 키워드의 글로벌 연구구조와 국내 국가R&D 구조를 비교하여 정책적 검토 후보를 도출하는 것이다.

따라서 민감 정보는 맥락을 이해할 수 있는 사용자에게 제한적으로 제공하고, 공개 화면에서는 구조적 경향, 클러스터 포지셔닝, 공백·강점 후보, 해석 가능한 근거 중심으로 제공한다.


# 14. 해설 요약 리포트 및 공개 콘텐츠 확장 전략

## 14-1. 역할 정의

MVP 범위에는 별도 블로그 운영 기능을 포함하지 않는다.

다만 분석 결과를 사용자가 이해할 수 있도록 키워드별 **해설 요약 리포트**를 생성한다. 해설 요약 리포트는 새 분석이 아니라, 이미 생성된 분석 결과를 정책기획자와 일반 독자가 이해할 수 있도록 재구성하는 설명 계층이다.

향후 서비스 공개 이후에는 이 리포트를 기반으로 블로그, 정책 브리핑, 공개 아카이브 콘텐츠로 확장할 수 있다.

---

## 14-2. 해설 요약 리포트 기본 구조

해설 요약 리포트는 다음 구조를 따른다.

1. 이 키워드가 왜 중요한가
2. 글로벌 연구는 어떤 클러스터로 나뉘는가
3. 최근 성장하는 클러스터는 무엇인가
4. 한국 R&D는 어디에 집중되어 있는가
5. 국내 공백 후보는 무엇인가
6. 국내 niche/강점 후보는 무엇인가
7. 정책기획 관점에서 무엇을 검토해야 하는가
8. 관련 논문·기관·연구자 후보는 무엇인가
9. 이 분석의 한계와 주의사항은 무엇인가

---

## 14-3. 설명 원칙

좋은 표현:

- 중심 경향
- 브리지 역할
- 하위 군집
- 연결 패턴
- 정렬 경향
- niche 후보
- 공백 가능성
- 국내 R&D 포지셔닝
- 정책 검토 후보

나쁜 표현:

- 절대적으로 우수하다
- 세계 최고 수준이다
- 반드시 핵심이다
- 한국은 뒤처져 있다
- 특정 기관의 성과가 낮다
- 특정 연구자가 더 우수하다

---

# 15. 시스템 아키텍처 개요

## Frontend

- Next.js
- TypeScript
- React
- sigma.js
- graphology
- Cytoscape.js는 보조 검토

## Graph Viewer

- sigma.js 기반 대규모 그래프 렌더링
- graphology 기반 브라우저 내 그래프 상태 관리
- 노드 검색, 클러스터 필터, 연도 필터, 엣지 타입 필터
- 노드 클릭 시 상세 패널 표시
- 추천 연구자 역할 라벨과 그래프 위치 연동

## Backend

- FastAPI
- Worker
- Redis
- Graph API
- Export API

## Database

- PostgreSQL
- 분석 실행 결과 저장
- 그래프 노드/엣지 저장
- 레이아웃 좌표 저장
- 추천 결과 및 설명 저장

## Analysis Engine

- NetworkX
- igraph(확장 시)
- sentence-transformers
- clustering libraries
- graph layout libraries

## Data Collectors

- OpenAlex Connector
- Semantic Scholar Connector
- NTIS Connector

## External Compatibility

- GEXF Export
- JSON Export
- CSV Nodes/Edges Export
- Gephi Desktop 분석 호환

---

# 16. 대용량 처리 전략

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

# 17. 구현 로드맵

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
- sigma.js + graphology 기반 그래프 뷰어
- 그래프 데이터 API
- 그래프 필터·검색·하이라이트 기능
- GEXF/JSON/CSV Export 기능
- 연구자 추천 화면
- 추천 근거 및 주의 플래그 표시
- Global Impact × Domestic R&D Relevance 매트릭스 화면

---

## Phase 5

- Claude orchestration
- 해설 요약 리포트 생성
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

# 18. 핵심 리스크 및 대응

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
| Gephi 소스 직접 이식으로 인한 기술 복잡도 | Gephi 직접 이식 지양, sigma.js + graphology 직접 적용 |
| 대형 그래프 브라우저 렌더링 성능 저하 | Backend/Worker 사전 레이아웃 계산, threshold filtering, cluster drill-down 적용 |
| 외부 분석 도구와의 호환성 부족 | GEXF/JSON/CSV Export 제공 |
| 그래프 시각화가 장식 기능으로 축소 | 추천 근거, 클러스터, Niche/Gap/Alignment 해석과 연동 |
| 연구자·기관 정보의 순위화 오해 | 절대 순위·상세 점수 비공개, 역할·근거 중심 제공 |
| 연구비 지표의 성과평가 오해 | 투자 집중도·포지셔닝 신호로만 사용, 투자 대비 성과 미제공 |
| 국내 연구자 매칭 오류로 인한 개인 피해 | 매칭 신뢰도 내부 관리, 낮은 신뢰도 결과 공개 제한 |
| 공개 범위 불명확으로 인한 운영 리스크 | Public/Registered/Verified Professional/Admin/Hidden 접근 등급 적용 |

---

# 19. 최종 결론

본 프로젝트는 단순 논문 검색 서비스가 아니다.

핵심은:

> “키워드를 기반으로 글로벌 연구 생태계와 국내 국가R&D 구조를 자동 분석·비교하고, 그 결과를 데이터 자산으로 축적·공개하는 시스템”

이다.

이 프로젝트가 성공하면:

- 글로벌 연구구조 아카이브
- 국가R&D 비교분석 플랫폼
- 정책 탐색 도구
- 해설 요약 리포트 및 향후 공개 콘텐츠 확장
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

# 붙임 8. 그래프 시각화 구현 상세 설계

## 8-1. 기본 방향

K2KM의 그래프 시각화는 웹서비스 내부 탐색 기능으로 구현한다.

Gephi 데스크톱 소스는 직접 이식하지 않는다. 대신 sigma.js와 graphology를 사용하여 K2KM 전용 그래프 뷰어를 개발하고, Gephi와의 호환성은 GEXF Export로 확보한다.

```text
K2KM Graph Viewer
= sigma.js rendering
+ graphology graph model
+ backend precomputed layout
+ K2KM-specific filters and explanation panels
```

## 8-2. 그래프 데이터 API

```http
GET /api/analysis-runs/{run_id}/graphs/papers
GET /api/analysis-runs/{run_id}/graphs/authors
GET /api/analysis-runs/{run_id}/graphs/keywords
GET /api/analysis-runs/{run_id}/graphs/ntis-projects
GET /api/analysis-runs/{run_id}/graphs/institutions
GET /api/analysis-runs/{run_id}/graphs/comparison
```

## 8-3. 그래프 응답 구조

```json
{
  "graph_type": "paper_network",
  "analysis_run_id": "run_20260513_001",
  "layout": "precomputed_force_atlas_like",
  "nodes": [
    {
      "key": "paper_001",
      "attributes": {
        "label": "Example Paper",
        "x": 12.4,
        "y": -3.2,
        "size": 8.5,
        "cluster": "cluster_01",
        "type": "paper",
        "paper_evidence_weight": 0.91,
        "topical_relevance": 0.88,
        "year": 2024,
        "label_priority": 0.93
      }
    }
  ],
  "edges": [
    {
      "key": "edge_001",
      "source": "paper_001",
      "target": "paper_002",
      "attributes": {
        "weight": 0.72,
        "type": "bibliographic_coupling"
      }
    }
  ]
}
```

## 8-4. 노드 속성 표준

| 속성 | 설명 |
| --- | --- |
| key | 노드 고유 ID |
| label | 화면 표시명 |
| x, y | 사전 계산된 레이아웃 좌표 |
| size | 노드 크기 |
| cluster | 소속 클러스터 |
| type | paper, author, keyword, ntis_project, institution |
| score | 주요 점수 |
| label_priority | 라벨 표시 우선순위 |
| caution_flags | 주의 플래그 |

## 8-5. 엣지 속성 표준

| 속성 | 설명 |
| --- | --- |
| key | 엣지 고유 ID |
| source | 출발 노드 |
| target | 도착 노드 |
| weight | 엣지 가중치 |
| type | citation, co-citation, co-authorship 등 |
| confidence | 연결 신뢰도 |

## 8-6. 레이아웃 계산 원칙

대형 그래프의 레이아웃은 브라우저에서 실시간 계산하지 않는다.

```text
Small Mode
- 브라우저 또는 서버 계산 모두 가능

Standard Mode
- Worker에서 사전 계산 후 저장

Large Mode
- Worker에서 사전 계산
- 클러스터별 축약 그래프 생성
- 화면에서는 drill-down 탐색 제공
```

## 8-7. 그래프 필터 기능

K2KM 그래프 뷰어는 다음 필터를 제공한다.

- 클러스터 필터
- 연도 필터
- 엣지 타입 필터
- 노드 타입 필터
- Paper Evidence Weight threshold
- Global Scholarly Impact threshold
- Domestic R&D Relevance threshold
- 국가/기관 필터
- 역할 라벨 필터

## 8-8. 그래프 상세 패널

노드 클릭 시 다음 정보를 제공한다.

### 논문 노드

- 제목
- 저자
- 출판연도
- 소속 클러스터
- Paper Evidence Weight
- Topical Relevance
- 인용 영향력
- 네트워크 중심성
- 관련 연구자

### 연구자 노드

- 이름
- 소속기관
- 국가
- 역할 라벨
- Global Scholarly Impact
- Domestic R&D Relevance
- 관련 논문 수
- 대표 논문
- 추천 근거
- 주의 플래그

### NTIS 과제 노드

- 과제명
- 수행기관
- 사업명
- 과제기간
- 글로벌 클러스터 유사도
- 관련 국내 연구자
- 관련 글로벌 클러스터

## 8-9. Export API

```http
GET /api/analysis-runs/{run_id}/exports/gexf
GET /api/analysis-runs/{run_id}/exports/json
GET /api/analysis-runs/{run_id}/exports/csv/nodes
GET /api/analysis-runs/{run_id}/exports/csv/edges
GET /api/analysis-runs/{run_id}/exports/svg
```

## 8-10. Export 정책

| 형식 | 제공 목적 |
| --- | --- |
| GEXF | Gephi Desktop/Gephi Lite 등 외부 도구 호환 |
| JSON | K2KM 내부 재사용 및 API 연계 |
| CSV Nodes | 노드 목록 후처리 |
| CSV Edges | 엣지 목록 후처리 |
| SVG/PNG | 보고서·블로그 삽입 |

## 8-11. Gephi 활용 원칙

Gephi는 K2KM의 웹 렌더링 엔진이 아니다.

Gephi는 다음 용도로 제한한다.

1. 내부 분석 검증
2. 레이아웃 품질 비교
3. GEXF 호환 파일 검증
4. 고급 사용자용 외부 탐색 도구
5. 보고서용 정적 이미지 생성 보조

## 8-12. 라이선스 검토 원칙

Gephi 또는 gephi-lite 소스를 직접 복사·수정·배포하는 경우에는 라이선스 검토가 필요하다.

K2KM의 기본 구현은 특정 Gephi 소스를 직접 이식하지 않고, 웹 그래프 라이브러리를 독립적으로 사용하는 방식으로 설계한다.

---

# 붙임 9. 최종 설계 요약

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


---

# 붙임 10. 접근 등급 및 민감도 관리 상세

## 10-1. 접근 등급 정의

| 등급 | 정의 | 주요 사용자 |
| --- | --- | --- |
| Public | 누구나 볼 수 있는 공개 정보 | 일반 방문자 |
| Registered | 로그인 사용자에게 제공하는 정보 | 가입·인증 사용자 |
| Verified Professional | 업무 목적이 확인된 사용자에게 제공하는 정보 | 정책기획자, 연구기획자, 전문기관 실무자 |
| Admin/Internal | 운영자와 내부 검증자만 확인하는 정보 | 서비스 운영자, 관리자 |
| Hidden/System-only | 사용자 화면에 표시하지 않고 계산에만 사용하는 정보 | 시스템 내부 |

## 10-2. MVP 구현 등급

MVP에서는 다음 3개 등급만 우선 구현한다.

| 등급 | 구현 범위 |
| --- | --- |
| Public | 공개 가능한 그래프, 클러스터, Gap/Niche/Alignment 요약, 해설 요약 리포트 |
| Admin/Internal | 상세 점수, 매칭 신뢰도, 연구비 원자료, 오류 검토 데이터 |
| Hidden/System-only | 내부 ranking score, 알고리즘 중간값, 개인별 연구비 연결값 |

Registered와 Verified Professional은 서비스 고도화 단계에서 추가한다.

## 10-3. 연구비 지표 사용 원칙

연구비는 국내 R&D 포지셔닝을 설명하는 보조 신호이다. 단순 연구비 총액이나 기관별 연구비 순위는 K2KM의 공개 화면에서 제공하지 않는다.

```text
연구비 지표의 기본 용도
= 클러스터별 국내 R&D 투자 집중도 파악
+ 최근 투자 흐름 파악
+ 공백·중복·집중 후보 탐색
```

K2KM은 투자 대비 성과, 기관별 효율성, 연구자별 연구비 수혜 순위는 산출하지 않는다.

## 10-4. 연구자 정보 공개 원칙

연구자 정보는 역할 기반 탐색으로 제공한다.

```text
제공 가능:
- 역할 라벨
- 대표 논문/과제
- 추천 근거
- 주의 플래그
- 관련 클러스터

제공 금지:
- 절대 순위
- 종합점수 원값
- 내부 ranking score
- 개인별 연구비 연결값
```

연구자 화면은 “순위표”가 아니라 “탐색 도구”로 설계한다.

## 10-5. 기관 정보 공개 원칙

기관 정보는 구조적 참여 현황을 설명하기 위해 사용한다.

```text
제공 가능:
- 기관 유형별 분포
- 주요 참여기관
- 기관 협력 구조
- 클러스터별 기관 참여 양상

제공 제한:
- 기관별 연구비 총액
- 기관별 종합점수
- 기관별 성과 순위
- 투자 대비 성과
```

## 10-6. 공개 문구 원칙

권장 문구:

```text
이 클러스터는 국내 R&D 과제와 투자 집중도가 상대적으로 높게 나타납니다.
이 연구자는 해당 키워드 생태계에서 브리지 역할을 하는 후보로 분류됩니다.
이 기관은 해당 클러스터에서 반복적으로 등장하는 참여기관입니다.
```

금지 문구:

```text
이 연구자가 1위입니다.
이 기관이 가장 우수합니다.
이 사업은 투자 대비 성과가 낮습니다.
A기관은 이 분야에서 연구비를 가장 많이 받았습니다.
```
