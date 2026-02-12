# Phase 25: .scoda ZIP 패키지 포맷 도입 및 DB-앱 분리

**일시:** 2026-02-12
**브랜치:** `feature/scoda-package`

## 배경

기존 구조에서는 `trilobase.db`가 PyInstaller exe 내부에 번들링되어 있어:
- DB 수정 시 exe 재빌드 필요
- 두 exe(`trilobase.exe`, `trilobase_mcp.exe`)에 DB 중복 포함
- DB 경로 로직이 4개 파일에 중복

## 변경 사항

### 신규 파일

| 파일 | 설명 |
|------|------|
| `scoda_package.py` | 핵심 모듈 — ScodaPackage 클래스 + 중앙 집중 DB 접근 함수 |
| `scripts/create_scoda.py` | `trilobase.db` → `trilobase.scoda` 패키징 스크립트 |

### 수정 파일

| 파일 | 변경 내용 |
|------|----------|
| `app.py` | DB 경로/overlay 로직 90줄 삭제, `from scoda_package import get_db` |
| `mcp_server.py` | DB 경로/overlay 로직 50줄 삭제, `from scoda_package import get_db, ensure_overlay_db` |
| `scripts/gui.py` | DB 경로 로직 → `scoda_package.get_scoda_info()` 사용, GUI에 .scoda 정보 표시 |
| `trilobase.spec` | `trilobase.db` 번들링 제거, `scoda_package.py` 추가 |
| `test_app.py` | fixture → `scoda_package._set_paths_for_testing()` 사용, ScodaPackage 테스트 10개 추가 |
| `scripts/release.py` | 릴리스 디렉토리에 .scoda 파일도 생성 |
| `scripts/build.py` | 빌드 후 `dist/`에 .scoda 패키지 생성 |
| `.gitignore` | `*.scoda` 추가 |

## .scoda 포맷

```
trilobase.scoda (ZIP)
├── manifest.json   # 메타데이터 (format, version, checksum 등)
├── data.db         # SQLite DB
└── assets/         # 향후 이미지/문서 (현재 비어 있음)
```

## 경로 탐색 우선순위

1. `_set_paths_for_testing()` 호출 시 → 해당 경로 사용
2. Frozen 모드: exe 옆의 `trilobase.scoda` → 없으면 번들 내부 `trilobase.db`
3. Dev 모드: 프로젝트 루트 `trilobase.scoda` → 없으면 `trilobase.db`
4. Overlay DB: 항상 .scoda/.db 옆에 `trilobase_overlay.db`

## 배포 구조 (목표)

```
trilobase/
├── trilobase.exe         # GUI (DB 미포함, 가벼움)
├── trilobase_mcp.exe     # MCP (DB 미포함)
├── trilobase.scoda       # 데이터 패키지
└── trilobase_overlay.db  # 사용자 주석 (런타임 자동 생성)
```

## 테스트 결과

- 기존 101개 + ScodaPackage 10개 = **111개 모두 통과**
- `.scoda` 모드 정상 동작 확인 (5,340 레코드)
- `.scoda` 없을 때 `.db` 폴백 정상 동작 확인
- `--dry-run` 모드 정상 동작 확인
