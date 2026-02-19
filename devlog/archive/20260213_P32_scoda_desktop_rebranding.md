# Plan: Phase 38 — GUI를 "SCODA Desktop"으로 리브랜딩 + 로드된 패키지 목록 표시

**날짜:** 2026-02-13

## 배경

현재 GUI(`scripts/gui.py`)는 "Trilobase SCODA Viewer"라는 이름으로 Trilobase 전용처럼 보인다. 실제로는 trilobase.scoda + paleocore.scoda 두 패키지를 동시에 로드하지만, 어떤 패키지가 로드되었는지 GUI에서 확인할 수 없다. 또한 PaleoCore가 dependency로 함께 로드된다는 것도 로그에 나타나지 않는다.

## 변경 목표

1. **이름 변경**: "Trilobase SCODA Viewer" → "SCODA Desktop" (제목, 헤더, 로그 메시지)
2. **Information 섹션**: 로드된 SCODA 패키지 목록 표시 (trilobase + paleocore)
3. **시작 로그**: dependency 관계 로그 메시지 (trilobase.scoda 로드 → paleocore.scoda dependency 로드)

## 수정 파일

| 파일 | 변경 |
|---|---|
| `scripts/gui.py` | 제목/헤더 변경, Information 섹션에 패키지 목록 추가, 초기 로그 메시지 개선 |
| `scoda_package.py` | `get_scoda_info()`에서 PaleoCore 패키지 버전/이름 정보 추가 반환 |

## 구현 상세

### 1. `scripts/gui.py` 이름 변경 (3곳)

- `self.root.title("Trilobase SCODA Viewer")` → `self.root.title("SCODA Desktop")`
- 헤더 Label `text="Trilobase SCODA Viewer"` → `text="SCODA Desktop"`
- 초기 로그 `"Trilobase SCODA Viewer initialized"` → `"SCODA Desktop initialized"`

### 2. Information 섹션에 "Loaded Packages" 표시

기존:
```
Package:   trilobase.scoda (v0.3.0)
Overlay:   trilobase_overlay.db
Flask:     ● Stopped
Flask URL: http://localhost:8080
```

변경 후:
```
Packages:  trilobase.scoda (v0.3.0)
           └ paleocore.scoda (dependency)
Overlay:   trilobase_overlay.db
Flask:     ● Stopped
Flask URL: http://localhost:8080
```

- 기존 `db_row` label을 "Packages:"로 변경
- `paleocore_exists`이면 바로 아래에 새 행 추가
- paleocore가 없으면 행 생략

### 3. 초기 로그 메시지 개선

변경 후:
```
[HH:MM:SS] SCODA Desktop initialized
[HH:MM:SS] Loaded: trilobase.scoda (v0.3.0)
[HH:MM:SS]   └ dependency: paleocore.scoda (v0.3.0)
[HH:MM:SS] Overlay: trilobase_overlay.db
```

### 4. `scoda_package.py` — `get_scoda_info()` 확장

PaleoCore가 .scoda일 때 버전/이름/레코드 수 추가 반환:
```python
if _paleocore_pkg:
    info['paleocore_source_type'] = 'scoda'
    info['paleocore_scoda_path'] = _paleocore_pkg.scoda_path
    info['paleocore_version'] = _paleocore_pkg.version
    info['paleocore_name'] = _paleocore_pkg.name
    info['paleocore_record_count'] = _paleocore_pkg.record_count
```

## 검증

```bash
python scripts/gui.py    # 시각적 확인
pytest test_app.py -v    # 기존 테스트 영향 없음
```
