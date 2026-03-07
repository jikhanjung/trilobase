# 110: Assertion DB v0.1.5 — 프로필 체인 개편 및 데이터 정제

**날짜:** 2026-03-07
**DB:** trilobase-assertion-0.1.5.db

## 개요

Treatise 1959/2004 프로필의 edge cache 구성 방식을 개편하고,
taxonomy JSON의 genus 중복 및 placeholder 이름 문제를 해결했다.

## 변경 내용

### 1. 프로필 체인 개편

**Before:**
- default (JA2002): 5,083 edges
- treatise2004: default 복사 + Agnostida/Redlichiida 교체 → 5,138 edges
- treatise1959: default 복사 + 전체 교체 → 5,323 edges

**After:**
- default (JA2002): 5,083 edges (변경 없음)
- treatise1959: **standalone** (default 복사 없음, 1959 assertion만) → 1,324 edges
- treatise2004: **treatise1959 기반** (1959 복사 + Agnostida/Redlichiida 교체) → 1,667 edges

### 2. Taxonomy JSON genus 중복 해소 (`build_treatise1959_tree.py`)

OCR 페이지 경계 오류로 32개 genus가 tree에서 두 곳에 중복 배치되어 있었다.

**3가지 패턴:**
- Dinesidae vs Ptychopariidae (27건): page 250 Dinesidae header 이후 page 253 Ptychopariidae genera가 잘못 배정
- Dolerolenidae vs Olenidae (3건): page 225 경계 오류
- Pterygometopidae vs Chasmopinae (2건): page 509/512 경계 오류

**PDF 확인 결과:** 모두 OCR family header 누락/오매칭이 원인. 올바른 배치는 Ptychopariidae, Dolerolenidae(Redlichiida), Chasmopinae.

**수정:**
- `integrate_genera_into_tree()`에 global dedup set 추가 — genus는 tree에서 한 번만 배치
- Subfamily 매칭을 family 매칭보다 먼저 처리 (더 구체적인 위치 우선)
- 이전 실행 잔여물 제거 로직 추가 (strip genera + revert placeholder rename)

**결과:** 1,048 → 1,014 genera (중복 34건 제거)

### 3. Placeholder 이름 고유화

"Subfamily Uncertain", "Family Uncertain" 같은 placeholder가 서로 다른 부모 아래 반복되어
같은 taxon으로 매칭되는 문제 해결.

**수정:** 부모 이름 포함 → `Subfamily Uncertain (Protolenidae)` 등 (15건 rename)

### 4. Assertion 중복 방지 (`import_treatise1959.py`)

tree에서 같은 taxon이 여러 경로로 방문되면 같은 child_id에 복수 PLACED_IN assertion이 생기는 문제.

**수정:** `asserted_children` set으로 이미 assertion이 있는 child_id skip (8건)

### 5. 빌드 파이프라인 정비 (`create_scoda.py`)

- 빌드 순서: treatise1959 → treatise2004 (2004가 1959을 base로 사용하므로)
- Treatise 1959 import를 assertion .scoda 빌드에 포함

## 수정 파일

| 파일 | 변경 내용 |
|------|----------|
| `scripts/build_treatise1959_tree.py` | global genus dedup, placeholder rename, strip previous run |
| `scripts/import_treatise1959.py` | standalone edge cache, assertion dedup |
| `scripts/import_treatise.py` | base profile: default → treatise1959 |
| `scripts/create_scoda.py` | 빌드 순서 1959→2004, 1959 import 포함 |
| `scripts/create_assertion_db.py` | version bump 0.1.4 → 0.1.5 |
| `data/treatise_1959_taxonomy.json` | 중복 genus 제거, placeholder 고유화 |

## 최종 프로필 현황

| ID | Name | Base | Edges | 설명 |
|----|------|------|-------|------|
| 1 | Jell & Adrain 2002 + Adrain 2011 | — | 5,083 | 기본 프로필 |
| 2 | treatise1959 | standalone | 1,324 | 1959 Treatise 전체 (genus 1,001) |
| 3 | treatise2004 | treatise1959 | 1,667 | 1959 + Agnostida/Redlichiida 2004 교체 |
