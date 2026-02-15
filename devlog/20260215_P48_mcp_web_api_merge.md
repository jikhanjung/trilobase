# MCP + Web API 단일 프로세스 통합

**날짜:** 2026-02-15
**유형:** 계획(Plan)

## Context

현재 Web API(FastAPI, 포트 8080)와 MCP SSE 서버(Starlette, 포트 8081)가 별도 프로세스로 실행됨. FastAPI 마이그레이션 완료 후 두 ASGI 앱을 단일 프로세스(포트 8080)로 통합하여 운영 단순화.

## 현재 구조

- `app.py`: FastAPI — `/api/*` + SPA catch-all `/{filename:path}` (포트 8080)
- `mcp_server.py`: Starlette — `/sse`, `/messages`, `/health` (포트 8081, 별도 프로세스)
- `gui.py`: 두 서버를 개별 관리 (Start/Stop Flask + Start/Stop MCP SSE)
- DB 접근: 둘 다 동일한 `scoda_package.get_db()` 사용 → 충돌 없음

## 핵심 설계: Sub-App Mount

FastAPI의 `app.mount("/mcp", starlette_app)`로 MCP Starlette 앱을 `/mcp` 경로에 마운트.

- `GET /mcp/sse` — SSE 연결
- `POST /mcp/messages` — MCP 메시지
- `GET /mcp/health` — 헬스체크

`SseServerTransport("/messages")`는 `scope["root_path"]`를 읽어 `/mcp/messages?session_id=...`로 올바르게 응답. CORS 미들웨어는 마운트된 서브앱에도 적용됨. `/{filename:path}` catch-all보다 mount가 우선 매칭되므로 충돌 없음.

stdio 모드(`python -m scoda_desktop.mcp_server`)는 변경 없이 유지.

## 변경 사항

### 1. `scoda_desktop/mcp_server.py` — 팩토리 함수 추출

`run_sse()`에서 Starlette 앱 생성 로직을 `create_mcp_app()` 함수로 분리:

```python
def create_mcp_app() -> Starlette:
    """Create MCP SSE Starlette app for mounting."""
    ensure_overlay_db()
    sse = SseServerTransport("/messages")
    server = _create_mcp_server()  # 기존 Server + tools 설정

    async def handle_sse(request):
        async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
            await server.run(streams[0], streams[1], server.create_initialization_options())

    async def handle_messages(request):
        await sse.handle_post_message(request.scope, request.receive, request._send)

    async def health_check(request):
        return JSONResponse({"status": "ok"})

    return Starlette(routes=[
        Route("/sse", endpoint=handle_sse),
        Route("/messages", endpoint=handle_messages, methods=["POST"]),
        Route("/health", endpoint=health_check),
    ])
```

`run_sse()`는 standalone 용도로 유지 (내부에서 `create_mcp_app()` 호출).

### 2. `scoda_desktop/app.py` — MCP 마운트

```python
from .mcp_server import create_mcp_app
app.mount("/mcp", create_mcp_app())
```

`/{filename:path}` catch-all 정의 이전에 mount 호출 (Starlette는 mount를 우선 매칭).

### 3. `scoda_desktop/gui.py` — MCP 프로세스 관리 제거

삭제할 요소:
- `mcp_port`, `mcp_process`, `mcp_thread`, `mcp_running` 속성
- `start_mcp()`, `stop_mcp()`, `_start_mcp_subprocess()`, `_start_mcp_threaded()`, `_read_mcp_logs()` 메서드
- MCP 관련 UI (Start/Stop MCP SSE 버튼이 이미 제거됨 — 확인 필요)
- `quit_app()`에서 MCP 중지 로직

MCP 상태/URL 표시가 남아있다면 함께 정리.

### 4. `ScodaDesktop.spec` — MCP EXE 이름 변경

`ScodaDesktop_mcp` → `ScodaMCP`로 리네이밍:
- `name='ScodaDesktop_mcp'` → `name='ScodaMCP'`
- 배포: `ScodaDesktop.exe` + `ScodaMCP.exe`

### 5. `scoda_desktop/serve.py` — 변경 없음

이미 `app`만 실행하므로 MCP도 자동 포함됨.

### 6. 테스트 추가

기존 MCP 테스트(`test_mcp.py`, `test_mcp_basic.py`)는 stdio 모드 사용 → 영향 없음.

통합 테스트 추가 (`test_runtime.py`):
```python
def test_mcp_health_via_mount(client):
    """MCP health endpoint accessible through main app."""
    resp = client.get("/mcp/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
```

## 변경 파일

| 파일 | 변경 규모 | 설명 |
|------|----------|------|
| `scoda_desktop/mcp_server.py` | 소 | `create_mcp_app()` 팩토리 추출, `run_sse()` 리팩터 |
| `scoda_desktop/app.py` | 소 | `app.mount("/mcp", create_mcp_app())` 추가 |
| `scoda_desktop/gui.py` | 중 | MCP 프로세스 관리 코드 제거 (~100줄) |
| `tests/test_runtime.py` | 소 | `/mcp/health` 통합 테스트 추가 |
| `ScodaDesktop.spec` | 소 | `ScodaDesktop_mcp` → `ScodaMCP` 리네이밍 |
| `scoda_desktop/serve.py` | 없음 | 변경 불필요 |

## 검증

```bash
# 전체 테스트
pytest tests/ -x -q  # 226+ 통과

# 수동 확인
python -m scoda_desktop.serve
curl http://localhost:8080/api/manifest          # Web API
curl http://localhost:8080/mcp/health            # MCP health
curl http://localhost:8080/mcp/sse               # SSE stream

# stdio 모드 (Claude Desktop용) — 변경 없이 동작
python -m scoda_desktop.mcp_server
```
