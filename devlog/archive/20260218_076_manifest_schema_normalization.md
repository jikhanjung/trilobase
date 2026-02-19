# 076: Manifest Schema 정규화 — DB 레벨 (A-3)

**날짜:** 2026-02-18
**계획 문서:** `devlog/20260218_P59_manifest_schema_normalization.md`

## 작업 내용

DB의 ui_manifest를 새 `type: "hierarchy"` 스키마로 직접 업데이트.
기존 `type: "tree"` + `tree_options` / `type: "chart"` + `chart_options`를
`type: "hierarchy"` + `display` + `hierarchy_options` + `tree_display` / `nested_table_display`로 전환.

### 변환 요약

| DB | 뷰 | 변경 전 | 변경 후 |
|----|-----|---------|---------|
| trilobase.db | taxonomy_tree | `type: "tree"` | `type: "hierarchy", display: "tree"` |
| trilobase.db | chronostratigraphy_table | `type: "chart"` | `type: "hierarchy", display: "nested_table"` |
| paleocore.db | chronostratigraphy_chart | `type: "chart"` | `type: "hierarchy", display: "nested_table"` |

### 수정 파일

| 파일 | 작업 |
|------|------|
| `scripts/add_scoda_manifest.py` | tree→hierarchy, chart→hierarchy 전환 |
| `scripts/create_paleocore.py` | chart→hierarchy 전환 |
| `scripts/validate_manifest.py` | hierarchy view 검증 강화 (tree_display, nested_table_display) |
| `tests/conftest.py` | test fixture manifest 정규화 |
| `tests/test_trilobase.py` | TestManifestTreeChart → TestManifestHierarchy 전환 |
| `tests/test_runtime.py` | tree type 검증 → hierarchy type 검증 |
| `trilobase.db` | manifest 갱신 (add_scoda_manifest.py 실행) |
| `paleocore.db` | manifest 갱신 (직접 UPDATE) |

### 하위 호환

- `app.js`의 `normalizeViewDef()`는 유지 (외부 .scoda 패키지 하위 호환)
- `validate_manifest.py`의 `KNOWN_VIEW_TYPES`에 `tree`, `chart` 유지

## 테스트: 247개 전부 통과

- trilobase.db: validator OK (0 error, 0 warning)
- paleocore.db: validator OK (0 error, 0 warning)
