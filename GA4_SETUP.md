# 관리자 탭 / Google Analytics 4 연결

사이트의 `관리자` 탭 또는 https://j-hwan9.github.io/SBE-US-Market-Dashboard/#admin 에서 PIN **970513**으로 열 수 있습니다. PIN은 요청한 간단한 화면 잠금입니다. 통계 조회는 Google 계정의 GA4 권한으로 보호됩니다.

## 1. 방문 수집: GA4 웹 스트림

1. https://analytics.google.com/ 에서 계정과 GA4 속성을 생성합니다. 시간대는 **대한민국 / Asia/Seoul**을 선택합니다.
2. 웹 데이터 스트림을 생성합니다. URL: `https://j-hwan9.github.io/SBE-US-Market-Dashboard/`.
3. 스트림의 **향상된 측정**을 끕니다. 공개 탭 전환을 코드에서 직접 `page_view`로 보내므로 자동 이벤트 중복을 방지합니다.
4. 스트림의 **측정 ID** (`G-...`)와 속성 설정의 **숫자 속성 ID**를 복사합니다. 스트림 ID와 속성 ID는 다릅니다.
5. `dist/analytics-config.json`의 `measurementId`를 입력하고 main에 커밋하면 Pages 배포 후 수집이 시작됩니다. 별도 HTML 태그 삽입은 필요 없습니다.

## 2. 관리자 화면 안에서 통계 조회: Google OAuth

1. https://console.cloud.google.com/ 에서 프로젝트를 생성하고 **Google Analytics Data API**를 사용 설정합니다.
2. Google Auth Platform에서 브랜딩/대상/데이터 액세스를 설정합니다. 개인 계정이면 외부(External), 테스트 단계에서는 본인 Google 이메일을 테스트 사용자로 추가합니다. 회사 조직 전용 프로젝트라면 조직 정책에 맞는 대상을 선택합니다.
3. 읽기 전용 범위 `https://www.googleapis.com/auth/analytics.readonly`를 사용합니다. 앱 홈페이지는 대시보드 URL입니다. 본인 테스트 사용에는 전체 사용자 공개 배포가 필요하지 않습니다.
4. OAuth 클라이언트를 **웹 애플리케이션** 유형으로 생성합니다.
5. **승인된 JavaScript 원본**에 `https://j-hwan9.github.io`를 추가합니다. 원본에는 저장소 경로나 `#admin`을 넣지 않습니다. 팝업 토큰 방식을 사용하므로 리디렉션 URI는 필요하지 않습니다.
6. 클라이언트 ID (`....apps.googleusercontent.com`)를 복사합니다. Client secret/서비스 계정 키는 사용하지 않으며 저장소에 올리지 않습니다.
7. `dist/analytics-config.json`의 `propertyId`와 `oauthClientId`를 채우고 배포합니다.
8. 관리자 탭에서 **Google 계정 연결**을 누르고 GA4 속성에 Viewer 이상 권한이 있는 계정으로 연결합니다.

```json
{
  "measurementId": "G-실제측정ID",
  "propertyId": "실제숫자속성ID",
  "oauthClientId": "실제클라이언트ID.apps.googleusercontent.com"
}
```

위 세 식별자는 공개 설정 값입니다. 비밀번호·인증 코드·OAuth access token·client secret은 전달할 필요 없습니다. 세 ID를 전달하면 설정 파일 연결을 대신 진행할 수 있습니다.

## 지표와 집계 기준

- **Users**: 선택 기간 전체의 `totalUsers`. 일별 사용자 수를 더하지 않으므로 재방문자를 이중 집계하지 않습니다.
- **Sessions**: `sessions`, 방문 횟수.
- **Page views**: `screenPageViews`, 공개 탭 전환도 한 번의 조회로 기록.
- **Views / session**: 조회 수 ÷ 방문 수. 방문 수가 0이면 —.
- **Daily traffic**: 날짜별 Users / Sessions / Views 및 추이.
- **Tab usage**: 탭별 Views / Users.
- **Devices**: 기기 범주별 Sessions / Users.
- **Traffic sources**: 유입 출처/매체별 Sessions / Users.

기본 기간은 어제까지 최근 7일입니다. 최근 30/90일과 오늘도 선택할 수 있습니다. 날짜 경계는 GA4 속성 시간대를 따릅니다. 오늘은 잠정 집계이며 일반 보고서는 24–48시간 지연될 수 있습니다. 조회/사용자 수는 광고 차단, 네트워크 제한, 브라우저 및 기기에 따라 실제 이용과 차이가 있습니다.

보고서 조회는 정확한 호스트 `j-hwan9.github.io`와 가상 페이지 경로 `/SBE-US-Market-Dashboard/tab/`로 한정합니다. 같은 GA4 속성의 다른 사이트 트래픽이 섞이지 않습니다. 탭: home, regulatory, news, prices, competitive, performance. 제품 선택, 검색어, PIN은 이벤트로 보내지 않습니다. 관리자 탭에서 수동 조회 이벤트는 보내지 않으며 측정을 비활성화합니다.

## 운영 및 확인

- 기본 GA4 수집/보고는 정기 GitHub Actions 작업 없이 동작합니다. Google 보고서를 관리자 브라우저에서 읽습니다. 별도 서버를 운영할 필요가 없습니다.
- Access token과 통계는 브라우저 메모리에만 있습니다. 저장소, localStorage, sessionStorage에 보관하지 않습니다. 잠금/다른 탭 이동/새로고침하면 다시 연결해야 합니다.
- 연결 이전의 방문 수는 복원되지 않습니다. 초기 화면의 —는 미연결/조회 전, API가 정상 반환한 0은 실제 해당 조회의 0입니다.
- 설치 후 공개 Home → Regulatory → News를 이동하고 GA4 실시간 보고서에서 확인하세요. 관리자 일반 보고서 반영은 기다려야 할 수 있습니다.
- `403`: Data API 활성화, GA4 속성 ID 및 계정 조회 권한, OAuth 테스트 사용자 여부를 확인하세요.
- `origin_mismatch`: 승인된 JavaScript 원본이 `https://j-hwan9.github.io`인지 확인하세요.
- 로그인 창이 뜨지 않으면 브라우저 팝업/Google 접근 정책을 확인하세요. OAuth 테스트 모드에서는 주기적으로 다시 동의를 요청할 수 있습니다.
- PIN은 코드상 간단한 화면 잠금입니다. 실제 GA4 통계는 속성 권한이 있는 Google 계정만 조회할 수 있습니다.

공식 문서: [수동 페이지 조회](https://developers.google.com/analytics/devguides/collection/ga4/views), [브라우저 OAuth 토큰 방식](https://developers.google.com/identity/oauth2/web/guides/use-token-model), [Analytics Data API](https://developers.google.com/analytics/devguides/reporting/data/v1/quickstart).
