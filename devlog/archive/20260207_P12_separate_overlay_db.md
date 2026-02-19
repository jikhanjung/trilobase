# Plan: Overlay DB 분리 (옵션 1)

**날짜:** 2026-02-07
**목표:** Canonical DB와 Local Overlay DB를 완전 분리

## 배경

**문제:**
- 현재 `user_annotations`가 canonical DB 안에 있음
- PyInstaller onefile 빌드 시 DB가 실행 파일 내부 → read-only
- 사용자 주석 저장 불가

**SCODA 원칙:**
- Canonical 데이터는 불변 (immutable)
- 사용자 의견은 별도 레이어

## 구조 설계

### 배포 패키지

```
releases/trilobase-v1.0.0/
├── trilobase.exe              # 실행 파일 (canonical DB 포함)
└── (trilobase_overlay.db)     # 첫 실행 시 자동 생성
```

### DB 구조

**Canonical DB** (실행 파일 내부, read-only):
- `taxonomic_ranks`, `synonyms`, `formations`, `countries`, ...
- `artifact_metadata`, `provenance`, `schema_descriptions`
- `ui_display_intent`, `ui_queries`, `ui_manifest`
- 모든 SCODA 메타데이터

**Overlay DB** (외부 파일, read/write):
- `overlay_metadata` 테이블 (canonical DB 버전 추적)
- `user_annotations` 테이블

### SQLite ATTACH 사용

```python
import sqlite3

# Canonical DB (번들 내부)
canonical_db = os.path.join(sys._MEIPASS, 'trilobase.db')
conn = sqlite3.connect(canonical_db)

# Overlay DB (외부)
overlay_db = os.path.join(os.path.dirname(sys.executable), 'trilobase_overlay.db')
conn.execute(f"ATTACH DATABASE '{overlay_db}' AS overlay")

# 쿼리 예시
conn.execute("SELECT * FROM taxonomic_ranks")           # canonical
conn.execute("SELECT * FROM overlay.user_annotations")  # overlay
```

## 구현 단계

### 1. `scripts/init_overlay_db.py` (신규)

Overlay DB 초기화 스크립트:

```python
#!/usr/bin/env python3
"""
Initialize overlay database for user annotations.

Creates a separate SQLite database for user-editable content.
"""

import sqlite3
import os
import sys


def create_overlay_db(db_path, canonical_version='1.0.0'):
    """Create overlay database with metadata and user_annotations table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # overlay_metadata 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS overlay_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    # Canonical DB 버전 저장
    cursor.execute(
        "INSERT OR REPLACE INTO overlay_metadata (key, value) VALUES ('canonical_version', ?)",
        (canonical_version,)
    )
    cursor.execute(
        "INSERT OR REPLACE INTO overlay_metadata (key, value) VALUES ('created_at', datetime('now'))",
    )

    # user_annotations 테이블 (Phase 17에서 이동)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_annotations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT NOT NULL,
            entity_id INTEGER NOT NULL,
            entity_name TEXT,
            annotation_type TEXT NOT NULL,
            content TEXT NOT NULL,
            author TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_annotations_entity
            ON user_annotations(entity_type, entity_id)
    """)

    conn.commit()
    conn.close()
    print(f"Overlay DB created: {db_path}")


def main():
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = 'trilobase_overlay.db'

    canonical_version = sys.argv[2] if len(sys.argv) > 2 else '1.0.0'

    create_overlay_db(db_path, canonical_version)


if __name__ == '__main__':
    main()
```

### 2. `app.py` 수정 — DB 연결 변경

**현재:**
```python
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn
```

**수정:**
```python
import os
import sys

# DB 경로 결정
if getattr(sys, 'frozen', False):
    # PyInstaller bundle
    CANONICAL_DB = os.path.join(sys._MEIPASS, 'trilobase.db')
    OVERLAY_DB = os.path.join(os.path.dirname(sys.executable), 'trilobase_overlay.db')
else:
    # Development
    CANONICAL_DB = os.path.join(os.path.dirname(__file__), 'trilobase.db')
    OVERLAY_DB = os.path.join(os.path.dirname(__file__), 'trilobase_overlay.db')


def get_db():
    """Get database connection with overlay attached."""
    conn = sqlite3.connect(CANONICAL_DB)
    conn.row_factory = sqlite3.Row

    # Overlay DB가 없으면 생성
    if not os.path.exists(OVERLAY_DB):
        _create_overlay_db()

    # Overlay 연결
    conn.execute(f"ATTACH DATABASE '{OVERLAY_DB}' AS overlay")

    return conn


def _create_overlay_db():
    """Create overlay DB if not exists."""
    from scripts.init_overlay_db import create_overlay_db

    # canonical DB에서 버전 읽기
    conn = sqlite3.connect(CANONICAL_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM artifact_metadata WHERE key = 'version'")
    row = cursor.fetchone()
    version = row[0] if row else '1.0.0'
    conn.close()

    create_overlay_db(OVERLAY_DB, version)
```

### 3. API 수정 — Overlay 테이블 참조

