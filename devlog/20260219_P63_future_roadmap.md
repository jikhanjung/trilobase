# P63: Trilobase 향후 작업 로드맵

**작성일:** 2026-02-19
**선행 문서:** P45 (초기 로드맵), P56 (Q1 로드맵), P62 (프로젝트 분리)

---

## 현재 상태 요약

| 항목 | 상태 |
|------|------|
| scoda-engine 분리 | ✅ 별도 repo (`/mnt/d/projects/scoda-engine`) |
| DB/dist 디렉토리 정리 | ✅ `db/` (canonical), `dist/` (산출물) |
| Generic Viewer (범용 뷰어) | ✅ manifest-driven, auto-discovery |
| Manifest Validator | ✅ `scripts/validate_manifest.py` |
| .scoda 패키지 | ✅ trilobase.scoda + paleocore.scoda |
| UID 커버리지 | ✅ 7개 테이블 10,384건 100% |
| Taxonomic Opinions PoC (B-1) | ✅ Eurekiidae 시범 |
| 테스트 | ✅ trilobase 66개 / scoda-engine 191개 |

---

## Trilobase 작업

### T-1. Uncertain Family Opinions 확장 (B-2)

**우선순위:** 높음 (다음 작업)
**선행:** B-1 완료 ✅

"Uncertain" Order 소속 56개 Family에 대해 문헌 기반 taxonomic opinion 입력.

**작업:**
- 56개 Family × 1~3개 opinion = 약 100건 입력
- 입력 스크립트 작성 (bibliography 매칭 자동화)
- "Uncertain" → 실제 Order 재배치 가능한 건 `is_accepted` 전환
- 통계 대시보드: opinion 커버리지 표시

**규모:** 중규모 (스크립트 + 데이터 입력)

---

### T-2. Assertion-Centric 모델 검토 (B-3)

**우선순위:** 낮음 (장기, 조건부)
**선행:** T-1 완료
**설계 문서:** `devlog/archive/20260216_P53_assertion_centric_model.md`

`parent_id`를 assertions(opinions)에서 완전히 파생하는 모델로 전환 가능성 검토.
복수 분류 체계가 실제로 필요한 사례가 충분히 축적된 후 진행.

---

### T-3. 미해결 데이터 항목

**우선순위:** 낮음 (데이터 품질 한계)

| 항목 | 건수 | 비고 |
|------|------|------|
| Synonym 미연결 | 4건 | 원본에 senior taxa 없음 |
| parent_id NULL Genus | 342건 | family가 NULL인 무효 taxa (정상) |

---

## scoda-engine 작업

### S-1. conftest.py Generic Fixture 전환

**우선순위:** 중간
**선행:** 분리 완료 ✅

현재 scoda-engine 테스트의 conftest.py가 trilobase 테마(taxonomic_ranks, genus 등) 사용 중.
SCODA 메커니즘 테스트에 도메인 독립적인 generic fixture로 교체.

**작업:**
- 테스트 데이터를 범용 스키마로 교체 (예: items, categories)
- manifest도 범용 테마로 변경
- 기존 122개 runtime + 16개 MCP 테스트 유지

---

### S-2. PyPI 배포

**우선순위:** 중간
**선행:** S-1 권장 (필수는 아님)

`scoda-engine` 패키지를 PyPI에 배포하여 `pip install scoda-engine`으로 설치 가능하게 함.

**작업:**
- pyproject.toml 메타데이터 보강 (license, author, classifiers, URLs)
- README.md PyPI용 정리
- `python -m build` + `twine upload`
- trilobase requirements.txt를 PyPI 참조로 변경

---

### S-3. validate_manifest.py 중복 제거

**우선순위:** 낮음
**선행:** S-2 (PyPI 배포 후)

현재 `validate_manifest.py`가 trilobase와 scoda-engine 양쪽에 존재.
scoda-engine 패키지에서 import하도록 trilobase 측 중복 제거.

---

### S-4. SCODA 백오피스 (C-2)

**우선순위:** 장기 (별도 프로젝트)

.scoda 패키지를 관리/패키징하는 웹 기반 도구.

**범위:**
- manifest 시각적 편집
- 쿼리 검증
- 패키지 빌드 (원클릭 .scoda 생성)
- UID 참조 검증
- dependency 관리

별도 프로젝트로 분리 가능. 현 단계에서는 구상만 존재.

---

## 우선순위 정리

```
Trilobase
  T-1. Uncertain Family Opinions 확장  [높음, 다음 작업]
    └── T-2. Assertion-Centric 검토    [장기, 조건부]

scoda-engine
  S-1. conftest Generic Fixture        [중간]
  S-2. PyPI 배포                       [중간]
    └── S-3. validate_manifest 중복 제거 [낮음]

장기
  S-4. SCODA 백오피스                   [별도 프로젝트]
```

## 권장 착수 순서

| 순서 | 항목 | 리포 | 규모 |
|------|------|------|------|
| 1 | T-1. Uncertain Family Opinions | trilobase | 중 |
| 2 | S-1. conftest Generic Fixture | scoda-engine | 소 |
| 3 | S-2. PyPI 배포 | scoda-engine | 소 |
| 4 | S-3. validate_manifest 중복 제거 | trilobase | 소 |
| 5 | T-2. Assertion-Centric 검토 | trilobase | 대 (조건부) |
| 6 | S-4. SCODA 백오피스 | 신규 | 대 |
