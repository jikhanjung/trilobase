# 20260315_P88 — [아이디어] paleobase: 통합 패키지 구상

## 배경

현재 taxa별로 `-base` 이름을 붙이는 패턴(`chelicerobase`, `graptobase`, `ostracobase` 등)이
다소 억지스럽다는 문제의식에서 출발.

- 대부분의 패키지가 Treatise 데이터 하나를 넣은 수준
- 독립적인 브랜드 이름을 붙일 만큼 각각이 충분한 정체성을 갖고 있는가?
- trilobase는 JA2002, A2011 등 독자 데이터와 앞으로도 문헌 추가 계획이 있어 독립 이름이 합당하지만,
  나머지는 불확실

## 아이디어 요약

**`paleobase`** 라는 이름으로 전체 taxa DB를 통합 패키지로 배포.

## 구현 옵션

### 옵션 1: 단순 번들 (포맷 변경 필요)
여러 DB를 하나의 `.scoda` 파일에 묶어서 배포.
현재 scoda 포맷은 DB 하나를 가정하므로 포맷 수준 변경이 필요.

### 옵션 2: 메타패키지 (현실적)
`paleobase.scoda`는 껍데기 패키지이고, 각 `-base`를 dependency로 선언.
사용자는 `paleobase` 하나만 받으면 전체 설치.
- 포맷 변경 불필요
- taxa 추가/제거 유연
- 버전은 paleobase 자체 sequential (1.0, 1.1, ...)

### 옵션 3: 단일 DB 통합 (대공사)
모든 taxa를 하나의 SQLite DB로 합쳐서 배포.
가장 심플한 사용자 경험이지만 빌드 파이프라인 대규모 재설계 필요.

## 현재 판단

- **단기**: 현재 `-base` 명명 유지. 이름보다 데이터 품질/완성도가 우선.
- **중기**: 옵션 2(메타패키지)로 `paleobase` 배포 검토. scoda 포맷 변경 없이 가능.
- **장기**: taxa 커버리지가 충분히 넓어지면 옵션 3 재검토.

## 미결 사항

- trilobase는 `paleobase` 통합에 포함하는가, 독립 유지인가?
- 통합 시 각 taxa DB의 독립 배포도 병행할 것인가?
- 버전 체계: CalVer(`paleobase-2026.03`) vs sequential(`paleobase-1.0`)
