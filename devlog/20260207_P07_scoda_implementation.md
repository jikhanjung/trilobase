# SCODA 구현 계획

**날짜:** 2026-02-07

## 배경

SCODA(Self-Contained Data Artifact)는 데이터를 서비스가 아닌 **자기완결적 지식 객체**로 다루는 프레임워크.
핵심 철학: "데이터는 연결하는 서비스가 아니라, 열어보는 아티팩트다."

Trilobase를 SCODA의 참조 구현(reference implementation)으로 전환한다.
기존 기능은 그대로 유지하면서, SCODA 컴포넌트를 추가적으로 구현한다.

## SCODA가 요구하는 것

### 필수 (SCODA-Core)

| 요소 | 의미 | 현재 상태 |
|------|------|-----------|
| **Identity** | 이름, 버전, 고유 ID | ❌ DB에 없음 (Git만) |
| **Data** | 실제 데이터 | ✅ SQLite DB |
| **Semantics** | 스키마 설명, 필드 의미 | ❌ 문서만 존재 |
| **Provenance** | 출처, 생성 과정 | ❌ 문서만 존재 |
| **Integrity** | 해시, 버전 규칙 | ❌ 없음 |

### 선택 (SCODA-Extended)

| 요소 | 의미 | 현재 상태 |
|------|------|-----------|
| **Display Intent** | "이 데이터를 어떤 형태로 보여줄 것인가" 힌트 | ❌ |
| **Saved Queries** | 이름 붙은 재사용 가능한 쿼리 | ❌ (app.py에 하드코딩) |
| **UI Manifest** | 선언적 뷰 정의 (JSON) | ❌ |
| **UI Assets** | 내장 HTML/CSS/JS | ❌ (현재는 파일시스템) |
| **Local Overlay** | 사용자 주석 (canonical 데이터 수정 없이) | ❌ |

---

## Phase 13: SCODA-Core 메타데이터

### 목표

DB 안에 "이 아티팩트가 무엇인지" 기록. 외부 문서 없이도 DB 파일 하나만으로 자기 자신을 설명할 수 있게 한다.

### 새 테이블

#### artifact_metadata (아티팩트 신원)

| key | value 예시 | 설명 |
|-----|-----------|------|
| artifact_id | trilobase | 고유 식별자 |
| name | Trilobase | 표시 이름 |
| version | 1.0.0 | 시맨틱 버전 |
| schema_version | 1.0 | 스키마 버전 |
| created_at | 2026-02-07 | 생성일 |
| description | Trilobite genus-level taxonomy... | 설명 |
| license | CC-BY-4.0 | 라이선스 |
| sha256 | (해시값) | 무결성 검증용 |

#### provenance (출처)

어디서 온 데이터인지 기록.

| 필드 | 설명 |
|------|------|
| source_type | primary / supplementary / build |
| citation | 인용문 전체 |
| description | 이 출처가 기여한 내용 |
| year | 출판연도 |

초기 데이터:
- Jell & Adrain (2002) — primary source (genus 목록)
- Adrain (2011) — supplementary (suprafamilial 분류)

#### schema_descriptions (스키마 설명)

각 테이블과 컬럼의 의미를 DB 안에 기록.

| table_name | column_name | description |
|------------|-------------|-------------|
| taxonomic_ranks | NULL | 통합 분류 체계 (Class~Genus) |
| taxonomic_ranks | rank | Class, Order, Suborder, Superfamily, Family, Genus |
| taxonomic_ranks | is_valid | 1=유효, 0=무효 (synonym 등) |
| synonyms | synonym_type | j.s.s., j.o.s., preocc., replacement |
| ... | ... | ... |

### API 추가

- `GET /api/metadata` — 아티팩트 정보 + DB 통계 반환
- `GET /api/provenance` — 출처 목록 반환

### 작업 순서

1. [ ] `scripts/add_scoda_tables.py` 작성 — 테이블 생성 + 초기 데이터
2. [ ] 스크립트 실행하여 `trilobase.db`에 적용
3. [ ] `app.py`에 `/api/metadata`, `/api/provenance` 추가
4. [ ] `test_app.py`에 테스트 추가
5. [ ] 커밋

---

## Phase 14: Display Intent + Saved Queries

### 목표

"이 데이터를 처음 열었을 때 어떻게 보여줘야 하는가"를 DB 안에 기록.
또한 자주 쓰는 쿼리를 이름 붙여 등록해 두어, 뷰어가 재사용할 수 있게 한다.

