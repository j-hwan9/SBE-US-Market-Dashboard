# 공개 사이트 연결

사이트 이름: **Samsung Bioepis US Market Dashboard**

## 한 번만 설정

1. GitHub에서 **Public** 저장소를 만듭니다. 권장 이름: `samsung-bioepis-us-market-dashboard`. 기본 브랜치는 `main`으로 둡니다.
2. 이 프로젝트의 파일을 저장소 루트에 넣습니다. `.github/workflows`, `dist`, `scripts`, `tests`, `data`가 포함되어야 합니다. `.openai`, `.git`, 임시 소스 캐시와 자격 증명은 공개 저장소에 넣지 않습니다.
3. 저장소 **Settings → Pages → Build and deployment → Source → GitHub Actions**를 선택합니다.
4. **Actions → Deploy dashboard → Run workflow**를 실행합니다. 성공한 실행의 `github-pages` 환경에서 공개 주소를 확인합니다.

공개 사이트는 GitHub Pages에서 제공하며 방문자가 ChatGPT에 로그인하지 않습니다. 회사 네트워크의 GitHub Pages 허용 여부는 실제 공개 주소에서 확인해야 합니다.

## 자료 업데이트

- 사이트의 **공식 소스 업데이트** 버튼 → GitHub의 **Refresh official sources** → **Run workflow**.
- 완료 후 사이트에서 **최신 게시본 불러오기**를 누릅니다.
- 수집은 관리자 GitHub 계정만 실행합니다. 공개 방문자에게 쓰기 토큰이나 API 키가 노출되지 않습니다.
- 같은 실행은 매월 **8일 09:23 KST**에 예약되어 있습니다. GitHub의 예약 실행은 지연될 수 있고 비활성 공개 저장소에서는 중지될 수 있으므로 실행 기록을 확인할 수 있습니다.
- 이전 저장본과 신규·제외·변경 항목은 사이트의 **조회 시점 / 변경 이력**에서 확인합니다.

## 동작

1. FDA Purple Book 다운로드 페이지에서 가장 최근 월의 공식 CSV 링크를 찾습니다.
2. 전체 목록 구간을 읽어 Licensed인 351(k) 제품과 reference product를 구성합니다.
3. DailyMed API에서 SPL 버전을 확인하고 BLA를 대조합니다. 버전이 같으면 검증된 파싱 결과를 재사용합니다.
4. DailyMed에 없으면 Drugs@FDA API의 최신 label PDF를 가져옵니다.
5. 데이터 누락·형식 변경·참조제품 연결·PI 추출을 검증합니다. 실패하면 기존 게시본을 유지합니다.
6. 성공한 데이터와 이력을 Git에 저장한 뒤 GitHub Pages를 다시 게시합니다.

`force_download`를 켜면 같은 PI 버전도 다시 다운로드합니다. 키나 유료 AI API 없이 Python 표준 라이브러리와 PDF 텍스트 추출기로 실행됩니다.

## 실행이 실패하면

Actions 실행 화면의 오류 로그와 `refresh-diagnostics` 첨부 파일에서 원인을 확인합니다. 소스 서버의 일시 오류라면 다시 실행합니다. PI 구조나 CSV 컬럼이 달라졌다면 파서를 수정한 후 실행합니다. 새 제품에 아직 공식 PI가 없으면 해당 제품만 미확보 상태로 표시하며, 기존 PI를 추측값으로 바꾸지 않습니다.

자동 커밋이 브랜치 보호 규칙으로 차단되면 직접 보호 규칙을 약화시키기보다 관리자가 승인하는 별도 갱신 브랜치/PR 방식으로 전환해야 합니다. 기본 구성은 개인 관리용 저장소의 기본 브랜치 쓰기 권한을 사용합니다.

## 로컬 실행

Python 3, Node.js, Poppler의 `pdftotext`가 필요합니다.

```bash
python3 -m unittest discover -s tests -v
node tests/ui.cjs
python3 scripts/refresh.py --catalog-only
python3 scripts/refresh.py --check-only
python3 scripts/refresh.py
```

기존 `collect.py`, `fda_fallback.py`, `finalize.py`는 최초 자료 구축 기록입니다. 정기 갱신에는 **refresh.py**를 사용합니다.

공식 안내: [GitHub Pages 설정](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site), [수동 실행](https://docs.github.com/actions/managing-workflow-runs/manually-running-a-workflow).
