# Phase 37: PyInstaller 빌드에 paleocore.scoda 포함

**날짜:** 2026-02-13
**계획 문서:** `devlog/20260213_P31_pyinstaller_paleocore_scoda.md`

## 작업 내용

Phase 35에서 `paleocore.scoda` 패키지 생성 스크립트(`scripts/create_paleocore_scoda.py`)를 만들었으나, `scripts/build.py`는 `trilobase.scoda`만 생성하고 `paleocore.scoda`는 포함하지 않았다. 빌드 후 배포 시 `paleocore.scoda`가 누락되면 PaleoCore 데이터(countries, formations, ICS chronostratigraphy 등)에 접근 불가.

## 변경 사항

### `scripts/build.py`

1. **`create_paleocore_scoda_package()` 함수 추가** (line 93-114)
   - `paleocore.db` 존재 확인 → `ScodaPackage.create()` → `dist/paleocore.scoda`
   - PaleoCore 고유 metadata override (authors: Correlates of War Project, ICS)
   - 없으면 skip 메시지 (에러가 아님 — paleocore 없이도 trilobase는 동작)

2. **`print_results()` 수정**
   - `create_scoda_package()` 호출 후 `create_paleocore_scoda_package()` 호출
   - 배포 안내 메시지에 `paleocore.scoda` 추가

## 검증

```bash
# scoda 생성 테스트
python -c "
import sys; sys.path.insert(0, 'scripts')
from build import create_scoda_package, create_paleocore_scoda_package
import os; os.makedirs('dist', exist_ok=True)
create_scoda_package()
create_paleocore_scoda_package()
"
# ✓ .scoda package created: dist/trilobase.scoda (1.0 MB)
# ✓ paleocore.scoda package created: dist/paleocore.scoda (0.1 MB)

# 기존 테스트 영향 없음
pytest test_app.py -v
# 161 passed
```

## 배포 구조 (최종)

```
dist/
├── trilobase         # (또는 trilobase.exe) GUI 뷰어
├── trilobase_mcp     # (또는 trilobase_mcp.exe) MCP stdio 서버
├── trilobase.scoda   # Trilobase 데이터 패키지
└── paleocore.scoda   # PaleoCore 데이터 패키지
```
