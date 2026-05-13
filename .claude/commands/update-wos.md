# /update-wos — WoS Master Journal List 자동 갱신

Clarivate MJL 다운로드 페이지를 열고, 파일이 다운로드되면 자동으로 DB에 import한다.

## 1. 다운로드 마커 생성

Downloads 폴더의 기준 시각을 기록해둔다 (이후 새 파일 감지에 사용).

```bash
touch /tmp/wos_mjl_marker
```

## 2. 브라우저로 다운로드 페이지 열기

```bash
open "https://mjl.clarivate.com/collection-list-downloads"
```

그리고 사용자에게 아래 안내를 출력한다:

```
브라우저에서 MJL 다운로드 페이지가 열렸습니다.

로그인 후 아래 항목을 다운로드하세요 (무료 계정 필요):
  - Science Citation Index Expanded (SCIE)
  - Social Sciences Citation Index (SSCI)
  - Arts & Humanities Citation Index (AHCI)
  - Emerging Sources Citation Index (ESCI)

하나의 파일로 "Download all" 또는 개별 인덱스를 모두 받아도 됩니다.
다운로드가 완료되면 자동으로 감지합니다…
```

## 3. 다운로드 완료 감지 (최대 10분 대기)

~/Downloads 에서 마커보다 새로운 CSV 파일이 생길 때까지 5초 간격으로 폴링한다.

```bash
for i in $(seq 1 120); do
  found=$(find ~/Downloads -name "*.csv" -newer /tmp/wos_mjl_marker -type f 2>/dev/null | head -1)
  if [ -n "$found" ]; then
    echo "$found"
    break
  fi
  sleep 5
done
```

- 파일이 감지되면 경로를 `CSV_PATH` 변수에 저장하고 다음 단계로 진행한다.
- 10분(120회) 이내에 감지되지 않으면 사용자에게 아래를 출력하고 중단한다:
  ```
  다운로드 파일을 감지하지 못했습니다.
  CSV 경로를 직접 전달해 재시도할 수 있습니다:
    /update-wos /path/to/downloaded_file.csv
  ```

## 4. 파일이 인자로 직접 전달된 경우

사용자가 `/update-wos /some/path/file.csv` 형식으로 실행했다면
1~3단계를 건너뛰고 해당 경로를 `CSV_PATH`로 사용해 4단계로 바로 이동한다.

## 5. Import 실행

```bash
cd /Users/hyeokseong/GitHubRepo/2_Keyword-to-Knowledge-Map/backend
python -m app.commands.import_wos_journals "$CSV_PATH"
```

## 6. 결과 보고

성공 시:
```
✅ WoS MJL 갱신 완료

파일: <CSV_PATH>
결과: <import 출력 그대로>
갱신 주기 권장: 분기 1회 (Clarivate 연 2~4회 업데이트)
다음 갱신 예정: <오늘로부터 3개월 후 날짜, YYYY-MM-DD>
```

오류 시 원인을 분석하고 해결 방법을 안내한다:
- **CSV 컬럼명 불일치** → `import_wos_journals.py`의 alias 목록 수정 필요
- **DB 미연결** → `backend/.env`의 `DATABASE_URL` 확인
- **마이그레이션 미적용** → `alembic upgrade head` 실행
