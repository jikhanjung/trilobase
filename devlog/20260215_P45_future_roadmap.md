# 향후 주요 작업 로드맵

**작성일:** 2026-02-15

현재까지 Phase 46 + UID Phase B 완료. 아래는 향후 진행할 큰 주제 3가지.

---

## 1. Flask → FastAPI 전환

**현재 상태:** `scoda_desktop/app.py`가 Flask 기반 (동기, WSGI)

**목표:** FastAPI (비동기, ASGI)로 전환

**동기:**
- MCP 서버(`mcp_server.py`)가 이미 Starlette + Uvicorn (ASGI) 사용 중 — Flask와 이중 스택
- async/await 네이티브 지원으로 DB 쿼리 병렬화 가능
- 자동 OpenAPI 문서 생성 (Swagger UI)
- Pydantic 기반 요청/응답 검증
- ASGI 단일 스택으로 통합 (Flask WSGI + Starlette ASGI → FastAPI ASGI만)

**주요 작업:**
- Flask route → FastAPI router 전환
- Jinja2 템플릿 서빙 방식 변경 (또는 static file 서빙으로 단순화)
- GUI(`gui.py`), serve.py의 서버 실행 방식 변경 (Werkzeug → Uvicorn)
- MCP 서버와 ASGI 앱 통합 가능성 검토 (단일 Uvicorn 프로세스)
- PyInstaller 빌드 호환성 확인
- 테스트 전환 (Flask test client → httpx AsyncClient)

**영향 범위:** `app.py`, `serve.py`, `gui.py`, `ScodaDesktop.spec`, 테스트 전체

---

## 2. Taxonomic Opinions — 문헌 기반 다중 견해 기록

**현재 상태:** 한 taxon에 대해 하나의 분류 체계만 기록 (예: Family Eurekiidae의 소속 Order가 하나만 존재)

**목표:** 동일 taxon에 대해 서로 다른 문헌(provenance)에 기반한 여러 분류학적 견해를 기록하고 비교 표시

**예시:**
- Eurekiidae를 Ptychopariida에 넣는 견해 (Jell & Adrain, 2002)
- Eurekiidae를 Asaphida에 넣는 견해 (Fortey, 1990)
- 각 견해에 근거 문헌, 연도, 신뢰도 등 부여

**주요 작업:**
- 데이터 모델 설계: `taxonomic_opinions` 테이블 (taxon_id, opinion_type, value, bibliography_id, provenance 등)
- opinion_type 정의: placement (소속), validity (유효성), synonymy (동의어 관계) 등
- 기본 견해(default opinion) vs 대안 견해 구분
- Web UI: taxon 상세에서 "Opinions" 섹션 — 문헌별 견해 목록, 비교 뷰
- MCP 도구: `get_taxon_opinions` 등
- SCODA 원칙 유지: canonical 데이터의 불변성과 opinions 레이어의 관계 정의

**핵심 질문:**
- Opinions를 canonical DB에 넣을 것인가, overlay에 넣을 것인가?
- 기존 `synonyms` 테이블과의 관계는?
- bibliography 테이블과의 연결 (FK vs UID)

---

## 3. SCODA Package 백오피스 시스템

**현재 상태:** .scoda 패키지 생성은 CLI 스크립트(`create_scoda.py`, `create_paleocore_scoda.py`)로 수동 실행

**목표:** .scoda 패키지를 관리하고 패키징하는 웹 기반 백오피스 시스템

**주요 기능:**
- 패키지 목록 관리 (생성, 버전 관리, 메타데이터 편집)
- DB 테이블 브라우저 / 편집기
- manifest.json 시각적 편집 (뷰 정의, 쿼리, display intent)
- mcp_tools.json 편집 / 검증
- 패키지 빌드 & 릴리스 (원클릭 .scoda 생성, SHA-256, 불변성 검증)
- dependency 관리 (PaleoCore 등 참조 패키지 연결)
- schema_descriptions, provenance 등 SCODA 메타데이터 편집 UI
- 패키지 간 UID 참조 검증

**아키텍처 고려:**
- 별도 프로젝트 vs trilobase 저장소 내 서브디렉토리
- FastAPI 백엔드 (주제 1과 연계)
- 프론트엔드: React/Vue SPA 또는 단일 파일 SPA
- SQLite 직접 조작 vs 추상화 레이어

---

## 우선순위 및 의존 관계

```
1. Flask → FastAPI 전환
   (기반 인프라 — 나머지 작업의 토대)
       │
       ├→ 2. Taxonomic Opinions
       │     (데이터 모델 확장, UI/MCP 추가)
       │
       └→ 3. SCODA 백오피스
             (별도 시스템, FastAPI 경험 활용)
```

- **1번**이 가장 먼저 — 이후 작업이 모두 새 스택 위에서 진행
- **2번**은 데이터 모델 설계가 핵심 — 작은 PoC부터 시작 가능
- **3번**은 가장 큰 범위 — 별도 프로젝트로 분리할 수도 있음
