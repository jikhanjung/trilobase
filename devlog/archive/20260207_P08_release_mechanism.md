# Phase 16: 릴리스 메커니즘 구현 계획

**날짜:** 2026-02-07

## 배경

SCODA의 핵심 원칙인 **불변성(immutability)** 과 **"silent mutation 없음"** 을 실현하는 릴리스 메커니즘. 버전된 DB 사본 + 메타데이터 JSON + SHA-256 체크섬을 포함한 배포 패키지를 생성하는 오프라인 스크립트.

Phase 13-15에서 DB 내부에 identity, provenance, schema descriptions, display intent, queries, UI manifest를 갖추었으므로, 이제 이를 **자기완결적(self-contained) 배포 아티팩트**로 패키징하는 단계.

## 구현 단계

### 1. `.gitignore` 수정

`releases/` 디렉토리 추가 (바이너리 릴리스 아티팩트 추적 방지):

```
releases/
```

### 2. 릴리스 스크립트: `scripts/release.py` (신규)

**핵심 함수:**

- `get_version(db_path)` — artifact_metadata에서 version 읽기
- `calculate_sha256(file_path)` — SHA-256 해시 계산 (8KB 청크)
- `store_sha256(db_path, sha256_hash)` — 소스 DB에 sha256 키 저장
- `get_statistics(db_path)` — DB 통계 계산 (`app.py:288-309`의 로직 재사용)
- `get_provenance(db_path)` — provenance 레코드 목록 반환
- `build_metadata_json(db_path, sha256_hash)` — metadata.json 내용 생성
- `generate_readme(version, sha256_hash, stats)` — 릴리스용 README.md 생성
- `create_release(db_path, output_dir)` — 메인 오케스트레이션 함수
- `main()` — CLI 진입점 (`--dry-run` 옵션 지원)

**create_release 흐름:**

1. DB 존재 + version 메타데이터 검증
2. 릴리스 디렉토리 `releases/trilobase-v{version}/` 경로 결정
3. **이미 존재하면 중단** (불변성 원칙 — 덮어쓰기 불가)
4. DB를 릴리스 디렉토리에 복사
5. 복사본을 read-only로 설정 (chmod 444)
6. **릴리스 복사본**의 SHA-256 계산 (chicken-and-egg 문제 회피)
7. 소스 DB의 artifact_metadata에 sha256 저장
8. metadata.json 생성 + 기록
9. checksums.sha256 생성 (형식: `<hash>  trilobase.db`, sha256sum --check 호환)
10. README.md 생성
11. 결과 출력 + git tag 명령어 안내 (자동 실행하지 않음)

**--dry-run 모드:**
- 파일 생성/복사/DB 수정 없이 계획만 출력

**릴리스 디렉토리 구조:**
```
releases/trilobase-v1.0.0/
├── trilobase.db          # Read-only SQLite DB
├── metadata.json         # 메타데이터 + 출처 + 통계
├── checksums.sha256      # SHA-256 해시
└── README.md             # 사용 안내
```

### 3. metadata.json 구조

```json
{
  "artifact_id": "trilobase",
  "name": "Trilobase",
  "version": "1.0.0",
  "schema_version": "1.0",
  "created_at": "2026-02-07",
  "description": "Trilobite genus-level taxonomy database...",
  "license": "CC-BY-4.0",
  "released_at": "2026-02-07T...",
  "sha256": "abc123...",
  "provenance": [
    {"source_type": "primary", "citation": "Jell & Adrain (2002)", ...},
    ...
  ],
  "statistics": {
    "genera": 5113, "valid_genera": 4258, "families": 191,
    "orders": 12, "synonyms": 1055, "bibliography": 2130,
    "formations": 2009, "countries": 151
  }
}
```

### 4. 테스트: `test_app.py` 수정

`TestRelease` 클래스 (~12개 테스트), 기존 `test_db` fixture 재사용:

| 테스트 | 검증 내용 |
|--------|----------|
| `test_get_version` | version "1.0.0" 반환 |
| `test_get_version_missing` | version 없는 DB에서 SystemExit |
| `test_calculate_sha256` | 64자 hex 문자열 반환 |
| `test_calculate_sha256_deterministic` | 동일 파일 → 동일 해시 |
| `test_calculate_sha256_changes` | DB 수정 후 해시 변경 |
| `test_get_statistics` | 테스트 DB 통계 정확 (genera=4, valid=3 등) |
| `test_get_provenance` | 2개 provenance 레코드 + 구조 |
| `test_build_metadata_json` | 필수 키 포함 (artifact_id, version, provenance, statistics, released_at) |
| `test_generate_readme` | version, hash, statistics 포함 |
| `test_create_release` | 통합: 디렉토리 + 4개 파일 생성, DB read-only, JSON 유효, checksums 정확 |
| `test_create_release_already_exists` | 중복 릴리스 시 에러 |
| `test_store_sha256` | artifact_metadata에 sha256 키 저장 |

임포트: `sys.path.insert(0, ...)` + `from release import ...`

### 5. 릴리스 실행 및 검증

```bash
python scripts/release.py --dry-run    # 사전 확인
python scripts/release.py              # 실제 릴리스
sha256sum --check releases/trilobase-v1.0.0/checksums.sha256
```

### 6. 문서 (코드 커밋 전 작성)

1. `devlog/20260207_015_phase16_release_mechanism.md` 작성
2. `docs/HANDOVER.md` 갱신 (Phase 16 완료, 테스트 수 업데이트)
3. 코드 + 문서 함께 커밋

## 설계 결정

| 항목 | 결정 | 이유 |
|------|------|------|
| SHA-256 대상 | 릴리스 복사본 | chicken-and-egg 문제 회피 |
| API 변경 | 없음 | `/api/metadata`가 자동으로 sha256 반영 |
| git tag | 수동 (안내 출력) | 비가역적 작업은 사용자 확인 필요 |
| 중복 릴리스 | 에러 중단 | SCODA 불변성 원칙 |
| 테스트 위치 | test_app.py | 기존 프로젝트 관례 (단일 테스트 파일) |
| `--dry-run` | 지원 | CI/검증 용도 |

## 수정 파일 요약

| 파일 | 변경 | 신규/수정 |
|------|------|----------|
| `scripts/release.py` | 릴리스 패키징 스크립트 | 신규 |
| `.gitignore` | `releases/` 추가 | 수정 |
| `test_app.py` | TestRelease 클래스 (~12개 테스트) | 수정 |

## 검증 방법

1. `python -m pytest test_app.py` — 기존 79개 + 신규 ~12개 = ~91개 통과
2. `python scripts/release.py --dry-run` — 부작용 없이 계획 출력
3. `python scripts/release.py` — 릴리스 디렉토리 생성
4. `sha256sum --check releases/trilobase-v1.0.0/checksums.sha256` — 무결성 검증
5. `cat releases/trilobase-v1.0.0/metadata.json | python -m json.tool` — JSON 유효성
6. `curl http://localhost:8080/api/metadata` — sha256 키 확인
