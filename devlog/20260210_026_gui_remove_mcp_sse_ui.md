# 작업 로그 026: GUI MCP SSE UI 요소 제거

**작업일:** 2026-02-10
**브랜치:** `feature/scoda-implementation`
**계획 문서:** `devlog/20260210_P18_gui_remove_mcp_sse_ui.md`

## 작업 배경

MCP는 `--mcp-stdio` 모드로 Claude Desktop과 정상 동작 중.
SSE 모드는 더 이상 필요하지 않으므로, GUI에서 MCP SSE 관련 UI 요소를 제거하여 인터페이스를 단순화.

## 변경 파일

- `scripts/gui.py`

## 변경 내용

### 제거된 UI 요소

**Info 섹션 (`_create_widgets`)**

| 제거 항목 | 내용 |
|----------|------|
| `mcp_status_row` + `mcp_status_label` | "MCP: ● Stopped" 상태 표시 행 |
| `mcp_url_row` + `mcp_url_label` | "MCP URL: http://localhost:8081" 표시 행 |

**Controls 섹션 (`_create_widgets`)**

| 제거 항목 | 내용 |
|----------|------|
| `mcp_row` (Frame) | MCP 버튼 컨테이너 |
| `mcp_start_btn` | ▶ Start MCP SSE 버튼 |
| `mcp_stop_btn` | ■ Stop MCP SSE 버튼 |

**`_update_status()` 메서드**

| 제거 항목 | 내용 |
|----------|------|
| MCP status 업데이트 블록 | `mcp_status_label`, `mcp_url_label` config 호출 |
| MCP 버튼 상태 업데이트 블록 | `mcp_start_btn`, `mcp_stop_btn` config 호출 |

### 유지된 항목

- `__init__`의 MCP 상태 변수 (`mcp_running`, `mcp_process`, `mcp_port` 등)
- `start_mcp()`, `stop_mcp()`, `_start_mcp_server()` 등 SSE 관련 메서드 (코드 보존)
- `quit_app()`의 `mcp_process.terminate()` (안전한 종료 유지)
- `main()`의 `--mcp-stdio` 분기 (Claude Desktop 연동 필수)

## 테스트

- `ast.parse()` 문법 검사 통과
- 제거된 위젯 참조 잔존 여부 확인: 없음

## 결과

GUI가 Flask 서버 제어에만 집중하는 간결한 레이아웃으로 정리됨.
MCP stdio 모드는 영향 없이 정상 유지.
