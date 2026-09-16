# 미국 바이오·제약 뉴스 소스 접근성 점검

점검일: Sep 16, 2026 (KST). **실제 수집 목록 변경 없음.** 검증 전용 브랜치의 GitHub-hosted Ubuntu runner 두 대에서 동일한 검사를 수행했습니다. 같은 날의 단기 테스트이며 장기간 안정성을 보장하지 않습니다.

## 추천: 기존 5개 매체에 더할 5곳

| 매체 | 검증한 수집 경로 | 두 runner 결과 | 적합한 내용 / 연결 조건 |
|---|---|---|---|
| STAT | https://www.statnews.com/category/pharma/feed/ 및 /category/biotech/feed/ | 각각 200, 제목·날짜·링크 20/20건 | 미국 제약·바이오 사업, FDA, 정책. STAT+ 원문은 구독 필요 가능; 공개 RSS 메타데이터만 게시 |
| BioPharma Dive | https://www.biopharmadive.com/feeds/news/ | 200, 10/10건 | 미국 제약·바이오 사업, 승인·임상·가격. 홈페이지/표본 기사는 403이므로 RSS 제목·설명만으로 분류; 본문 접근을 필수 조건으로 삼지 않음 |
| Fierce Biotech | https://www.fiercebiotech.com/rss/biotech/xml | 200, 25/25건 | 임상·개발·허가·기업 동향. 중첩된 제목 태그와 비표준 날짜 형식을 처리하는 어댑터 필요 |
| GEN | https://www.genengnews.com/feed/ | 200, 10/10건 | 바이오 연구·항체·제조·개발. 상업/바이오시밀러 기사 비중은 상대적으로 낮으므로 현행 제품 필터 유지 |
| Drug Discovery & Development | https://www.drugdiscoverytrends.com/feed/ | 200, 25/25건 | 제약·바이오 파이프라인, 임상, 항암제. 현행 제품 필터 유지 |

위 숫자는 점검 당시 피드에서 제목·게시일·링크가 모두 확인된 항목 수이며, 대시보드 필터에 매칭되는 기사 수나 일일 발행량이 아닙니다. 본문 재게시/유료벽 우회는 하지 않습니다.

## 추가 보조 채널

| 채널 | 결과 | 구분/주의점 |
|---|---|---|
| Bio.News https://bio.news/feed/ | 200, 10/10건, 두 runner 일치 | BIO 협회가 제작하는 바이오·미국 정책 채널. 독립 언론과 협회 관점을 구분 |
| FDA Law Blog https://www.thefdalawblog.com/feed/ | 200, 10/10건, 두 runner 일치 | 법률 전문가의 FDA·규제 해설; FDA 공식 사이트가 아님 |
| KFF Health News https://kffhealthnews.org/feed/ | 200, 10/10건, 두 runner 일치 | 미국 약가·보험·Medicare/Medicaid 보조 채널; 바이오 전문지는 아님 |
| Biosimilars Law Bulletin https://www.biosimilarsip.com/feed/ | 200, 10/10건, 두 runner 일치 | 바이오시밀러 특허·소송 법률 블로그. 피드 첫 기사가 Jun 11, 2026으로 발행 빈도 낮음 |

## 추가 확인이 필요한 3곳

- **Biosimilar Development**: 홈페이지와 표본 공개 페이지 200, 제목 메타데이터 확인. 자동 발견 RSS 없음. 일반 메타데이터 파서에서 날짜가 추출되지 않아 사이트별 날짜 파서 확인 필요. 홈페이지 첫 링크에는 편집위원 소개도 포함되므로 기사 유형 필터 필요.
- **Life Science Leader**: 홈페이지와 표본 페이지 200. 자동 발견 RSS 없음. 표본에 잡지 아카이브가 섞여 있으며 날짜가 일반 메타데이터로 추출되지 않음. 뉴스 목록/날짜 파서 별도 개발 필요.
- **Fierce Healthcare**: /rss/healthcare/xml은 200이지만 0건. 홈페이지에 노출된 다른 RSS는 12건이지만 처음 두 항목이 2018년 스폰서 콘텐츠. 접속 성공만으로 최신 뉴스 수집 가능하다고 판단하지 않음. 홈페이지는 200이므로 현재 뉴스 목록 수집은 별도 후보.

## 이번 GitHub 환경에서 보류한 8곳

| 매체 | 실제 실패 지점 |
|---|---|
| BioPharm International | robots.txt 403; 후속 기사 요청 중단 |
| Pharmaceutical Technology (pharmtech.com) | robots.txt 403; 후속 기사 요청 중단 |
| Endpoints News | robots.txt 403; 후속 기사 요청 중단 |
| The Center for Biosimilars | robots.txt 403; 후속 기사 요청 중단 |
| Drug Topics | robots.txt 403; 후속 기사 요청 중단 |
| Pharmacy Times | robots.txt 403; 후속 기사 요청 중단 |
| AJMC | robots.txt 403; 후속 기사 요청 중단 |
| Managed Healthcare Executive | robots.txt 200; 홈페이지 및 뉴스 사이트맵 403 |

403은 이번 경로/환경의 결과이며 매체의 모든 접근 경로가 영구적으로 불가능하다는 의미는 아닙니다. robots.txt를 받지 못한 경우와 robots 규칙이 명시적으로 금지한 경우를 혼동하지 않았습니다.

## 운영 반영 시 필요한 사항

- 기존 5곳 + 우선 후보 5곳 = 10개 매체. 현행 molecule/제품명/Market overall/Policy 규칙 적용.
- RSS 우선으로 제목·날짜·출처·링크를 저장하고, 본문 대신 피드 설명에서 분류한 항목은 분류 근거를 RSS로 기록. 본문에만 제품명이 있는 기사는 누락될 수 있음.
- 기사 URL의 utm_*와 fragment 정리 후 중복 제거. 댓글 RSS는 수집 대상에서 제외.
- 원문이 구독 필요인 경우 링크 옆에 표시. RSS 접근 가능성이 무제한 재사용 허가를 의미하지 않으므로 공식 피드 조건에 맞춰 출처·링크 표시.
- RSS 10~25건 제한으로 새 기사 발행이 많으면 일일 수집 사이 누락 가능. 피드의 최신 게시일, 파싱 성공률, 연속 실패를 기록해 운영 안정성 평가.
- 향후 추가 후 최소 일주일간 실제 일일 실행 성공률을 확인해야 장기 안정성 판단 가능.

## 검증 근거

- [20개 후보 × 2개 runner 검사](https://github.com/j-hwan9/SBE-US-Market-Dashboard/actions/runs/35102390902)
- [Fierce 제목/URL 처리 및 HTML 후보 보충검사](https://github.com/j-hwan9/SBE-US-Market-Dashboard/actions/runs/35102719327)
- [구조화된 결과](news-source-audit-20260916.json)

공식 매체 소개: [STAT](https://www.statnews.com/about/), [Fierce Biotech](https://www.fiercebiotech.com/fiercebiotechcom/about-us), [GEN](https://www.genengnews.com/), [Drug Discovery & Development](https://www.drugdiscoverytrends.com/about-us/), [Bio.News](https://bio.news/about/), [KFF Health News](https://kffhealthnews.org/about-us/).
