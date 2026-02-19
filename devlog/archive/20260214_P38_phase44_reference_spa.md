# Phase 44 계획: Reference Implementation SPA

**날짜**: 2026-02-14
**상태**: 계획

## 배경

현재 `app.js`(~1,567줄)에 **범용 SCODA 뷰어 로직**과 **trilobase 전용 로직**이 혼재되어 있다.
다른 .scoda 패키지(paleocore 등)를 동일 뷰어로 보면 trilobase 전용 section type(`genus_geography`, `synonym_list`, `rank_statistics`, `rank_children`)과 format type(`hierarchy`, `temporal_range`)을 처리 못해 빈 영역이 된다.

**목표**: trilobase 전용 코드를 "Reference Implementation SPA"로 분리하여 `.scoda` 패키지의 `assets/spa/`에 번들하고, 사용자가 추출하면 Flask가 자동으로 그 SPA를 서빙한다.

## 변경 요약

| 구분 | 설명 |
|------|------|
| Built-in viewer | Generic SCODA viewer (manifest-driven only) |
| Reference SPA | 현재 full-featured 코드의 standalone 버전, `.scoda` assets에 저장 |
| 자동 전환 | 추출된 SPA 디렉토리 있으면 서빙, 없으면 generic |
| 추출 | GUI "Extract Reference SPA" 버튼 |

## Manifest의 Trilobase 전용 요소

**Detail view sections:**
- `genus_detail`: `genus_geography`, `synonym_list` (+ `field_grid`, `raw_text`, `annotations`)
- `rank_detail`: `rank_statistics`, `rank_children` (+ `field_grid`, `raw_text`, `annotations`)

**Field format types:**
- `hierarchy` (taxonomy 계층 breadcrumb)
- `temporal_range` (temporal code + ICS 매핑 링크)

**범용 section types** (generic viewer에서 처리):
- `field_grid`, `linked_table`, `tagged_list`, `raw_text`, `annotations`

---

## Step 1: Reference SPA 파일 생성 (`spa/` 디렉토리)

현재 코드를 standalone SPA로 복사/변환.

### `spa/index.html` (신규)
- `templates/index.html` 기반, Jinja2 없음
- 경로 변환: `/static/css/style.css` → `./style.css`, `/static/js/app.js` → `./app.js`
- API_BASE 자동 감지 스크립트 추가:
  ```html
  <script>
  const API_BASE = window.location.protocol === 'file:' ? 'http://localhost:8080' : '';
  </script>
  ```

### `spa/app.js` (신규)
- 현재 `static/js/app.js` 복사
- 모든 `fetch('/api/...)` → `fetch(API_BASE + '/api/...')` 전환 (~15곳)
- `renderDetailFromManifest()`의 `view.source` URL도 API_BASE prefix 추가

### `spa/style.css` (신규)
- 현재 `static/css/style.css` 그대로 복사 (변경 없음)

---

## Step 2: Built-in viewer를 Generic으로 축소

### `static/js/app.js` 수정
trilobase 전용 함수 **제거**:
- `buildHierarchyHTML()` (line 922-932)
- `buildTemporalRangeHTML()` (line 907-919)
- `renderGenusGeography()` (line 1364-1404)
- `renderSynonymList()` (line 1406-1441)
- `renderRankStatistics()` (line 1443-1466)
- `renderRankChildren()` (line 1468-1497)
- `navigateToRank()` (line 864-870)
- `navigateToGenus()` (line 871-878)
- `selectFamily()` 별칭 (line 752)

`formatFieldValue()` 수정:
- `case 'hierarchy'`: 텍스트로 표시 (hierarchy 배열이면 name join, 아니면 그대로)
- `case 'temporal_range'`: `<code>` 태그만 (ICS 링크 없이)

`renderDetailSection()` 수정:
- `genus_geography`, `synonym_list`, `rank_statistics`, `rank_children` case 제거
- `default`: `section.data_key`가 있고 데이터가 배열이면 `renderLinkedTable()` fallback, 아니면 skip

### `static/css/style.css` 수정
- `.rank-Class`, `.rank-Order`, `.rank-Suborder`, `.rank-Superfamily`, `.rank-Family` 색상 규칙 제거

### `templates/index.html`
- 변경 없음 (이미 generic 구조)

---

## Step 3: `ScodaPackage` 확장 (`scoda_package.py`)

### `create()` 메서드에 `extra_assets` 파라미터 추가
```python
@staticmethod
def create(db_path, output_path, metadata=None, extra_assets=None):
    # ... 기존 코드 ...
    with zipfile.ZipFile(...) as zf:
        # ... manifest + data.db ...
        if extra_assets:
            for archive_path, local_path in extra_assets.items():
                zf.write(local_path, archive_path)
```

### 새 메서드/프로퍼티 추가
- `has_reference_spa` (property): `manifest.get('has_reference_spa', False)`
- `extract_spa(output_dir=None)`: assets/spa/ 파일을 외부 디렉토리로 추출
  - 기본 경로: `<scoda_dir>/<name>_spa/`
- `get_spa_dir()`: 예상 SPA 추출 경로 반환
- `is_spa_extracted()`: 추출 완료 여부 확인

---

## Step 4: `.scoda` 패키징에 SPA 포함

### `scripts/create_scoda.py` 수정
- `spa/` 디렉토리의 파일들을 `extra_assets`로 전달
- manifest에 `has_reference_spa: true`, `reference_spa_path: "assets/spa/"` 추가

### `scripts/build.py` 수정
- `create_scoda_package()`에서 SPA 파일 포함

