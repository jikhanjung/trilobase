# P57: Structured Logging 도입

**작성일:** 2026-02-17
**상태:** 계획

## 배경

현재 SCODA Desktop 런타임은 Python `logging` 모듈을 전혀 사용하지 않음.
- `app.py`: 로깅 없음 (uvicorn 기본 로그만 의존)
- `mcp_server.py`: `print()` 3줄 (시작 메시지만)
- `scoda_package.py`: 완전 무음 (예외만 발생)
- `gui.py`: 자체 `LogRedirector` + `_append_log()` (잘 동작하므로 유지)
- `serve.py`: `print()` 배너 (단순 런처, 변경 불필요)

## 목표

**3개 핵심 파일**에 Python `logging` 모듈 도입:
1. `scoda_package.py` — 패키지 탐색, DB ATTACH, overlay 생성 추적
2. `mcp_server.py` — 도구 호출 기록, 에러 진단
3. `app.py` — 쿼리 실행 에러, composite 쿼리 진단

GUI(`gui.py`), 런처(`serve.py`)는 변경하지 않음.

## 원칙

- **최소 침습**: 기존 동작 변경 없음, 로그 추가만
- **stdlib만 사용**: 외부 의존성 추가 없음
- **DEBUG 레벨 위주**: 기본 실행 시 보이지 않음, 문제 해결 시 활성화
- **INFO는 시작/중요 이벤트만**: 패키지 로드, DB 연결, 서버 시작
- **WARNING/ERROR**: 실패/폴백 시에만

## 구현 계획

### Step 1: `scoda_package.py` 로깅 추가

```python
import logging
logger = logging.getLogger(__name__)
```

로그 포인트:
- `ScodaPackage.__init__()`: INFO 패키지 열기, DEBUG manifest 내용
- `ScodaPackage.close()`: DEBUG 정리
- `PackageRegistry.scan()`: INFO 탐색 디렉토리, 발견 패키지 수, WARNING 유효하지 않은 패키지
- `PackageRegistry.get_db()`: DEBUG DB 연결 (overlay ATTACH, dependency ATTACH)
- `_resolve_paths()`: INFO 최종 경로, DEBUG 탐색 과정 (frozen/dev 모드)
- `_resolve_dependencies()`: DEBUG 의존성 해석
- `ensure_overlay_db()`: INFO 신규 생성, DEBUG 이미 존재
- `get_db()`: DEBUG 연결 모드 (active package / legacy)

### Step 2: `mcp_server.py` 로깅 추가

```python
import logging
logger = logging.getLogger(__name__)
```

로그 포인트:
- `call_tool()`: INFO 도구 호출 (이름 + 인자 요약), WARNING 알 수 없는 도구
- `_execute_dynamic_tool()`: DEBUG 쿼리 타입/이름, ERROR SQL 실행 실패
- `_execute_named_query_internal()`: DEBUG 쿼리 이름, ERROR 실행 실패
- `run_stdio()` / `run_sse()`: INFO 서버 시작 (기존 `print()` 대체)
- `create_mcp_app()`: DEBUG SSE 앱 생성

### Step 3: `app.py` 로깅 추가

```python
import logging
logger = logging.getLogger(__name__)
```

로그 포인트:
- `_execute_query()`: DEBUG 쿼리 이름, ERROR 실행 실패
- `api_composite_detail()`: DEBUG 뷰 이름 + sub-query 수, WARNING 뷰 미발견
- `api_entity_detail()`: DEBUG entity 이름 + sub-query 수
- `_auto_generate_manifest()`: INFO 자동 생성 (테이블 수)

### Step 4: GUI 로거 연결

`gui.py`의 기존 `LogRedirector`에 Python `logging.Handler`를 추가하여 stdlib 로그가 GUI 로그 패널에도 표시되도록 연결.

```python
class TkLogHandler(logging.Handler):
    def emit(self, record):
        self._append_log(self.format(record), record.levelname)
```

## 영향도

- 외부 의존성 추가: 없음 (stdlib만)
- 기존 동작 변경: `mcp_server.py`의 `print()` 3줄 → `logger.info()` 전환
- 테스트 영향: 없음 (로그 출력은 테스트에 영향 주지 않음)
- 성능 영향: 무시 가능 (DEBUG 레벨은 기본적으로 비활성)

## 예상 변경량

| 파일 | 추가/수정 줄 수 |
|------|----------------|
| `scoda_package.py` | ~25줄 |
| `mcp_server.py` | ~20줄 |
| `app.py` | ~15줄 |
| `gui.py` | ~20줄 (TkLogHandler) |
| **합계** | **~80줄** |
