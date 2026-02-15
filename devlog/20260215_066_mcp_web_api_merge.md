# MCP + Web API 단일 프로세스 통합

**날짜:** 2026-02-15
**계획 문서:** `devlog/20260215_P48_mcp_web_api_merge.md`

## 작업 내용

FastAPI(포트 8080)와 MCP SSE 서버(Starlette, 포트 8081)를 단일 프로세스(포트 8080)로 통합.

### 핵심 설계: Sub-App Mount

FastAPI의 `app.mount("/mcp", starlette_app)`로 MCP Starlette 앱을 `/mcp` 경로에 마운트:

- `GET /mcp/sse` — SSE 연결 (MCP 통신)
- `POST /mcp/messages` — MCP 메시지
- `GET /mcp/health` — 헬스체크

`/{filename:path}` catch-all보다 mount가 우선 매칭되므로 충돌 없음.
stdio 모드(`python -m scoda_desktop.mcp_server`)는 변경 없이 유지.

## 변경 파일

| 파일 | 변경 | 설명 |
|------|------|------|
| `scoda_desktop/mcp_server.py` | +13/-5 | `create_mcp_app()` 팩토리 추출, `run_sse()` 리팩터 |
| `scoda_desktop/app.py` | +5 | `app.mount("/mcp", create_mcp_app())` 추가 |
| `scoda_desktop/gui.py` | -125 | MCP 프로세스 관리 코드 전면 제거 |
| `tests/test_runtime.py` | +15 | `/mcp/health`, `/mcp/messages` 통합 테스트 추가 |
| `ScodaDesktop.spec` | +-6 | `ScodaDesktop_mcp` → `ScodaMCP` 리네이밍 |

## 제거된 코드 (gui.py, ~100줄)

- `mcp_port`, `mcp_process`, `mcp_thread`, `mcp_log_reader_thread`, `mcp_running` 속성
- `start_mcp()`, `stop_mcp()`, `_start_mcp_server()` 메서드
- `_start_mcp_threaded()`, `_start_mcp_subprocess()`, `_read_mcp_logs()` 메서드
- `quit_app()`의 MCP 중지 로직

## 테스트

- 228개 전부 통과 (기존 226 + 신규 2)
- 신규: `TestMCPMount.test_mcp_health_via_mount`, `TestMCPMount.test_mcp_messages_rejects_get`
- 기존 MCP 테스트(`test_mcp.py`, `test_mcp_basic.py`)는 stdio 모드 사용 → 영향 없음