### `.scoda` 결과 구조:
```
trilobase.scoda (ZIP)
├── manifest.json          # has_reference_spa: true
├── data.db
└── assets/
    └── spa/
        ├── index.html
        ├── app.js
        └── style.css
```

---

## Step 5: Flask 자동 전환 (`app.py`)

### `index()` 라우트 수정
```python
@app.route('/')
def index():
    spa_dir = _get_reference_spa_dir()
    if spa_dir:
        return send_from_directory(spa_dir, 'index.html')
    return render_template('index.html')
```

### SPA 에셋 서빙 라우트 추가
```python
@app.route('/<path:filename>')
def serve_spa_file(filename):
    spa_dir = _get_reference_spa_dir()
    if spa_dir and os.path.isfile(os.path.join(spa_dir, filename)):
        return send_from_directory(spa_dir, filename)
    return '', 404
```
- 모든 `/api/*` 라우트보다 **후순위**로 등록 (Flask는 구체적 라우트 우선)
- `send_from_directory`로 안전하게 서빙

### `_get_reference_spa_dir()` 헬퍼
- 활성 패키지의 `.scoda` 위치 기준으로 `<name>_spa/` 디렉토리 확인
- `index.html` 존재하면 해당 경로 반환, 아니면 `None`

---

## Step 6: GUI 추출 UI (`scripts/gui.py`)

### "Extract Reference SPA" 버튼 추가
- 선택된 패키지에 `has_reference_spa`일 때만 활성화
- 클릭 시:
  - 이미 추출됨 → "이미 추출됨. 브라우저에서 열까요?" 확인
  - 미추출 → `ScodaPackage.extract_spa()` 호출 → 로그 표시 → 브라우저 열기 제안
- `_update_status()`에서 버튼 상태 관리

---

## Step 7: PyInstaller 설정 (`ScodaDesktop.spec`)

### datas에 `spa/` 추가
```python
datas=[
    ('app.py', '.'),
    ('scoda_package.py', '.'),
    ('templates', 'templates'),
    ('static', 'static'),
    ('spa', 'spa'),       # ← 추가: .scoda 생성 시 사용
],
```

---

## Step 8: 테스트

### `test_app.py`에 추가 (~12개)

**TestScodaPackageSPA** (6개):
- `test_create_with_spa`: extra_assets로 .scoda 생성, assets/spa/ 파일 확인
- `test_has_reference_spa`: manifest 플래그 확인
- `test_extract_spa`: 추출 후 파일 존재 확인
- `test_extract_spa_default_dir`: 기본 디렉토리 이름 `<name>_spa/`
- `test_is_spa_extracted`: 추출 전 False, 추출 후 True
- `test_extract_no_spa_raises`: SPA 없는 패키지에서 ValueError

**TestFlaskAutoSwitch** (4개):
- `test_index_generic_without_spa`: SPA 미추출 시 generic viewer 서빙
- `test_index_reference_spa_when_extracted`: SPA 추출 시 reference SPA 서빙
- `test_spa_assets_served`: 추출 후 `./app.js`, `./style.css` 정상 서빙
- `test_api_routes_take_priority`: `/api/manifest` 등은 SPA 서빙에 영향 없음

**TestGenericViewerFallback** (2개):
- `test_unknown_section_type_graceful`: 알 수 없는 section type이 에러 없이 처리됨
- (프론트엔드 로직이므로 기본적으로 수동 검증, 서버 측은 기존 테스트로 커버)

---

## 구현 순서

1. **Step 1**: `spa/` 디렉토리에 Reference SPA 파일 생성
2. **Step 2**: `static/js/app.js`, `static/css/style.css` generic으로 축소
3. **Step 3**: `scoda_package.py` — `create()` 확장 + 새 메서드
4. **Step 4**: `scripts/create_scoda.py`, `scripts/build.py` — SPA 패키징
5. **Step 5**: `app.py` — 자동 전환 로직
6. **Step 6**: `scripts/gui.py` — 추출 UI
7. **Step 7**: `ScodaDesktop.spec` — 빌드 설정
8. **Step 8**: 테스트

---

## 검증 방법

1. `pytest test_app.py` — 기존 217개 + 신규 ~12개 전부 통과
2. `python app.py --package trilobase` → `http://localhost:8080/` → generic viewer 확인
3. GUI에서 "Extract Reference SPA" → `trilobase_spa/` 디렉토리 생성 확인
4. Flask 재시작 → `http://localhost:8080/` → reference SPA 자동 전환 확인
5. `trilobase_spa/index.html` 더블클릭 → file:// 프로토콜로 API 접속 확인
6. `paleocore` 패키지 선택 → SPA 없으므로 generic viewer 서빙 확인

---

## 수정 대상 파일 요약

| 파일 | 작업 |
|------|------|
| `spa/index.html` | **신규** — standalone HTML |
| `spa/app.js` | **신규** — full-featured JS (API_BASE prefix) |
| `spa/style.css` | **신규** — full CSS 복사 |
| `static/js/app.js` | **수정** — trilobase 전용 함수 제거, fallback 추가 |
| `static/css/style.css` | **수정** — rank 전용 CSS 제거 |
| `scoda_package.py` | **수정** — create() 확장, SPA 관련 메서드 추가 |
| `scripts/create_scoda.py` | **수정** — SPA 파일 패키징 |
| `scripts/build.py` | **수정** — SPA 포함 빌드 |
| `app.py` | **수정** — 자동 전환 로직, SPA 에셋 서빙 |
| `scripts/gui.py` | **수정** — Extract Reference SPA 버튼 |
| `ScodaDesktop.spec` | **수정** — spa/ datas 추가 |
| `test_app.py` | **수정** — 신규 테스트 ~12개 |