### Display Intent란?

SCODA 4-layer UI 모델의 가장 핵심 레이어.
뷰어에게 "이 entity는 tree로 보여줘", "이건 table로" 같은 힌트를 제공.

| entity | default_view | 의미 |
|--------|-------------|------|
| genera | tree | 분류 계층이 주요 구조 |
| genera | table | 검색/필터용 평면 목록 (보조) |
| references | table | 참고문헌은 정렬 가능한 목록 |
| synonyms | graph | 동의어 관계는 네트워크 |

표준 View Type: `tree`, `table`, `detail`, `map`, `timeline`, `graph`

### Saved Queries란?

현재 `app.py`에 SQL이 하드코딩되어 있음.
이걸 DB 테이블로 옮기면, 외부 SCODA 뷰어도 동일한 쿼리를 실행할 수 있음.

등록할 쿼리:
- `taxonomy_tree` — 계층 트리 (Class~Family)
- `family_genera` — Family별 Genus 목록
- `genus_detail` — Genus 상세정보
- `rank_detail` — Rank 상세정보
- `genera_list` — 전체 Genus 평면 목록
- `bibliography_list` — 참고문헌 목록

### API 추가

- `GET /api/display-intent` — Display Intent 목록
- `GET /api/queries` — 등록된 쿼리 목록
- `GET /api/queries/<name>/execute` — Named Query 실행 (파라미터 지원)

### 작업 순서

1. [ ] `ui_display_intent`, `ui_queries` 테이블 생성
2. [ ] Display Intent 초기 데이터 삽입
3. [ ] 기존 app.py 쿼리를 Named Query로 등록
4. [ ] API 엔드포인트 구현
5. [ ] 테스트
6. [ ] 커밋

---

## Phase 15: UI Manifest

### 목표

선언적(declarative) 뷰 정의. "tree view의 label은 name 필드, 자식은 parent_id로 찾아" 같은 구조화된 지시.

### UI Manifest란?

JSON으로 된 뷰 설정. Display Intent보다 구체적이지만, HTML/CSS/JS(literal)보다는 추상적.
**뷰어가 달라도** 이 JSON을 해석해 적절한 UI를 생성할 수 있음.

```json
{
  "default_view": "taxonomy_tree",
  "views": {
    "taxonomy_tree": {
      "type": "tree",
      "source": "taxonomic_ranks",
      "label_field": "name",
      "children_field": "parent_id",
      "detail_fields": ["author", "year", "genera_count"]
    },
    "genera_table": {
      "type": "table",
      "source_query": "genera_list",
      "columns": ["name", "family", "author", "year", "temporal_code", "is_valid"],
      "default_sort": "name",
      "searchable": true
    }
  }
}
```

### Frontend 변경

- 앱 시작 시 `/api/manifest` 호출하여 뷰 정의 로드
- Tree / Table / Bibliography 뷰 전환 탭 추가
- manifest 설정에 따라 동적 렌더링

### 작업 순서

1. [ ] `ui_manifest` 테이블 생성
2. [ ] Trilobase용 manifest JSON 작성 및 삽입
3. [ ] `GET /api/manifest` 엔드포인트
4. [ ] Frontend에 뷰 전환 UI 추가
5. [ ] 테스트
6. [ ] 커밋

---

## Phase 16: 릴리스 메커니즘

### 목표

버전 태깅된 불변(immutable) 아티팩트를 생성하는 프로세스.

### 릴리스 스크립트 (`scripts/release.py`)

실행 시:
1. `artifact_metadata`에서 version 읽기
2. DB 파일의 SHA-256 해시 계산 → `artifact_metadata`에 저장
3. 릴리스 디렉토리 생성:
   ```
   releases/trilobase-v1.0.0/
   ├── trilobase.db          # 읽기 전용 DB
   ├── metadata.json         # 메타데이터 export
   ├── checksums.sha256      # 해시
   └── README.md             # 사용법
   ```
4. Git tag 생성 (v1.0.0)

### metadata.json 예시

```json
{
  "artifact_id": "trilobase",
  "name": "Trilobase",
  "version": "1.0.0",
  "created_at": "2026-02-07",
  "provenance": [...],
  "statistics": {
    "genera": 5113,
    "valid_genera": 4258,
    "families": 191,
    "synonyms": 1055,
    "bibliography": 2130
  }
}
```

