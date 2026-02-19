# Phase 20: Overlay DB 분리 완료

**날짜:** 2026-02-08

## 요약

Canonical DB와 Overlay DB를 완전 분리하여 PyInstaller onefile 빌드 시 read-only canonical DB + read/write overlay DB 구조 구현. 사용자 주석이 실행 파일 외부에 저장되어 영구 보존 가능.

## 배경

**문제:**
- PyInstaller onefile 빌드 시 `trilobase.db`가 임시 폴더(`sys._MEIPASS`)에 압축 해제됨
- 임시 폴더는 read-only → `user_annotations` 저장 불가
- 앱 재시작 시 임시 폴더 초기화 → 주석 손실

**해결책 (Option 1):**
- Canonical DB: 실행 파일 내부 (read-only, 불변)
- Overlay DB: 실행 파일 외부 (read/write, 사용자 데이터)
- SQLite ATTACH로 두 DB를 하나의 연결에서 사용

## 구현 내용

### 1. `scripts/init_overlay_db.py` (신규)

Overlay DB 초기화 스크립트:

```python
def create_overlay_db(db_path, canonical_version='1.0.0'):
    """Create overlay database with metadata and user_annotations table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # overlay_metadata: canonical DB 버전 추적
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS overlay_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    cursor.execute(
        "INSERT OR REPLACE INTO overlay_metadata (key, value) VALUES ('canonical_version', ?)",
        (canonical_version,)
    )

    # user_annotations: Phase 17에서 이동
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_annotations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT NOT NULL,
            entity_id INTEGER NOT NULL,
            entity_name TEXT,               -- 릴리스 간 매칭용
            annotation_type TEXT NOT NULL,
            content TEXT NOT NULL,
            author TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
```

**핵심:**
- `overlay_metadata.canonical_version`: 릴리스 간 마이그레이션 추적
- `entity_name` 컬럼: ID가 변경되어도 entity 매칭 가능

### 2. `app.py` 수정 — 이중 DB 연결

**DB 경로 설정:**

```python
import os
import sys

# Determine DB paths based on execution mode
if getattr(sys, 'frozen', False):
    # Running as PyInstaller bundle
    CANONICAL_DB = os.path.join(sys._MEIPASS, 'trilobase.db')
    OVERLAY_DB = os.path.join(os.path.dirname(sys.executable), 'trilobase_overlay.db')
else:
    # Running as normal Python script (development)
    base_dir = os.path.dirname(__file__)
    CANONICAL_DB = os.path.join(base_dir, 'trilobase.db')
    OVERLAY_DB = os.path.join(base_dir, 'trilobase_overlay.db')
```

**연결 함수:**

```python
def _ensure_overlay_db():
    """Create overlay DB if not exists."""
    if os.path.exists(OVERLAY_DB):
        return

    from scripts.init_overlay_db import create_overlay_db

    # Get canonical version
    conn = sqlite3.connect(CANONICAL_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM artifact_metadata WHERE key = 'version'")
    row = cursor.fetchone()
    version = row[0] if row else '1.0.0'
    conn.close()

    create_overlay_db(OVERLAY_DB, version)


def get_db():
    """Get database connection with overlay attached."""
    _ensure_overlay_db()

    conn = sqlite3.connect(CANONICAL_DB)
    conn.row_factory = sqlite3.Row

    # Attach overlay database
    conn.execute(f"ATTACH DATABASE '{OVERLAY_DB}' AS overlay")

    return conn
```

### 3. API 수정 — `overlay.` 접두사

**GET /api/annotations/<entity_type>/<int:entity_id>:**

```python
cursor.execute("""
    SELECT id, entity_type, entity_id, entity_name, annotation_type, content, author, created_at
    FROM overlay.user_annotations
    WHERE entity_type = ? AND entity_id = ?
    ORDER BY created_at DESC, id DESC
""", (entity_type, entity_id))
```

**POST /api/annotations:**

```python
# Get entity_name for future-proof matching
cursor.execute("SELECT name FROM taxonomic_ranks WHERE id = ?", (entity_id,))
row = cursor.fetchone()
entity_name = row['name'] if row else None

cursor.execute("""
    INSERT INTO overlay.user_annotations
    (entity_type, entity_id, entity_name, annotation_type, content, author)
    VALUES (?, ?, ?, ?, ?, ?)
""", (entity_type, entity_id, entity_name, annotation_type, content, author))
```

