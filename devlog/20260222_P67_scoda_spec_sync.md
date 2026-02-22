# P67: SCODA 스펙 문서 ↔ 빌드 스크립트 일치화

**날짜:** 2026-02-22

## 배경

`docs/scoda_package_architecture.md` 스펙과 `scripts/create_scoda.py` 구현 사이에 3가지 불일치 발견:

| 항목 | 스펙 (문서) | 구현 (스크립트) | 결정 |
|------|------------|----------------|------|
| checksum | 별도 `checksums.sha256` 파일 | manifest 내 `data_checksum_sha256` 필드 | **구현 채택** — 단일 data.db에 별도 파일 불필요 |
| dependency version | range (`>=0.3.0,<0.4.0`) | 고정 (`0.1.1`) | **스펙 채택** — range 형식이 표준적 |
| `required` 필드 | 있음 | 없음 | **스펙 채택** — 명시적 표기 유용 |

추가: 구현에 있는 `alias`, `file`, `description` 필드가 스펙에 없음 → 스펙에 추가.

## 변경 사항

### 1. `docs/scoda_package_architecture.md`

- §2: `checksums.sha256` → manifest 내 `data_checksum_sha256` 필드로 변경, `mcp_tools.json`/`CHANGELOG.md` 추가
- §5.2: manifest 예시를 실제 구현 구조에 맞게 갱신 (version range + alias/file/description/required)

### 2. `scripts/create_scoda.py`

- dependency version: `"0.1.1"` → `">=0.1.1,<0.2.0"` (2곳)
- `"required": true` 필드 추가 (2곳)

## 검증

- `python scripts/create_scoda.py` 재빌드 → manifest.json 확인
- `pytest tests/` 통과 확인
