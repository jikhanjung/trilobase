# Phase 25 계획: .scoda ZIP 패키지 포맷 도입 및 DB-앱 분리

**작성일:** 2026-02-12

## 배경

현재 구조의 문제점:
1. `trilobase.db`가 PyInstaller exe 내부에 번들링 — DB 수정 시 exe 재빌드 필요
2. 두 exe(`trilobase.exe`, `trilobase_mcp.exe`)에 DB가 중복 포함
3. DB 경로 해석 로직이 4개 파일에 중복 (`app.py`, `mcp_server.py`, `gui.py`, `serve.py`)
4. overlay DB 생성 로직도 3곳에 중복 (`app.py`, `mcp_server.py`, `init_overlay_db.py`)

## 목표

### .scoda 패키지 포맷

`.scoda` 파일은 ZIP 아카이브로, 다음 구조를 가진다:

```
trilobase.scoda (ZIP)
├── manifest.json           # 패키지 메타데이터
├── data.db                 # SQLite 데이터베이스
└── assets/                 # 향후 이미지/문서용 디렉토리 (현재 비어 있음)
```

**manifest.json 규격:**
```json
{
  "format": "scoda",
  "format_version": "1.0",
  "name": "trilobase",
  "version": "1.0.0",
  "title": "Trilobase - Trilobite Genus Database",
  "description": "Trilobite genus-level taxonomy database based on Jell & Adrain (2002)",
  "created_at": "2026-02-12T00:00:00+00:00",
  "license": "CC-BY-4.0",
  "authors": ["Jell, P.A.", "Adrain, J.M."],
  "data_file": "data.db",
  "record_count": 5340,
  "data_checksum_sha256": "abcdef1234..."
}
```

### 배포 구조 변경

```
BEFORE (현재):                        AFTER (변경 후):
trilobase.exe (DB 내장)              trilobase.exe (DB 미포함)
trilobase_mcp.exe (DB 내장)          trilobase_mcp.exe (DB 미포함)
trilobase_overlay.db                 trilobase.scoda (데이터 패키지)
                                     trilobase_overlay.db
```

## 설계

### 1. scoda_package.py — 핵심 모듈

두 가지 역할을 하나의 모듈에 통합:

**A. ScodaPackage 클래스:**

```python
class ScodaPackage:
    """Read-only access to a .scoda ZIP package."""

    def __init__(self, scoda_path):
        # ZIP 파일 경로 저장
        # atexit에 cleanup 등록

    @property
    def manifest(self):
        """Lazy-load manifest.json"""

    @property
    def db_path(self):
        """Lazy-extract data.db to temp directory"""

    def get_asset(self, asset_name):
        """Read asset from ZIP (향후 이미지 접근용)"""

    def list_assets(self):
        """List all assets in package"""

    def close(self):
        """Clean up temp files"""

    @staticmethod
    def create(db_path, output_path, extra_metadata=None):
        """Build .scoda from SQLite DB"""
```

**B. 중앙 집중 DB 접근 함수:**

```python
# 경로 해석 (한 곳에서만 관리)
def _resolve_paths():
    """
    Frozen 모드: exe 옆에서 trilobase.scoda 탐색
    Dev 모드:    프로젝트 루트에서 trilobase.scoda 탐색, 없으면 trilobase.db 폴백
    Overlay:     항상 .scoda/.db 옆에 trilobase_overlay.db
    """

# 공개 API
def get_db():           # canonical + overlay ATTACH 연결 반환 (기존과 동일 시그니처)
def ensure_overlay_db() # overlay DB 자동 생성 (통합 구현)
def get_scoda_info()    # GUI 표시용 패키지 정보
def _set_paths_for_testing(canonical_db, overlay_db)  # 테스트용 경로 오버라이드
```

### 2. scripts/create_scoda.py — 빌드 스크립트

```bash
python scripts/create_scoda.py                  # trilobase.db → trilobase.scoda
python scripts/create_scoda.py --dry-run        # manifest 미리보기
python scripts/create_scoda.py --db path/to/db  # 커스텀 입력
```

`artifact_metadata` 테이블에서 메타데이터를 읽어 manifest.json 생성.

### 3. 기존 파일 리팩토링

