# 073: Structured Logging 도입

**작성일:** 2026-02-17
**계획 문서:** `devlog/20260217_P57_structured_logging.md`

## 개요

SCODA Desktop 런타임 4개 핵심 파일에 Python `logging` 모듈을 도입하여 구조화된 로깅 체계를 구축.

## 변경 파일

### `scoda_package.py` (+23줄)
- `logger = logging.getLogger(__name__)` 추가
- `ScodaPackage.__init__()`: INFO 패키지 열기, DEBUG manifest 내용
- `PackageRegistry.scan()`: INFO 스캔 디렉토리, WARNING 유효하지 않은 패키지
- `PackageRegistry.get_db()`: DEBUG overlay/dependency ATTACH
- `_resolve_paths()`: INFO 최종 DB 경로, DEBUG frozen/dev 모드 분기
- `_ensure_overlay_for_package()`, `ensure_overlay_db()`: INFO 신규 overlay 생성

### `mcp_server.py` (+15줄, -3줄)
- `print()` 3줄 → `logger.info()` 전환 (SSE 서버 시작 메시지)
- `call_tool()`: INFO 도구 호출 (이름 + 인자 요약)
- `_execute_named_query_internal()`: DEBUG 쿼리 결과 행수, WARNING 미발견, ERROR 실패
- `_execute_dynamic_tool()`: DEBUG 쿼리 타입
- Unknown tool: WARNING

### `app.py` (+6줄)
- `_auto_generate_manifest()`: INFO 자동 생성 (테이블 수)
- `_execute_query()`: ERROR 쿼리 실패
- `api_composite_detail()`: WARNING detail view 미발견

### `gui.py` (+31줄)
- `TkLogHandler` 클래스 신규: Python `logging.Handler` → GUI 로그 패널 라우팅
- 레벨별 색상 매핑: ERROR→빨강, WARNING→주황, INFO→파랑
- `scoda_desktop` 로거에 핸들러 등록 (DEBUG 레벨)

## 설계 원칙

- **최소 침습**: 기존 동작 변경 없음, 로그 추가만
- **stdlib만 사용**: 외부 의존성 없음
- **DEBUG 위주**: 기본 실행 시 보이지 않음, 문제 해결 시 활성화
- **INFO는 시작/중요 이벤트만**, **WARNING/ERROR는 실패/폴백 시만**

## 영향도

- 외부 의존성 추가: 없음
- 기존 동작 변경: `mcp_server.py`의 `print()` 3줄만 `logger.info()`로 전환
- 테스트 영향: 없음
- 총 변경: +71줄, -4줄