### 작업 순서

1. [ ] `scripts/release.py` 작성
2. [ ] 테스트 릴리스 생성
3. [ ] 커밋

---

## Phase 17: Local Overlay (사용자 주석)

### 목표

사용자가 canonical 데이터를 변경하지 않으면서 메모, 대안적 해석, 링크 등을 추가할 수 있게 한다.

### 왜 필요한가?

분류학에서 의견 차이는 정상. 예를 들어:
- "이 genus의 family 배치에 동의하지 않음"
- "최신 논문에서 이 synonym 관계가 재검토됨"
- "나의 표본 관찰 메모"

이런 것들은 canonical 데이터를 수정하는 게 아니라, **개인 레이어**로 덧붙여야 함.

### user_annotations 테이블

| 필드 | 설명 |
|------|------|
| entity_type | genus, family, synonym 등 |
| entity_id | 대상 레코드 ID |
| annotation_type | note, correction, alternative, link |
| content | 주석 내용 |
| author | 작성자 이름 |
| created_at | 생성일시 |

### API

- `GET /api/annotations/<entity_type>/<entity_id>`
- `POST /api/annotations`
- `DELETE /api/annotations/<id>`

### Frontend

- Detail modal에 "My Notes" 섹션 추가
- 배경색으로 canonical 데이터와 시각적 구분
- 텍스트 입력 + 타입 선택 폼

### 작업 순서

1. [ ] `user_annotations` 테이블 생성
2. [ ] API 엔드포인트 구현
3. [ ] Frontend UI 구현
4. [ ] 테스트
5. [ ] 커밋

---

## 전체 파일 변경 요약

| 파일 | 변경 | Phase |
|------|------|-------|
| `scripts/add_scoda_tables.py` | **신규** | 13, 14, 15 |
| `scripts/release.py` | **신규** | 16 |
| `app.py` | 수정 (엔드포인트 추가) | 13~17 |
| `templates/index.html` | 수정 (뷰 전환, 주석 UI) | 15, 17 |
| `static/js/app.js` | 수정 (manifest 렌더링, 주석) | 15, 17 |
| `static/css/style.css` | 수정 (스타일 추가) | 15, 17 |
| `test_app.py` | 수정 (새 API 테스트) | 13~17 |

## SCODA Fallback Chain

구현 완료 후, 어떤 SCODA 뷰어라도 `trilobase.db`를 열면:

```
1. UI Assets 있음?      → (Phase 17 이후 가능) 내장 UI로 렌더링
2. UI Manifest 있음?    → (Phase 15) JSON 설정대로 뷰 생성
3. Display Intent 있음? → (Phase 14) 힌트에 따라 기본 뷰 생성
4. 아무것도 없음?       → 스키마 기반 테이블 뷰로 표시
```

각 레이어를 제거해도 그 아래 레이어가 동작. 이것이 SCODA의 "graceful degradation".

---

## DB 변경 시 SCODA 반영 전략

### 변경의 종류

Trilobase DB는 앞으로도 계속 진화할 수 있다:

| 변경 유형 | 예시 | 빈도 |
|-----------|------|------|
| **데이터 수정** | genus 오타 수정, synonym 추가, 새 문헌 반영 | 자주 |
| **데이터 추가** | 새로운 genus 등록, 새 bibliography 항목 | 자주 |
| **스키마 확장** | 새 테이블 추가 (e.g., specimens), 새 컬럼 추가 | 가끔 |
| **스키마 변경** | 기존 컬럼 타입 변경, 테이블 구조 재편 | 드물게 |
| **SCODA 레이어 변경** | 새 Display Intent, Saved Query 추가/수정 | 가끔 |

### SCODA 버전 규칙

SCODA의 핵심: **silent mutation 금지**. 모든 변경은 새 버전을 만든다.

```
version = MAJOR.MINOR.PATCH

PATCH (1.0.0 → 1.0.1)
  - 오타 수정, 소소한 데이터 보정
  - schema_version 유지

MINOR (1.0.0 → 1.1.0)
  - 새 데이터 추가 (새 genus, 새 bibliography)
  - 새 테이블/컬럼 추가 (기존 구조 깨지지 않음)
  - 새 Saved Query, Display Intent 추가
  - schema_version 유지 또는 소수점 증가 (1.0 → 1.1)

MAJOR (1.0.0 → 2.0.0)
  - 기존 테이블 구조 변경 (breaking change)
  - 기존 Saved Query가 동작하지 않는 변경
  - schema_version 변경 (1.x → 2.0)
```

