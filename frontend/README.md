# K2KM Frontend

Next.js 16 + React 19 + TypeScript + Tailwind v4 기반 K2KM 웹앱.
Phase 4 MVP — 분석 잡 생성 / 모니터링 / 결과 탐색 / 그래프 시각화.

## 스택

- **Framework**: Next.js 16 (App Router)
- **UI**: Tailwind v4 + 커스텀 디자인 토큰 (Claude 제품 스타일에서 영감)
- **Data**: TanStack Query v5
- **Graph viz**: Sigma.js + Graphology + ForceAtlas2 (client-only, `next/dynamic`)
- **API client**: native `fetch` 래퍼 (`src/lib/api/client.ts`)

## 페이지 / 라우트

| Route | 역할 |
|---|---|
| `/` | 분석 목록 (자동 5초 폴링) |
| `/jobs/new` | 새 분석 생성 — 키워드 모드 / 자연어 모드 |
| `/jobs/[id]` | 분석 상세 — 진행 상태 + 논문/저자/키워드/그래프 탭 |
| `/graphs/[id]` | 그래프 시각화 — Sigma + Louvain 군집 색상 |

자연어 모드에서는 `POST /api/v1/jobs/parse-query` 로 키워드 미리보기 표시 후 `POST /api/v1/jobs/from-query` 제출.

## 환경

```bash
cp .env.example .env.local
# NEXT_PUBLIC_API_BASE=http://localhost:8000

npm install
npm run dev
```

백엔드(`backend/docker-compose up`)와 함께 실행하면 E2E 동작.

## 디자인 토큰

`src/app/globals.css` — 모든 색상/라운드/그림자가 CSS 변수.
다크 모드는 아직 미적용 (Phase 4 MVP 범위 밖).
