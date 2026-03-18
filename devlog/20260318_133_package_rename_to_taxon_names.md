# 133. SCODA 패키지명 학명 전환

**날짜:** 2026-03-18
**유형:** refactor (패키지 리네임)

---

## 배경

기존 `-base` 접미사 패키지명(trilobase, brachiobase 등)을 라틴화된 분류군명으로 변경.
레포/프로젝트 디렉토리명 `trilobase/`는 유지하되, SCODA 패키지 ID·DB 파일명·빌드 스크립트명을 일괄 전환.

## 이름 매핑

| 변경 전 | 변경 후 |
|---------|---------|
| trilobase (패키지명) | **trilobita** |
| brachiobase | **brachiopoda** |
| graptobase | **graptolithina** |
| chelicerobase | **chelicerata** |
| ostracobase | **ostracoda** |
| paleocore | (유지) |

## 변경 범위 (90개 파일, 435 ins / 426 del)

### 파일 리네임 (git mv)

- **DB 파일 (~30):** `db/trilobita-0.3.3.db`, `db/brachiopoda-0.2.6.db`, `db/graptolithina-0.1.2.db`, `db/chelicerata-0.1.2.db`, `db/ostracoda-0.1.2.db` 등 전 버전
- **빌드 스크립트 (11):**
  - `build_trilobita_db.py`, `build_trilobita_scoda.py`, `validate_trilobita_db.py`
  - `build_brachiopoda_db.py`, `build_brachiopoda_scoda.py`
  - `build_graptolithina_db.py`, `build_graptolithina_scoda.py`
  - `build_chelicerata_db.py`, `build_chelicerata_scoda.py`
  - `build_ostracoda_db.py`, `build_ostracoda_scoda.py`
- **데이터:** `data/mcp_tools_trilobita.json`

### 파일 내용 업데이트

| 카테고리 | 파일 | 변경 내용 |
|----------|------|----------|
| 빌드 스크립트 | 13개 (위 11 + build_all.py + db_path.py) | artifact_id, 함수명, regex, docstring, glob 패턴, argparse 텍스트 |
| db_path.py | 1 | `find_trilobita_db()` + backward compat alias `find_trilobase_db = find_trilobita_db` |
| 테스트 | test_trilobase.py, conftest.py | import, fixture, DB 경로, .scoda 파일명 |
| CI/CD | release.yml, manual-release.yml | 스크립트명, 릴리스 본문 텍스트 |
| 주요 문서 | CLAUDE.md, HANDOFF.md, CHANGELOG.md | DB 파일명, 스크립트명, 버전 테이블, 빌드 커맨드 |
| 도메인 문서 | PDF_SOURCE_STATUS.md | SCODA 컬럼 패키지명 |
| 설계 문서 | paleobase_design.md (v0.3) | manifest, bindings, SQL 예시, 호환성 표 등 전수 |
| docs/ | 20여 개 (schema, getting-started, architecture, project 등) | DB 파일명, manifest name, .scoda 파일명 |
| design/ | HISTORY.md, paleocore_schema.md, scoda_*_architecture.md 등 | manifest name, cache path, lockfile 예시 |

### 변경하지 않은 것

- **레포 디렉토리:** `/mnt/d/projects/trilobase/` (향후 별도 변경 예정)
- **테스트 파일명:** `test_trilobase.py` (레포 테스트로 유지)
- **레거시 스크립트:** `scripts/archive/` (비활성, 역사 보존)
- **devlog:** 기존 작업 기록 (역사 기록이므로 수정하지 않음)
- **paleocore:** 변경 없음 (분류군명이 아닌 인프라 패키지)

## 검증

- **pytest:** 117개 전부 통과 (84초)
- **활성 코드 잔여 확인:** scripts/, tests/, .github/ 에 old name 잔여 0건
  - `scripts/archive/`에만 old name 잔존 (비활성, 의도적 보존)

## 함께 진행된 작업

### docs/PDF_SOURCE_STATUS.md 현행화
- PDF 파일명 전수 수정 (실제 `data/pdf/` 파일명 반영)
- Part L vol.2 (2009): PDF ❌→✅
- Part O Rev (1997): TSF/SCODA ❌→✅
- Part I Scaphopoda (1989): 메인 테이블에 행 추가
- 요약 수치 갱신

### design/paleobase_design.md v0.3 통합 재작성
- v0.1 + v0.2 문서를 v0.3으로 통합 (paleobase_v0.2.md 삭제)
- graptobase(→graptolithina) 추가, meta_tree 8개 Phylum 노드 완성
- 현행 assertion 모델·SCODA manifest 스키마와 정합
- Implementation Roadmap (Stage 0~3) 신규 작성