**app.py:**
- 삭제: Lines 14-105 (경로 해석, `_ensure_overlay_db`, `_create_overlay_db_inline`, `get_db`)
- 추가: `from scoda_package import get_db`
- 12개 라우트는 변경 없음 (`get_db()` 시그니처 동일)

**mcp_server.py:**
- 삭제: Lines 16-65 (경로 해석, `get_db`, `init_overlay_db`)
- 추가: `from scoda_package import get_db, ensure_overlay_db`
- 14개 MCP 도구는 변경 없음

**scripts/gui.py:**
- 삭제: Lines 64-87 (DB 경로 해석)
- 추가: `scoda_package.get_scoda_info()` 사용
- Information 패널에 `.scoda` 정보 표시

**trilobase.spec:**
- GUI exe: `('trilobase.db', '.')` 제거, `('scoda_package.py', '.')` 추가
- MCP exe: `('trilobase.db', '.')` 제거, `('scoda_package.py', '.')` 추가

### 4. 테스트 수정

**test_app.py `client` fixture:**
```python
# BEFORE (line 431-433):
monkeypatch.setattr(app_module, 'CANONICAL_DB', canonical_db_path)
monkeypatch.setattr(app_module, 'OVERLAY_DB', overlay_db_path)

# AFTER:
import scoda_package
scoda_package._set_paths_for_testing(canonical_db_path, overlay_db_path)
```

**ScodaPackage 테스트 추가:**
- .scoda 생성/열기/manifest 검증
- checksum 일치 확인
- temp 파일 정리 확인
- get_db() + overlay ATTACH 동작 확인

### 5. 빌드/릴리스 수정

- `scripts/build.py`: 빌드 후 `dist/`에 .scoda도 생성
- `scripts/release.py`: 릴리스 디렉토리에 .scoda 포함
- `.gitignore`: `*.scoda` 추가

## 구현 순서

```
Step  1: scoda_package.py 신규 생성 (핵심 모듈)
Step  2: scripts/create_scoda.py 신규 생성 + trilobase.scoda 빌드
Step  3: app.py 리팩토링 (중복 로직 제거)
Step  4: mcp_server.py 리팩토링
Step  5: scripts/gui.py 리팩토링
Step  6: trilobase.spec 수정 (DB 번들링 제거)
Step  7: test_app.py 수정 (fixture 변경 + 테스트 추가)
Step  8: scripts/release.py, build.py 수정
Step  9: .gitignore 수정
Step 10: 문서 (devlog, HANDOVER.md)
```

## 커밋 전략

1. **Commit A**: `scoda_package.py` + `scripts/create_scoda.py` (신규 파일, 기존 코드 불변)
2. **Commit B**: `app.py`, `mcp_server.py`, `gui.py` 리팩토링 (import 변경)
3. **Commit C**: `trilobase.spec`, `build.py`, `release.py` 수정
4. **Commit D**: `test_app.py` 수정 + 테스트 통과 확인
5. **Commit E**: 문서 + `.gitignore`

## 수정 파일 목록

| 파일 | 변경 유형 |
|------|----------|
| `scoda_package.py` | **신규** |
| `scripts/create_scoda.py` | **신규** |
| `app.py` | 수정 — 90줄 삭제, import 1줄 추가 |
| `mcp_server.py` | 수정 — 50줄 삭제, import 1줄 추가 |
| `scripts/gui.py` | 수정 — DB 경로 로직 교체 |
| `trilobase.spec` | 수정 — DB 번들링 제거 |
| `test_app.py` | 수정 — fixture 변경 + 테스트 추가 |
| `scripts/release.py` | 수정 |
| `scripts/build.py` | 수정 |
| `.gitignore` | 수정 |

## 검증 방법

1. `python scripts/create_scoda.py --dry-run` — manifest 미리보기
2. `python scripts/create_scoda.py` — trilobase.scoda 생성
3. `unzip -l trilobase.scoda` — ZIP 구조 확인
4. `trilobase.db` 삭제 후 `python app.py` — .scoda 모드로 Flask 기동 확인
5. `python -m pytest test_app.py -v` — 전체 테스트 통과
6. `trilobase.scoda` 없이 `trilobase.db`만 있을 때 폴백 동작 확인
