# Plan: PyInstaller 빌드에 paleocore.scoda 포함

**날짜:** 2026-02-13
**상태:** 📋 계획

## 배경

Phase 35에서 `paleocore.scoda` 패키지를 생성했고, Phase 36에서 두 `.scoda` 조합 배포 테스트를 완료했다. 그러나 `scripts/build.py`는 `trilobase.scoda`만 생성하고 `paleocore.scoda`는 포함하지 않는다. 빌드 후 배포 시 `paleocore.scoda`가 누락되면 PaleoCore 데이터(countries, formations, ICS chronostratigraphy 등)에 접근할 수 없다.

## 현재 상태

- `scripts/build.py`: PyInstaller 빌드 후 `dist/trilobase.scoda`만 생성
- `scripts/create_paleocore_scoda.py`: 독립 실행 스크립트 (수동으로 `paleocore.scoda` 생성)
- `scoda_package.py`의 `_resolve_paleocore()`: exe_dir에서 `paleocore.scoda` 자동 탐색 → `.db` 폴백 (이미 구현됨)
- `trilobase.spec`: .scoda는 EXE 내부 번들이 아닌 외부 파일 (변경 불필요)

## 수정 작업

### `scripts/build.py` 변경

1. **`create_paleocore_scoda_package()` 함수 추가**
   - `paleocore.db` 존재 확인 → `ScodaPackage.create()` → `dist/paleocore.scoda`
   - PaleoCore 고유 metadata override (authors 등 — `create_paleocore_scoda.py`와 동일 패턴)
   - `paleocore.db` 없으면 skip 메시지 출력 (에러가 아님 — paleocore 없이도 trilobase는 동작)

2. **`print_results()` 수정**
   - `create_scoda_package()` 호출 후 `create_paleocore_scoda_package()` 호출
   - 배포 안내 메시지에 `paleocore.scoda` 추가

## 수정 파일

| 파일 | 변경 |
|---|---|
| `scripts/build.py` | `create_paleocore_scoda_package()` 추가 + `print_results()` 갱신 |

## 검증

```bash
# scoda 생성 기능만 테스트 (PyInstaller 실행 제외)
python -c "
import sys; sys.path.insert(0, 'scripts')
from build import create_scoda_package, create_paleocore_scoda_package
import os; os.makedirs('dist', exist_ok=True)
create_scoda_package()
create_paleocore_scoda_package()
"
ls -la dist/*.scoda

# 기존 테스트 영향 없음
pytest test_app.py -v
```
