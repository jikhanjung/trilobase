# Review: Local Overlay 내구성 문제와 해결 방향

**날짜:** 2026-02-07
**대상:** Phase 17 Local Overlay (user_annotations)

## 현재 구현의 문제점

### 1. ID 기반 참조의 취약성

현재 `user_annotations`는 `entity_type` + `entity_id`로 대상을 참조한다.

```sql
user_annotations (
    entity_type TEXT,   -- 'genus', 'family' 등
    entity_id INTEGER,  -- taxonomic_ranks.id
    ...
)
```

- FOREIGN KEY 없음, CASCADE DELETE 없음
- 릴리스 간 DB 재생성 시 **ID가 바뀔 수 있음**
- 이름 교정 시 같은 ID인데 다른 이름을 가리키게 됨

### 2. 릴리스-오버레이 분리 문제

SCODA 원칙상 릴리스 DB는 **불변**(read-only)이다. 그런데 현재 구현은 `user_annotations` 테이블이 같은 DB 안에 있다.

- 릴리스 DB에 사용자 데이터가 섞임
- 새 릴리스 수신 시 overlay를 새 DB로 옮기기 어려움
- 릴리스 무결성(SHA-256) 검증과 충돌

### 3. 릴리스 시점 검증 불가

- 릴리스는 서버에서 생성, annotation은 사용자 PC에서 생성
- 서버는 사용자 annotation의 존재를 모름
- 따라서 릴리스 시점에 orphan 검출 등 유효성 검증 불가

## 제안하는 해결 방향

### A. `entity_name` 추가 (매칭 앵커)

annotation 생성 시 ID와 함께 이름도 저장:

```sql
user_annotations (
    ...
    entity_id INTEGER,
    entity_name TEXT,     -- 'Phacops', 'Phacopidae' 등
    ...
)
```

분류학에서 이름은 가장 안정적인 식별자이므로 릴리스 간 매칭의 primary key로 적합.

### B. overlay를 DB 외부 파일(JSON)로 분리

릴리스 DB와 overlay를 물리적으로 분리:

```json
{
  "source_release": "trilobase-v1.0.0",
  "annotations": [
    {
      "entity_type": "genus",
      "entity_id": 100,
      "entity_name": "Phacops",
      "annotation_type": "note",
      "content": "Needs revision",
      "author": "Kim",
      "created_at": "2026-02-07T12:00:00"
    }
  ]
}
```

장점:
- 릴리스 DB 무결성 유지
- overlay 파일만 백업/공유 가능
- 릴리스 간 이동이 자연스러움

### C. 릴리스 간 overlay 마이그레이션 도구

```bash
python scripts/migrate_overlay.py \
    --old-db releases/trilobase-v1.0.0/trilobase.db \
    --new-db releases/trilobase-v1.1.0/trilobase.db \
    --overlay my_annotations.json
```

매칭 우선순위:

1. **entity_name 일치** → 새 ID로 갱신 (가장 흔한 케이스)
2. **entity_name 불일치** → old DB에서 old_id→name 조회 → new DB에서 name→new_id 매칭 시도
3. **매칭 실패** → unresolved 리포트 (사용자 수동 처리)

### D. 릴리스에 ID 매핑 포함

스키마 변경이나 데이터 변경이 있는 릴리스에 **entity별 ID 변경 매핑**을 함께 배포:

```json
// releases/trilobase-v1.1.0/id_mapping.json
{
  "from_version": "1.0.0",
  "to_version": "1.1.0",
  "mappings": {
    "genus": {
      "100": 150,
      "101": 151
    },
    "family": {
      "10": 12
    }
  }
}
```

이렇게 하면 클라이언트 쪽 마이그레이션이 **단순 lookup**으로 끝난다:
- 매핑 파일 로드 → old_id를 new_id로 치환 → 끝
- 이름 기반 fuzzy matching 불필요
- 매핑에 없는 ID = 변경 없음

변경/추가만 있고 삭제가 없다면, 대부분의 릴리스에서 매핑 파일이 비어있거나 아예 불필요할 수 있다.

### E. 첫 릴리스 성숙도 전략

ID 매핑의 필요성을 최소화하는 가장 효과적인 방법은 **첫 릴리스를 충분히 mature한 상태로 내보내는 것**이다.

- 첫 릴리스의 ID 체계가 안정적이면, 이후 릴리스에서 ID 변경이 거의 없음
- 추가(INSERT)만 있으면 기존 ID는 보존됨 → 매핑 불필요
- 이름 교정도 첫 릴리스 전에 최대한 마무리

**따라서:** 1.0.0 릴리스 전에 데이터 품질 검증을 철저히 하고, 이후 릴리스는 데이터 추가 위주로 관리하는 것이 overlay 호환성에 가장 유리하다.

### F. 전제 조건

- **데이터 삭제 없음**: 릴리스 간 레코드가 삭제되지 않는다고 가정
- 변경은 주로: ID 재배정, 이름 교정, 스키마 확장
- ID 변경이 있을 경우 릴리스에 `id_mapping.json` 포함

## 단계적 구현 방안

| 단계 | 내용 | 난이도 | 시점 |
|------|------|--------|------|
| 1 | `entity_name` 컬럼 추가 | 낮음 | 즉시 |
| 2 | overlay export/import (JSON) | 중간 | 첫 릴리스 전 |
| 3 | 릴리스에 `id_mapping.json` 생성 로직 | 중간 | 두 번째 릴리스 시 |
| 4 | 마이그레이션 도구 (매핑 기반 + 이름 fallback) | 중간 | 두 번째 릴리스 시 |
| 5 | 뷰어가 외부 JSON overlay를 런타임 로드 | 높음 | 장기 |

단계 1은 즉시 적용 가능. 단계 2는 첫 릴리스 전까지. 단계 3-5는 실제 두 번째 릴리스가 나올 때.

## 결론

현재 Phase 17 구현은 **프로토타입으로 유효**하지만, 실제 배포 환경에서는:

1. **overlay를 DB 외부 파일로 분리** (릴리스 불변성 보장)
2. **`entity_name` 저장** (어느 방향이든 필수 선행 작업)
3. **릴리스에 ID 매핑 포함** (클라이언트 마이그레이션을 단순 lookup으로 해결)
4. **첫 릴리스를 충분히 성숙시킴** (ID 안정성 확보로 매핑 필요성 자체를 최소화)