**DELETE /api/annotations/<int:annotation_id>:**

```python
cursor.execute("DELETE FROM overlay.user_annotations WHERE id = ?", (annotation_id,))
```

모든 annotation 쿼리에 `overlay.` 접두사 추가하여 overlay DB 참조.

### 4. `scripts/gui.py` 수정 — Overlay DB 표시

GUI에 Canonical + Overlay DB 정보 표시:

```python
# Determine DB paths
if getattr(sys, 'frozen', False):
    # Canonical DB: inside bundle
    self.canonical_db_path = os.path.join(sys._MEIPASS, 'trilobase.db')
    # Overlay DB: next to executable
    self.overlay_db_path = os.path.join(os.path.dirname(sys.executable), 'trilobase_overlay.db')
else:
    # Development mode
    self.canonical_db_path = os.path.join(self.base_path, 'trilobase.db')
    self.overlay_db_path = os.path.join(self.base_path, 'trilobase_overlay.db')

# GUI Info Frame
overlay_row = tk.Frame(info_frame)
overlay_row.pack(fill="x", pady=3)
tk.Label(overlay_row, text="Overlay:", width=12, anchor="w").pack(side="left")
overlay_name = os.path.basename(self.overlay_db_path)
overlay_exists = os.path.exists(self.overlay_db_path)
overlay_text = overlay_name if overlay_exists else f"{overlay_name} (auto-created)"
overlay_color = "green" if overlay_exists else "gray"
self.overlay_label = tk.Label(overlay_row, text=overlay_text, anchor="w", fg=overlay_color)
```

**GUI 표시:**

```
Canonical: trilobase.db (파란색)
Overlay:   trilobase_overlay.db (auto-created) (회색)
           → 첫 실행 후 초록색
```

### 5. `test_app.py` 수정 — 이중 DB Fixture

**test_db fixture 변경:**

```python
@pytest.fixture
def test_db(tmp_path):
    """Create temporary test databases (canonical + overlay) with sample data."""
    canonical_db_path = str(tmp_path / "test_trilobase.db")
    overlay_db_path = str(tmp_path / "test_overlay.db")

    # Create canonical DB (without user_annotations)
    conn = sqlite3.connect(canonical_db_path)
    # ... (create tables, NO user_annotations)
    conn.close()

    # Create overlay DB using init_overlay_db script
    from init_overlay_db import create_overlay_db
    create_overlay_db(overlay_db_path, canonical_version='1.0.0')

    return canonical_db_path, overlay_db_path
```

**client fixture 변경:**

```python
@pytest.fixture
def client(test_db, monkeypatch):
    """Create Flask test client with test databases (canonical + overlay)."""
    canonical_db_path, overlay_db_path = test_db
    import app as app_module
    monkeypatch.setattr(app_module, 'CANONICAL_DB', canonical_db_path)
    monkeypatch.setattr(app_module, 'OVERLAY_DB', overlay_db_path)
    # ...
```

**Release tests 수정:**

```python
def test_get_statistics(self, test_db):
    canonical_db, _ = test_db  # Unpack tuple
    stats = get_statistics(canonical_db)
    # ...
```

모든 release 관련 테스트에서 canonical DB만 사용 (overlay는 로컬 데이터이므로 릴리스 대상 아님).

### 6. `scripts/release.py` 수정 — Annotation 통계 제거

```python
def get_statistics(db_path):
    # ...
    cursor.execute("SELECT COUNT(*) as count FROM countries")
    stats['countries'] = cursor.fetchone()['count']

    # Note: user_annotations are in overlay DB (Phase 20), not canonical DB
    # Annotations are local overlay data and not included in canonical releases

    conn.close()
    return stats
```

**이유:**
- Annotations는 overlay DB에 있음 (canonical DB에 없음)
- Overlay는 로컬 사용자 데이터 → 릴리스 통계에 포함 안 함

## 배포 구조

### 개발 모드 (Python 스크립트)

```
trilobase/
├── trilobase.db              # Canonical DB
├── trilobase_overlay.db      # Overlay DB (첫 실행 시 자동 생성)
├── app.py
└── ...
```

