# Trilobase Release Guide

이 문서는 Trilobase의 **canonical DB 수정 → 릴리스 → 배포** 전체 프로세스를 설명합니다.

SCODA(Self-Contained Data Artifact) 원칙에 따라 각 릴리스는 **불변(immutable)**이며, 버전 번호로 식별됩니다.

---

## 목차

1. [버전 번호 규칙](#버전-번호-규칙)
2. [릴리스 절차](#릴리스-절차)
3. [배포 절차](#배포-절차)
4. [Overlay DB 호환성](#overlay-db-호환성)
5. [검증 및 테스트](#검증-및-테스트)
6. [주의사항](#주의사항)

---

## 버전 번호 규칙

Trilobase는 **Semantic Versioning** 방식을 따릅니다: `MAJOR.MINOR.PATCH`

### 버전 증가 기준

| 유형 | 버전 예시 | 변경 내용 | 하위 호환성 |
|------|----------|---------|----------|
| **PATCH** | 1.0.0 → 1.0.1 | 데이터 오류 수정, 타이포 수정 | ✅ 유지 |
| **MINOR** | 1.0.0 → 1.1.0 | 데이터 추가, 새 테이블 추가 | ✅ 유지 |
| **MAJOR** | 1.0.0 → 2.0.0 | 스키마 변경, 테이블 삭제, API breaking | ❌ 깨짐 |

### 예시

- **1.0.1**: Genus 5개의 author 오타 수정
- **1.1.0**: 새로운 지층(formation) 100개 추가
- **2.0.0**: `taxonomic_ranks` 테이블 구조 변경

---

## 릴리스 절차

Canonical DB를 수정한 후 새 릴리스를 생성하는 전체 절차입니다.

### Step 1: 데이터 수정

```bash
# 예: 새 Genus 추가
python scripts/normalize_database.py

# 또는 직접 SQL 수정
python3 -c "
import sqlite3
conn = sqlite3.connect('trilobase.db')
cursor = conn.cursor()
# ... SQL 실행 ...
conn.commit()
conn.close()
"
```

### Step 2: 테스트 실행

```bash
# 모든 테스트 통과 확인
pytest test_app.py -v

# 결과: 101 passed
```

### Step 3: 버전 번호 업데이트

```bash
# artifact_metadata 테이블의 version 업데이트
python3 -c "
import sqlite3
conn = sqlite3.connect('trilobase.db')
cursor = conn.cursor()

# 버전 업데이트
cursor.execute(\"UPDATE artifact_metadata SET value = '1.1.0' WHERE key = 'version'\")

# created_at 업데이트 (선택사항)
from datetime import date
cursor.execute(\"UPDATE artifact_metadata SET value = ? WHERE key = 'created_at'\", (str(date.today()),))

conn.commit()
conn.close()
print('✓ Version updated to 1.1.0')
"
```

### Step 4: 릴리스 패키징

```bash
# 1. Dry-run으로 사전 확인
python scripts/release.py --dry-run

# 출력 확인:
# - Version: 1.1.0
# - Release dir: releases/trilobase-v1.1.0
# - "Release directory does not exist — OK to proceed." 확인

# 2. 실제 릴리스 생성
python scripts/release.py
```

**생성되는 파일:**
```
releases/trilobase-v1.1.0/
├── trilobase.db         # Read-only 복사본 (0444 권한)
├── metadata.json        # 메타데이터 + 출처 + 통계
├── checksums.sha256     # SHA-256 해시
└── README.md            # 사용 안내
```

**자동으로 수행되는 작업:**
- SHA-256 해시 계산
- 소스 DB(`trilobase.db`)에 `sha256` 키 자동 추가
- 통계 정보 수집 및 `metadata.json` 생성
- 릴리스 디렉토리 read-only 설정

### Step 5: Git 커밋 및 태깅

```bash
# 1. 변경사항 커밋
git add trilobase.db
git commit -m "chore: Release v1.1.0

- [수정 내용 요약]
- Added 100 new formations
- Fixed 5 author name typos
- Updated artifact_metadata version to 1.1.0"

# 2. Git 태그 생성
git tag -a v1.1.0 -m "Release v1.1.0"

# 3. 푸시
git push origin feature/scoda-implementation  # 또는 main
git push origin v1.1.0
```

---

## 배포 절차

릴리스된 DB를 독립 실행형 앱으로 패키징하여 배포합니다.

### Step 1: Overlay DB 버전 업데이트

**Minor/Patch 버전 (하위 호환):**
```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('trilobase_overlay.db')
cursor = conn.cursor()
cursor.execute(\"UPDATE overlay_metadata SET value = '1.1.0' WHERE key = 'canonical_version'\")
conn.commit()
conn.close()
print('✓ Overlay DB version updated to 1.1.0')
"
```

**Major 버전 (breaking change):**
```bash
# 1. 기존 overlay DB 백업
mv trilobase_overlay.db trilobase_overlay_v1.db.backup

# 2. 새 overlay DB 생성
python scripts/init_overlay_db.py trilobase_overlay.db 2.0.0

# 3. 사용자 주석 마이그레이션 (필요 시)
# entity_name 컬럼 덕분에 대부분 자동 매칭 가능
# 필요 시 scripts/migrate_annotations.py 작성
```

### Step 2: PyInstaller 빌드

```bash
# 독립 실행형 앱 빌드 (Windows/Linux)
python scripts/build.py

# 생성 결과:
# - dist/trilobase.exe (Windows, ~14MB)
# - dist/trilobase (Linux, ~13MB)
```

**번들링되는 파일:**
- `trilobase.db` (canonical DB, read-only)
- `app.py`, `templates/`, `static/`
- `scripts/gui.py`
- Flask 및 의존성

### Step 3: 배포 파일 준비

```bash
# 1. 릴리스 디렉토리에 실행 파일 복사
cp dist/trilobase.exe releases/trilobase-v1.1.0/
cp dist/trilobase releases/trilobase-v1.1.0/

# 2. ZIP 압축 (선택사항)
cd releases
zip -r trilobase-v1.1.0-windows.zip trilobase-v1.1.0/trilobase.exe trilobase-v1.1.0/README.md
tar czf trilobase-v1.1.0-linux.tar.gz trilobase-v1.1.0/trilobase trilobase-v1.1.0/README.md
```

### Step 4: GitHub Release 생성

```bash
# GitHub CLI 사용 (선택사항)
gh release create v1.1.0 \
  --title "Trilobase v1.1.0" \
  --notes "Release notes here" \
  releases/trilobase-v1.1.0-windows.zip \
  releases/trilobase-v1.1.0-linux.tar.gz
```

---

## Overlay DB 호환성

Overlay DB는 사용자의 주석(annotations)을 저장하며, canonical DB 버전과 연동됩니다.

### 호환성 매트릭스

| Canonical 버전 변경 | Overlay DB 처리 | 사용자 주석 보존 |
|------------------|--------------|--------------|
| PATCH (1.0.0 → 1.0.1) | 버전만 업데이트 | ✅ 전체 보존 |
| MINOR (1.0.0 → 1.1.0) | 버전만 업데이트 | ✅ 전체 보존 |
| MAJOR (1.0.0 → 2.0.0) | 재생성 + 마이그레이션 | ⚠️ entity_name 기반 매칭 |

### entity_name의 역할

```sql
-- user_annotations 테이블 구조
CREATE TABLE user_annotations (
    id INTEGER PRIMARY KEY,
    entity_type TEXT,        -- 'genus', 'family', etc.
    entity_id INTEGER,       -- canonical DB의 ID (버전별로 변경 가능)
    entity_name TEXT,        -- 'Paradoxides' 등 (불변)
    annotation_type TEXT,
    content TEXT,
    created_at TEXT
);
```

**핵심:**
- `entity_id`는 canonical DB 버전마다 달라질 수 있음
- `entity_name`은 불변이므로 Major 버전 업그레이드 시 매칭 가능
- 예: "Paradoxides"라는 genus에 대한 주석은 ID가 바뀌어도 name으로 찾아 연결

### 마이그레이션 예시 (Major 버전)

```python
# scripts/migrate_annotations.py (예시 — 필요 시 작성)
import sqlite3

old_overlay = sqlite3.connect('trilobase_overlay_v1.db.backup')
new_overlay = sqlite3.connect('trilobase_overlay.db')
canonical = sqlite3.connect('trilobase.db')

# entity_name으로 새 entity_id 찾아서 주석 복사
old_cursor = old_overlay.cursor()
old_cursor.execute("SELECT * FROM user_annotations")

for row in old_cursor.fetchall():
    entity_type, entity_name = row[1], row[3]

    # 새 canonical DB에서 entity_id 찾기
    canonical_cursor = canonical.cursor()
    canonical_cursor.execute(
        "SELECT id FROM taxonomic_ranks WHERE rank = ? AND name = ?",
        (entity_type.capitalize(), entity_name)
    )
    new_id_row = canonical_cursor.fetchone()

    if new_id_row:
        new_id = new_id_row[0]
        new_overlay.execute(
            "INSERT INTO user_annotations (entity_type, entity_id, entity_name, ...) VALUES (?, ?, ?, ...)",
            (entity_type, new_id, entity_name, ...)
        )

new_overlay.commit()
```

---

## 검증 및 테스트

### 릴리스 무결성 검증

```bash
cd releases/trilobase-v1.1.0

# SHA-256 체크섬 확인
sha256sum --check checksums.sha256
# ✓ trilobase.db: OK

# metadata.json 확인
cat metadata.json | jq '.version, .sha256'
# "1.1.0"
# "abc123def456..."
```

### 실행 파일 테스트

```bash
# 1. GUI 실행
./dist/trilobase

# 2. 확인 사항:
# - GUI 로그에 "Canonical DB: trilobase.db" 표시
# - "Start Server" 클릭 → 브라우저 자동 오픈
# - http://localhost:8080 접속 확인
# - Tree View / Genera Table 정상 표시
# - 새로 추가된 데이터 확인
```

### API 테스트

```bash
# 서버 실행 후
curl http://localhost:8080/api/metadata | jq '.version, .sha256'
# "1.1.0"
# "abc123def456..."

# 통계 확인
curl http://localhost:8080/api/metadata | jq '.statistics'
```

---

## 주의사항

### ⚠️ 불변성 원칙

- **같은 버전 번호로 릴리스 재생성 불가**
  ```bash
  python scripts/release.py
  # Error: Release directory already exists: releases/trilobase-v1.1.0
  # SCODA immutability principle: cannot overwrite an existing release.
  ```
- 실수로 잘못된 릴리스 생성 시:
  1. 릴리스 디렉토리 삭제 (`rm -rf releases/trilobase-v1.1.0`)
  2. 버전 번호 증가 (1.1.0 → 1.1.1)
  3. 재릴리스

### ⚠️ 소스 DB 변경

- `scripts/release.py`는 **소스 DB(`trilobase.db`)에 `sha256` 키를 추가**합니다
- 릴리스 후 소스 DB를 커밋하는 것을 잊지 마세요

### ⚠️ Overlay DB 동기화

- 독립 실행형 앱 배포 시 overlay DB 버전 불일치 주의
- 사용자가 이전 버전의 overlay DB를 사용하면:
  - Minor/Patch: 대부분 정상 작동
  - Major: entity_id 불일치로 주석 미표시 가능

### ⚠️ PyInstaller 캐시

```bash
# 빌드 에러 발생 시 캐시 삭제
rm -rf build/ dist/ __pycache__
python scripts/build.py
```

---

## 빠른 참조 (Quick Reference)

### 데이터 수정 → 릴리스 (5단계)

```bash
# 1. 데이터 수정 + 테스트
pytest test_app.py

# 2. 버전 업데이트
python3 -c "
import sqlite3
conn = sqlite3.connect('trilobase.db')
conn.execute(\"UPDATE artifact_metadata SET value = '1.1.0' WHERE key = 'version'\")
conn.commit()
"

# 3. 릴리스 생성
python scripts/release.py

# 4. Git 커밋 + 태그
git add trilobase.db
git commit -m "chore: Release v1.1.0"
git tag -a v1.1.0 -m "Release v1.1.0"
git push origin main v1.1.0

# 5. 실행 파일 빌드
python scripts/build.py
```

---

## 관련 문서

- [HANDOVER.md](./HANDOVER.md) — 프로젝트 현황 및 인수인계
- [SCODA_CONCEPT.md](./SCODA_CONCEPT.md) — SCODA 개념 설명
- [../CLAUDE.md](../CLAUDE.md) — Claude Code 작업 규약
- [../devlog/20260207_P08_release_mechanism.md](../devlog/20260207_P08_release_mechanism.md) — 릴리스 메커니즘 설계 문서

---

**마지막 업데이트:** 2026-02-08