### 변경 작업 흐름

```
1. trilobase.db에서 변경 작업 수행 (개발 중)
     ↓
2. SCODA 메타데이터 동기화
   - artifact_metadata.version 업데이트
   - schema_descriptions 갱신 (스키마 변경 시)
   - provenance에 새 출처 추가 (새 문헌 반영 시)
     ↓
3. SCODA UI 레이어 동기화 (해당 시)
   - 새 테이블 → ui_display_intent 추가
   - 새 쿼리 필요 → ui_queries 추가
   - 뷰 구조 변경 → ui_manifest 갱신
     ↓
4. 테스트 (pytest)
     ↓
5. 릴리스 (scripts/release.py)
   - SHA-256 재계산
   - 새 아티팩트 생성
   - Git tag
```

### 구체적 시나리오

#### 시나리오 A: 데이터 수정 (genus 이름 오타)

```
변경: UPDATE taxonomic_ranks SET name = 'Correct' WHERE id = 123
반영:
  - artifact_metadata.version: 1.0.0 → 1.0.1
  - 나머지 SCODA 테이블: 변경 없음
```

#### 시나리오 B: 새 테이블 추가 (e.g., specimens)

```
변경: CREATE TABLE specimens (...)
반영:
  - artifact_metadata.version: 1.0.0 → 1.1.0
  - artifact_metadata.schema_version: 1.0 → 1.1
  - schema_descriptions: specimens 테이블/컬럼 설명 추가
  - ui_display_intent: specimens entity 추가 (예: 'table')
  - ui_queries: specimens 관련 쿼리 등록
  - ui_manifest: specimens 뷰 정의 추가
```

#### 시나리오 C: 기존 테이블 구조 변경

```
변경: taxonomic_ranks 컬럼 이름 변경, 또는 테이블 분리
반영:
  - artifact_metadata.version: 1.0.0 → 2.0.0 (breaking!)
  - artifact_metadata.schema_version: 1.0 → 2.0
  - schema_descriptions: 전면 갱신
  - ui_queries: 영향받는 쿼리 SQL 수정
  - ui_manifest: 영향받는 뷰 정의 갱신
  - provenance: 변경 사유 기록
```

#### 시나리오 D: 새 문헌 소스 반영

```
변경: 새 논문 기반으로 taxonomy 업데이트
반영:
  - artifact_metadata.version: 1.1.0 → 1.2.0
  - provenance: 새 출처 추가
    INSERT INTO provenance VALUES (..., 'supplementary',
      'Smith (2026) Revision of ...', ...);
  - 영향받는 taxa에 notes 업데이트
```

### Migration 스크립트 패턴

스키마 변경 시 마이그레이션 스크립트를 `scripts/migrations/` 에 보관:

```
scripts/migrations/
├── 001_add_scoda_tables.py          # Phase 13-15
├── 002_add_specimens_table.py       # 향후 예시
└── 003_rename_temporal_code.py      # 향후 예시
```

각 스크립트는:
1. 현재 `schema_version` 확인
2. 해당 버전에 맞는 변경 실행
3. `schema_version` 업데이트
4. `schema_descriptions` 갱신
5. 영향받는 SCODA UI 레이어 갱신

```python
# 스크립트 패턴 예시
def migrate(db_path):
    conn = sqlite3.connect(db_path)
    current = conn.execute(
        "SELECT value FROM artifact_metadata WHERE key='schema_version'"
    ).fetchone()[0]

    if current >= '1.1':
        print("Already migrated")
        return

    # 스키마 변경
    conn.execute("ALTER TABLE ...")

    # SCODA 메타데이터 갱신
    conn.execute("UPDATE artifact_metadata SET value='1.1' WHERE key='schema_version'")
    conn.execute("INSERT INTO schema_descriptions ...")

    conn.commit()
```

### 핵심 원칙

1. **DB 변경 = 새 버전**. 조용한 변경은 없다.
2. **스키마 변경 시 SCODA UI 레이어도 함께 갱신**. Saved Query가 깨지면 안 된다.
3. **이전 버전은 보존**. 릴리스된 아티팩트는 수정하지 않는다.
4. **Migration 스크립트로 추적 가능하게**. 어떤 변경이 언제 왜 일어났는지 기록.