### 배포 모드 (PyInstaller 실행 파일)

```
releases/trilobase-v1.0.0/
└── trilobase.exe                    # 실행 파일 (canonical DB 포함)

실행 시:
1. Canonical DB 압축 해제 → /tmp/.../trilobase.db (read-only)
2. Overlay DB 생성 → ./trilobase_overlay.db (read/write)
3. SQLite ATTACH로 두 DB 연결
```

**사용자 파일 구조:**

```
C:\Users\User\Desktop\trilobase\
├── trilobase.exe                # 배포 받은 실행 파일
└── trilobase_overlay.db         # 첫 실행 후 자동 생성 (28KB)
```

## 테스트 결과

```bash
$ python -m pytest test_app.py -v
============================= 101 passed in 35.70s =========================
```

**101개 테스트 모두 통과:**
- Flask API 테스트 (79개) ✓
- Release 메커니즘 (12개) ✓
- Annotations (10개) ✓

**Overlay DB 생성 검증:**

```bash
$ python -c "from app import get_db; conn = get_db(); ..."
✓ Overlay DB created successfully

$ ls -lh trilobase_overlay.db
-rw-r--r-- 1 user user 28K Feb  8 11:31 trilobase_overlay.db

Tables: overlay_metadata, user_annotations
Metadata:
  canonical_version: 1.0.0
  created_at: 2026-02-08 02:31:46
```

## 향후: 릴리스 간 Overlay 마이그레이션

v1.0.0 → v1.1.0 업그레이드 시:

```python
# overlay_metadata에서 버전 확인
cursor.execute("SELECT value FROM overlay.overlay_metadata WHERE key = 'canonical_version'")
overlay_version = cursor.fetchone()[0]  # '1.0.0'

# 새 canonical 버전
cursor.execute("SELECT value FROM artifact_metadata WHERE key = 'version'")
canonical_version = cursor.fetchone()[0]  # '1.1.0'

if overlay_version != canonical_version:
    # ID 매핑: entity_name으로 매칭
    cursor.execute("""
        SELECT id, name FROM taxonomic_ranks WHERE rank = 'Genus'
    """)
    name_to_new_id = {row['name']: row['id'] for row in cursor.fetchall()}

    # Overlay annotations의 entity_id 갱신
    cursor.execute("SELECT id, entity_name FROM overlay.user_annotations")
    for ann_id, entity_name in cursor.fetchall():
        new_id = name_to_new_id.get(entity_name)
        if new_id:
            cursor.execute(
                "UPDATE overlay.user_annotations SET entity_id = ? WHERE id = ?",
                (new_id, ann_id)
            )

    # 버전 갱신
    cursor.execute(
        "UPDATE overlay.overlay_metadata SET value = ? WHERE key = 'canonical_version'",
        (canonical_version,)
    )
```

## 수정 파일 요약

| 파일 | 변경 | 신규/수정 |
|------|------|----------|
| `scripts/init_overlay_db.py` | Overlay DB 초기화 스크립트 | 신규 |
| `app.py` | 이중 DB 연결 로직 (ATTACH) | 수정 |
| Annotation API 엔드포인트 | `overlay.user_annotations` 참조 | 수정 |
| `scripts/gui.py` | Overlay DB 경로 표시 | 수정 |
| `test_app.py` | 이중 DB fixture | 수정 |
| `scripts/release.py` | Annotation 통계 제거 | 수정 |

## 다음 단계

1. **Windows 빌드 및 테스트**: PyInstaller onefile에서 이중 DB 검증
2. **GUI 개선**: Overlay DB 경로 클릭 시 파일 탐색기 열기
3. **마이그레이션 자동화**: 릴리스 간 overlay 마이그레이션 스크립트
4. **문서화**: 사용자 가이드에 overlay DB 설명 추가

## 완료 상태

- ✅ Canonical/Overlay DB 분리
- ✅ SQLite ATTACH 연결
- ✅ API 엔드포인트 overlay 참조
- ✅ entity_name 저장 (릴리스 간 매칭용)
- ✅ overlay_metadata 버전 추적
- ✅ GUI Overlay 정보 표시
- ✅ 테스트 101개 통과
- ✅ Overlay DB 자동 생성 검증
