# /update-wos — WoS Master Journal List 갱신

Clarivate MJL CSV를 DB에 import/갱신한다.

## 1. CSV 파일 확인

사용자가 CSV 경로를 인자로 전달했는지 확인한다.
- 전달된 경우: 해당 경로를 사용한다.
- 전달되지 않은 경우: 아래 안내 메시지를 출력하고 중단한다.

```
MJL CSV 경로를 인자로 전달해주세요.
예: /update-wos /path/to/mjl_export.csv

CSV 다운로드 방법:
  1. https://mjl.clarivate.com/ 접속
  2. 우측 상단 "Download" → "Download entire collection" 클릭
  3. 다운로드된 CSV 파일 경로를 위 명령어에 전달
```

## 2. Import 실행

아래 명령을 프로젝트 루트의 `backend/` 디렉토리에서 실행한다.

```bash
cd /Users/hyeokseong/GitHubRepo/2_Keyword-to-Knowledge-Map/backend
python -m app.commands.import_wos_journals <CSV_PATH>
```

`<CSV_PATH>`는 사용자가 전달한 실제 경로로 치환한다.

## 3. 결과 보고

명령 실행 후 출력된 결과를 그대로 사용자에게 전달한다.

성공 예시:
```
Done. Upserted 21,483 rows, skipped 142 rows.
```

오류 발생 시:
- 오류 메시지를 출력하고 원인을 분석해 해결 방법을 안내한다.
- 흔한 원인:
  - **CSV 컬럼명 불일치**: Clarivate가 CSV 포맷을 변경했을 수 있음 → `import_wos_journals.py`의 `_COVERAGE_COLS` 등 alias 목록 업데이트 필요
  - **DB 미연결**: `backend/.env`의 `DATABASE_URL` 확인
  - **마이그레이션 미적용**: `alembic upgrade head` 실행 필요

## 4. 완료 후 안내

```
✅ WoS MJL 갱신 완료

import 결과: <실행 결과>
갱신 주기 권장: 분기 1회 (Clarivate는 보통 연 2~4회 업데이트)
다음 갱신 예정: <오늘로부터 3개월 후 날짜>
```
