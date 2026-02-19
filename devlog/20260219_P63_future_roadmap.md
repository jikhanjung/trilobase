# P63: Trilobase 향후 작업 로드맵

**작성일:** 2026-02-19
**선행 문서:** P45 (초기 로드맵), P56 (Q1 로드맵), P62 (프로젝트 분리)
**scoda-engine 로드맵:** `/mnt/d/projects/scoda-engine/devlog/20260219_P01_future_roadmap.md`

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
| 테스트 | ✅ trilobase 66개 |

---

## T-1. Uncertain Family Opinions 확장 (B-2)

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

## T-2. Assertion-Centric 모델 검토 (B-3)

**우선순위:** 낮음 (장기, 조건부)
**선행:** T-1 완료
**설계 문서:** `devlog/archive/20260216_P53_assertion_centric_model.md`

`parent_id`를 assertions(opinions)에서 완전히 파생하는 모델로 전환 가능성 검토.
복수 분류 체계가 실제로 필요한 사례가 충분히 축적된 후 진행.

---

## T-3. 미해결 데이터 항목

**우선순위:** 낮음 (데이터 품질 한계)

| 항목 | 건수 | 비고 |
|------|------|------|
| Synonym 미연결 | 4건 | 원본에 senior taxa 없음 |
| parent_id NULL Genus | 342건 | family가 NULL인 무효 taxa (정상) |

---

## 우선순위 정리

```
T-1. Uncertain Family Opinions 확장  [높음, 다음 작업]
  └── T-2. Assertion-Centric 검토    [장기, 조건부]
```
