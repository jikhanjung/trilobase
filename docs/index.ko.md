# Trilobase

**Trilobase**는 삼엽충(Trilobita) 속(genus) 수준의 분류학 정보를
문헌 기반으로 정제·정규화하여 구축한 **연구용 관계형 데이터베이스**입니다.

기존 분류학 문헌에 흩어져 있는 속명, 동의어, 상위 분류군,
산지 및 지층 정보를 **기계가 질의 가능한 형태(SQLite)**로 구조화하는 것이 목표입니다.

---

## 주요 문헌

- **Jell, P.A. & Adrain, J.M. (2002)** — *Available Generic Names for Trilobites*,
  Memoirs of the Queensland Museum 48(2): 331–553.
- **Adrain, J.M. (2011)** — *Class Trilobita Walch, 1771*,
  in Zhang, Z.-Q. (Ed.), Animal biodiversity (Zootaxa 3148): 104–109.

---

## 데이터베이스 현황

| 분류 계급 | 건수 |
|-----------|------|
| Class     | 1    |
| Order     | 12   |
| Suborder  | 8    |
| Superfamily | 13 |
| Family    | 191  |
| Genus     | 5,113 |
| **합계**  | **5,338** |

### 속(Genus) 상세

- **유효 속**: 4,258 (83.3%)
- **무효 속**: 855 (16.7%)
- **동의어 관계**: 1,055건
- **참고문헌**: 2,130건
- **분류학적 의견**: 84건

---

## 주요 기능

- **완전한 속 목록** — Jell & Adrain (2002)의 5,113개 속, 모든 삼엽충 목 포괄
- **동의어 해소** — 1,055건의 동의어 관계, 99.9% 연결율
- **계층적 분류** — Class → Order → Suborder → Superfamily → Family → Genus
- **지리 정보** — 142개국에 걸친 4,841건의 속-국가 연결
- **층서 정보** — 2,004개 지층에 걸친 4,853건의 속-지층 연결
- **문헌 인용** — 2,130건의 참고문헌과 FK 연결
- **MCP 통합** — Claude Desktop을 통한 자연어 질의 14개 도구
- **SCODA 패키징** — 재현 가능한 배포를 위한 자기완결적 데이터 아티팩트 형식

---

## SCODA 프레임워크

Trilobase는 **SCODA** (Self-Contained Data Artifact) 프레임워크의 참조 구현입니다.
하나의 `.scoda` 파일에 데이터베이스, 메타데이터, 출처, 스키마 설명,
UI 정의가 모두 포함되어 외부 문서 없이도 데이터 스스로를 설명합니다.

```sql
-- 아티팩트 정보 확인
SELECT * FROM artifact_metadata;

-- 데이터 출처 확인
SELECT source_type, citation, year FROM provenance;

-- 스키마 설명 조회
SELECT * FROM schema_descriptions WHERE table_name = 'taxonomic_ranks';
```

---

## 바로가기

- [시작하기](getting-started.md) — 설치 및 사용 방법
- [데이터베이스 스키마](database/schema.md) — 테이블 정의 및 컬럼 설명
- [SQL 쿼리 예제](database/queries.md) — 쿼리 예제 모음
- [MCP 도구](api/mcp-tools.md) — Model Context Protocol을 통한 LLM 통합
- [변경 기록](project/changelog.md) — 릴리스 이력