**Annotations API 수정:**

```python
@app.route('/api/annotations/<entity_type>/<int:entity_id>')
def api_get_annotations(entity_type, entity_id):
    conn = get_db()
    cursor = conn.cursor()

    # overlay. 접두사 추가
    cursor.execute("""
        SELECT id, entity_type, entity_id, entity_name, annotation_type, content, author, created_at
        FROM overlay.user_annotations
        WHERE entity_type = ? AND entity_id = ?
        ORDER BY created_at DESC, id DESC
    """, (entity_type, entity_id))

    annotations = cursor.fetchall()
    conn.close()
    # ... (나머지 동일)
```

모든 annotation 관련 쿼리에 `overlay.` 접두사 추가.

### 4. `entity_name` 컬럼 추가

Annotation 생성 시 entity_name도 저장 (R01 문서의 권장사항):

```python
@app.route('/api/annotations', methods=['POST'])
def api_create_annotation():
    data = request.get_json()
    # ...

    # entity_name 조회
    cursor.execute(
        "SELECT name FROM taxonomic_ranks WHERE id = ?",
        (entity_id,)
    )
    row = cursor.fetchone()
    entity_name = row['name'] if row else None

    # 저장 시 entity_name 포함
    cursor.execute("""
        INSERT INTO overlay.user_annotations
        (entity_type, entity_id, entity_name, annotation_type, content, author)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (entity_type, entity_id, entity_name, annotation_type, content, author))
```

### 5. `scripts/gui.py` 수정

Overlay DB 경로 표시:

```python
# GUI에 overlay DB 정보 추가
overlay_row = tk.Frame(info_frame)
overlay_row.pack(fill="x", pady=3)
tk.Label(overlay_row, text="Overlay:", width=12, anchor="w").pack(side="left")
overlay_name = os.path.basename(overlay_db_path)
self.overlay_label = tk.Label(overlay_row, text=overlay_name, anchor="w", fg="green")
self.overlay_label.pack(side="left", fill="x", expand=True)
```

### 6. `test_app.py` 수정

테스트 fixture에서 overlay DB 생성:

```python
@pytest.fixture
def test_db(tmp_path):
    canonical_db = str(tmp_path / "test_trilobase.db")
    overlay_db = str(tmp_path / "test_overlay.db")

    # Canonical DB 생성 (기존 코드)
    conn = sqlite3.connect(canonical_db)
    # ... (테이블 생성)
    conn.close()

    # Overlay DB 생성
    from scripts.init_overlay_db import create_overlay_db
    create_overlay_db(overlay_db, '1.0.0')

    return canonical_db, overlay_db
```

테스트에서 두 DB를 모두 사용하도록 수정.

## 마이그레이션

기존 사용자가 이미 canonical DB 안에 annotations를 가지고 있을 경우:

```python
# scripts/migrate_annotations_to_overlay.py
import sqlite3

canonical_db = 'trilobase.db'
overlay_db = 'trilobase_overlay.db'

# Canonical에서 annotations 읽기
conn_canon = sqlite3.connect(canonical_db)
cursor = conn_canon.cursor()
cursor.execute("SELECT * FROM user_annotations")
annotations = cursor.fetchall()
conn_canon.close()

# Overlay로 이동
conn_overlay = sqlite3.connect(overlay_db)
cursor = conn_overlay.cursor()
for ann in annotations:
    cursor.execute(
        "INSERT INTO user_annotations VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ann
    )
conn_overlay.commit()
conn_overlay.close()

print(f"Migrated {len(annotations)} annotations to overlay DB")
```

## 배포 변경

### `scripts/release.py` 수정

릴리스 패키지에 overlay DB 샘플 포함 (선택):

```python
# Empty overlay DB 생성
overlay_path = os.path.join(release_dir, 'trilobase_overlay.db')
create_overlay_db(overlay_path, version)

# README에 설명 추가
readme += """
## User Annotations

User notes are stored in `trilobase_overlay.db` (auto-created on first run).
This file is separate from the canonical database to preserve data immutability.
"""
```

## 검증

1. **빌드**: `python scripts/build.py`
2. **실행**: `./trilobase.exe`
3. **확인**:
   - Canonical DB: 실행 파일 내부 (read-only)
   - Overlay DB: 실행 파일 옆에 자동 생성
   - Annotation 추가 → overlay DB에 저장
   - 재시작 → annotation 유지

## 수정 파일 요약

| 파일 | 변경 |
|------|------|
| `scripts/init_overlay_db.py` | 신규 (overlay DB 초기화) |
| `app.py` | DB 연결 로직 변경 (ATTACH) |
| API 엔드포인트 | `overlay.user_annotations` 참조 |
| `scripts/gui.py` | Overlay DB 경로 표시 |
| `test_app.py` | Overlay DB fixture 추가 |
| `scripts/migrate_annotations_to_overlay.py` | 신규 (마이그레이션, 선택) |

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
    # ID 매핑 필요 (R01 문서 참조)
    # entity_name으로 매칭
```
