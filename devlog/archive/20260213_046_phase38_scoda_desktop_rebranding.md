# Phase 38: GUI를 "SCODA Desktop"으로 리브랜딩 + 로드된 패키지 목록 표시

**날짜:** 2026-02-13
**계획 문서:** `devlog/20260213_P32_scoda_desktop_rebranding.md`

## 변경 사항

### 1. `scoda_package.py` — `get_scoda_info()` 확장

PaleoCore가 `.scoda` 패키지일 때 추가 메타데이터 반환:
- `paleocore_version`: 패키지 버전
- `paleocore_name`: 패키지 이름
- `paleocore_record_count`: 레코드 수

### 2. `scripts/gui.py` — 리브랜딩 (3곳)

- 윈도우 타이틀: `"Trilobase SCODA Viewer"` → `"SCODA Desktop"`
- 헤더 라벨: `"Trilobase SCODA Viewer"` → `"SCODA Desktop"`
- 초기 로그: `"Trilobase SCODA Viewer initialized"` → `"SCODA Desktop initialized"`
- 모듈 docstring: `"Trilobase GUI Control Panel"` → `"SCODA Desktop — GUI Control Panel"`

### 3. `scripts/gui.py` — Information 섹션 패키지 목록

- `"Package:"` 라벨 → `"Packages:"` (scoda 모드일 때)
- PaleoCore dependency 행 신규 추가:
  - `.scoda`: `└ paleocore.scoda (vX.Y.Z, dependency)`
  - `.db` 폴백: `└ paleocore.db (dependency)`
  - 미존재 시: 행 자체 생략

### 4. `scripts/gui.py` — 시작 로그 메시지 개선

변경 전:
```
[HH:MM:SS] Trilobase SCODA Viewer initialized
[HH:MM:SS] Package: trilobase.scoda (v0.3.0)
[HH:MM:SS] Overlay DB: trilobase_overlay.db
```

변경 후:
```
[HH:MM:SS] SCODA Desktop initialized
[HH:MM:SS] Loaded: trilobase.scoda (v0.3.0)
[HH:MM:SS]   └ dependency: paleocore.scoda (v0.3.0)
[HH:MM:SS] Overlay: trilobase_overlay.db
```

## 테스트

- `pytest test_app.py -v` → **161개 전부 통과** (변경 영향 없음)
- GUI 변경은 시각적 확인 필요 (`python scripts/gui.py`)

## 수정 파일

| 파일 | 변경 |
|---|---|
| `scoda_package.py` | `get_scoda_info()` paleocore 메타데이터 3개 필드 추가 |
| `scripts/gui.py` | 리브랜딩 + 패키지 목록 + 로그 개선 |
