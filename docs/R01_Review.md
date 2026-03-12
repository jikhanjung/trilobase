# Review: SCODA and Trilobase Paper Draft

**Date**: 2026-03-12
**Reviewer**: Claude (AI-assisted review)

---

## 논문 개요

Assertion-based 분류학 모델, Classification Profiles, SCODA 패키지 프레임워크를 제안하고, Trilobase(삼엽충 속 수준 분류 데이터셋)를 사례로 제시하는 논문.

---

## 1. 구조 및 구성

| 파일 | 상태 | 비고 |
|---|---|---|
| `00_Header` | 완성 | 깔끔함 |
| `01_Abstract` | 완성 | 잘 정리됨 |
| `02_Introduction` | **3개 draft가 병존** | 정리 필요 |
| `03_Limitations` | 완성 | 논리 명확 |
| `04_Assertion-Based` | 완성 | 핵심 개념 |
| `05_Classification_Profiles` | 완성 | 적절한 분량 |
| `06_SCODA` | 완성 | 명확한 설명 |
| `07_Case_Study_Trilobase` | 완성 | 구조적 |
| `08_Discussion` | 완성 | 균형 잡힘 |
| `09_Conclusion` | 완성 (제목에 `# #` 오타) | 마이너 수정 필요 |
| `10_References` | **비어 있음** | 참고문헌 미작성 |
| `99_Figure_Plan 1/2` | 기획 메모 | 한국어 혼용 |

---

## 2. 강점

1. **명확한 핵심 개념**: "taxonomy = assertions, classification = derived views"라는 메시지가 전 섹션에 걸쳐 일관되게 전달됨
2. **논리 흐름이 좋음**: 문제 제기(03) → 해결 모델(04) → 파생 개념(05) → 배포 프레임워크(06) → 사례(07) 순서가 자연스러움
3. **학술 영어의 품질이 높음**: 문장이 깔끔하고 passive voice 사용이 적절하며, 주요 저널 투고에 적합한 수준
4. **SCODA 개념의 독창성**: 데이터셋을 versioned artifact로 배포한다는 아이디어가 재현성 측면에서 설득력 있음
5. **Figure 기획이 체계적**: 3개 figure + 1개 table 구성이 concept → method → infrastructure → data 순으로 잘 설계됨

---

## 3. 주요 문제점

### (1) Introduction에 3개 draft가 그대로 남아 있음

`02_Introduction.md`에 1st/2nd/3rd draft가 모두 포함되어 있다. 3rd draft가 가장 완성도가 높으므로 이전 draft를 제거하고 3rd draft만 남겨야 한다. 또한 3rd draft 시작에 `# 1. Introduction (Paleobiology-oriented version)`이라는 작업용 제목이 있어 정리 필요.

### (2) References가 비어 있음

`10_References.md`가 완전히 비어 있다. 본문에서 언급되는 주요 참고문헌(Treatise on Invertebrate Paleontology, Jell & Adrain 2002, Adrain 2011, Paleobiology Database 등)이 반드시 추가되어야 한다.

### (3) 반복이 과도함

거의 모든 섹션이 같은 문장 패턴으로 끝남:

> "Together, the assertion-based representation of taxonomy, classification profiles, and the SCODA package model provide a framework for..."

Abstract, Introduction, Discussion, Conclusion에서 이 문구가 거의 동일하게 반복된다. 각 섹션의 마무리를 차별화해야 한다.

### (4) 구체적 데이터/예시 부족

- **Section 07 (Case Study)**: "approximately 5,600 taxa, 8,000 assertions" 등의 숫자만 있고, **실제 assertion 예시**(예: 특정 삼엽충 속이 어떤 과에서 어떤 과로 이동했는지)가 없음
- Classification profile 간 **구체적 비교 결과**가 제시되지 않음 (몇 개의 속이 다르게 배치되는지, 어떤 패턴이 있는지)
- SCODA의 **기술적 구현 세부사항**이 추상적 (manifest.json의 실제 구조, ui_queries 예시 등)

### (5) 관련 연구 비교 부족

기존 분류학 데이터베이스(PBDB, GBIF, Catalogue of Life 등)와의 **구체적 비교**가 부족하다. "canonical hierarchy"의 한계를 말하면서도 이 데이터베이스들이 실제로 어떻게 동의어나 대안적 분류를 처리하는지 분석하지 않는다.

### (6) Conclusion의 제목 오타

`09_Conclusion.md` 1행: `# # Conclusion` → `# Conclusion`으로 수정 필요.

---

## 4. 섹션별 세부 평가

| 섹션 | 완성도 | 핵심 코멘트 |
|---|---|---|
| Abstract | 90% | 잘 응축됨. 마지막 문장이 Introduction 반복 |
| Introduction | 60% | 3rd draft 기준 괜찮으나 정리 필요 |
| Limitations (03) | 85% | PBDB 언급이 조심스럽게 잘 되어 있음 |
| Assertion Model (04) | 80% | 개념은 명확하나 formal definition이 부족 |
| Classification Profiles (05) | 75% | 구체적 예시 없이 설명만 있음 |
| SCODA (06) | 80% | 개념 좋으나 기술 스펙이 모호 |
| Case Study (07) | 70% | 데이터 규모만 있고 실제 결과가 없음 |
| Discussion (08) | 85% | 균형 잡힌 톤, 기존 DB와의 보완 관계를 잘 설명 |
| Conclusion (09) | 80% | 깔끔하나 반복적 |
| References (10) | 0% | 미작성 |

---

## 5. 개선 권고 (우선순위 순)

1. **Introduction 정리**: 3rd draft만 남기고 이전 draft 삭제
2. **References 작성**: 최소 핵심 참고문헌 추가
3. **Case Study에 구체적 결과 추가**: 실제 classification profile 비교 예시, 특정 속의 이동 사례
4. **반복 문구 차별화**: 각 섹션 마무리를 다르게 작성
5. **Assertion model의 formal definition 강화**: relation type 목록, 데이터 스키마 등
6. **SCODA 기술 스펙 보강**: manifest.json 구조, .scoda 파일 포맷 등
7. **Conclusion 오타 수정**: `# #` → `#`

---

## 6. 종합 평가

**핵심 아이디어는 명확하고 학술적으로 가치가 있다.** "분류학 지식을 assertion으로 표현하고, classification을 derived view로 재구성한다"는 개념은 논리적이고 실용적이다. SCODA 패키지 모델도 재현성 문제에 대한 좋은 접근이다.

그러나 현재 원고는 **개념 설명(concept paper)에 치우쳐 있고, 실제 결과(result)가 부족하다.** Trilobase를 case study로 제시하면서도 구체적인 분석 결과나 비교 데이터가 없어, reviewer가 "이 접근법이 실제로 무엇을 보여주는가?"라는 질문에 답하기 어렵다. Figure Plan에서 기획한 Figure 2(classification comparison)의 **실제 데이터 기반 예시**를 본문에 포함시키는 것이 acceptance 가능성을 크게 높일 것이다.
