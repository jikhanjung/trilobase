# 134. Paleobase Stage 0~1 구현

**날짜:** 2026-03-18
**유형:** feat
**관련 문서:** P89 (Paleobase Meta-Package 설계)

---

## Stage 0: 사전 준비 (완료)

### 1. trilobita DB에 Phylum Arthropoda 추가

- `taxon` 테이블 rank CHECK 제약에 `'Phylum'` 추가
- `RANK_ORDER` 딕셔너리에 Phylum 추가 (최상위)
- Phylum Arthropoda (id=5345) taxon 자동 생성
- 3개 프로파일 모두 `Arthropoda → Trilobita` edge 포함
- taxon 5627→5628 (+1), edge_cache 8930→8933 (+3)

### 2. 4개 패키지에 paleocore 의존성 선언

brachiopoda, graptolithina, chelicerata, ostracoda의 `build_*_scoda.py`에 paleocore 의존성 추가:
- hub manifest: `"dependencies": {"paleocore": ">=0.1.1,<0.2.0"}`
- ScodaPackage metadata: `name/alias/version/file/required/description` 전체 블록

### 3. artifact_metadata 포맷 통일

4개 DB 빌드 스크립트에 `schema_version: "1.0"` 추가. 5개 패키지 모두 동일 메타데이터 키 보유:
`artifact_id`, `name`, `version`, `description`, `license`, `schema_version`, `created_at`

---

## Stage 1: Meta-Package 기초 (부분 완료)

### 완료

**데이터 파일 생성:**
- `data/paleobase_meta_tree.json` — 11개 노드 (Life→Eukaryota→Metazoa + 8 Phylum)
- `data/paleobase_bindings.json` — 5개 바인딩 (Arthropoda×3, Brachiopoda×1, Hemichordata×1)

**빌드 스크립트:**
- `scripts/build_paleobase_scoda.py` — meta-package .scoda 빌드
  - manifest.json + meta_tree.json + package_bindings.json을 ZIP으로 패키징
  - hub manifest 자동 생성
  - `--dry-run` 옵션 지원

**빌드 결과:**
- `dist/paleobase-0.1.0.scoda` (1,464 bytes)
- `dist/paleobase-0.1.0.manifest.json`

### 미완료 (scoda-engine 레포 작업 필요)

- scoda-engine에 `kind: "meta-package"` 인식 로직
- meta_tree + bindings 로딩 및 트리 합성 UI

---

## 변경 파일 목록

| 파일 | 변경 |
|------|------|
| `scripts/build_trilobita_db.py` | Phylum rank 추가, Arthropoda taxon/edge 생성 |
| `scripts/build_brachiopoda_scoda.py` | paleocore 의존성 추가 |
| `scripts/build_graptolithina_scoda.py` | paleocore 의존성 추가 |
| `scripts/build_chelicerata_scoda.py` | paleocore 의존성 추가 |
| `scripts/build_ostracoda_scoda.py` | paleocore 의존성 추가 |
| `scripts/build_brachiopoda_db.py` | schema_version 추가 |
| `scripts/build_graptolithina_db.py` | schema_version 추가 |
| `scripts/build_chelicerata_db.py` | schema_version 추가 |
| `scripts/build_ostracoda_db.py` | schema_version 추가 |
| `scripts/build_paleobase_scoda.py` | **신규** — meta-package 빌드 |
| `data/paleobase_meta_tree.json` | **신규** — 11 nodes |
| `data/paleobase_bindings.json` | **신규** — 5 bindings |

## 검증

- 117 tests passing
- 6개 .scoda 패키지 정상 빌드 (trilobita, brachiopoda, graptolithina, chelicerata, ostracoda, paleobase)
