# Phase 16: 릴리스 메커니즘 구현 완료

**날짜:** 2026-02-07

## 작업 내용

SCODA 불변성 원칙에 따라 버전된 릴리스 패키지를 생성하는 오프라인 스크립트를 구현.

### 구현된 기능

1. **릴리스 스크립트** (`scripts/release.py`)
   - `get_version()` — artifact_metadata에서 version 읽기
   - `calculate_sha256()` — SHA-256 해시 계산 (8KB 청크)
   - `store_sha256()` — 소스 DB에 sha256 키 저장
   - `get_statistics()` — DB 통계 계산 (app.py 로직 재사용)
   - `get_provenance()` — provenance 레코드 목록 반환
   - `build_metadata_json()` — metadata.json 내용 생성
   - `generate_readme()` — 릴리스용 README.md 생성
   - `create_release()` — 메인 오케스트레이션 함수
   - `main()` — CLI 진입점 (`--dry-run` 옵션 지원)

2. **릴리스 디렉토리 구조**
   ```
   releases/trilobase-v{version}/
   ├── trilobase.db          # Read-only SQLite DB
   ├── metadata.json         # 메타데이터 + 출처 + 통계
   ├── checksums.sha256      # SHA-256 해시 (sha256sum --check 호환)
   └── README.md             # 사용 안내
   ```

3. **설계 결정**
   - SHA-256은 릴리스 복사본 기준 (chicken-and-egg 문제 회피)
   - 기존 릴리스 디렉토리가 존재하면 에러 중단 (불변성 원칙)
   - git tag는 수동 (안내 출력만 — 비가역적 작업이므로)
   - API 변경 없음 (`/api/metadata`가 sha256 자동 반영)

### 수정 파일

| 파일 | 변경 | 신규/수정 |
|------|------|----------|
| `scripts/release.py` | 릴리스 패키징 스크립트 | 신규 |
| `.gitignore` | `releases/` 추가 | 수정 |
| `test_app.py` | TestRelease 클래스 (12개 테스트) | 수정 |
| `devlog/20260207_P08_release_mechanism.md` | 구현 계획 문서 | 신규 |

### 테스트 결과

- 기존 79개 + 신규 12개 = **91개 전부 통과**
- 신규 테스트:
  - `test_get_version` / `test_get_version_missing`
  - `test_calculate_sha256` / `test_calculate_sha256_deterministic` / `test_calculate_sha256_changes`
  - `test_store_sha256`
  - `test_get_statistics`
  - `test_get_provenance`
  - `test_build_metadata_json`
  - `test_generate_readme`
  - `test_create_release` (통합 테스트)
  - `test_create_release_already_exists`

### 사용법

```bash
python scripts/release.py --dry-run    # 사전 확인
python scripts/release.py              # 실제 릴리스
sha256sum --check releases/trilobase-v1.0.0/checksums.sha256  # 무결성 검증
```
