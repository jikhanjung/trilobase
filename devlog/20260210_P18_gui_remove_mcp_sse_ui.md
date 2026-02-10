# Plan P18: GUI에서 MCP SSE UI 요소 제거

**작성일:** 2026-02-10
**브랜치:** `feature/scoda-implementation`

## 배경

MCP는 `--mcp-stdio` 모드로 Claude Desktop과 잘 작동하고 있음.
SSE 모드는 불필요하므로, GUI에서 MCP SSE 관련 버튼과 상태 표시 요소를 제거하여 UI를 간결하게 정리.

## 제거 대상 (UI 요소)

### `_create_widgets` 내 Info 섹션

| 요소 | 설명 |
|------|------|
| `mcp_status_row` + `self.mcp_status_label` | MCP: ● Stopped 상태 표시 행 |
| `mcp_url_row` + `self.mcp_url_label` | MCP URL: http://localhost:8081 표시 행 |

### `_create_widgets` 내 Controls 섹션

| 요소 | 설명 |
|------|------|
| `mcp_row` (Frame) | MCP 버튼 컨테이너 |
| `self.mcp_start_btn` | ▶ Start MCP SSE 버튼 |
| `self.mcp_stop_btn` | ■ Stop MCP SSE 버튼 |

### `_update_status` 내 MCP 관련 코드

| 코드 블록 | 설명 |
|-----------|------|
| MCP status label 업데이트 | `self.mcp_status_label.config(...)` |
| MCP URL label 업데이트 | `self.mcp_url_label.config(...)` |
| MCP SSE 버튼 상태 업데이트 | `self.mcp_start_btn.config(...)`, `self.mcp_stop_btn.config(...)` |

## 유지 대상 (변경하지 않음)

- `__init__`의 MCP 상태 변수들 (`mcp_running`, `mcp_process`, `mcp_port` 등)
- `start_mcp()`, `stop_mcp()`, `_start_mcp_server()` 등 MCP SSE 메서드 (코드 로직 보존)
- `quit_app()`의 `self.mcp_running` 체크 및 `mcp_process.terminate()` (안전한 종료 유지)
- `--mcp-stdio` 관련 `main()` 함수 코드 (Claude Desktop 연동용, 유지 필수)
- `mcp_port = 8081` 변수 (내부 코드에서 참조 가능성)

> 이유: UI를 숨기는 것이지, MCP SSE 기능 자체를 삭제하는 것은 아님.
> 코드 로직은 그대로 두고 UI 레이어만 제거.

## 변경 파일

- `scripts/gui.py`

## 예상 결과

- GUI가 더 간결해짐 (Flask 제어에만 집중)
- `--mcp-stdio` 모드는 영향 없음
- MCP SSE 버튼 참조로 인한 `_update_status` 오류 발생하지 않도록 해당 블록 제거

## 작업 순서

1. `_create_widgets` — MCP Status 행 제거 (Info 섹션)
2. `_create_widgets` — MCP URL 행 제거 (Info 섹션)
3. `_create_widgets` — MCP SSE Start/Stop 버튼 행 제거 (Controls 섹션)
4. `_update_status` — MCP 관련 label/button 업데이트 블록 제거

## 테스트 계획

- GUI 실행 확인 (AttributeError 없음)
- Flask 시작/중지 정상 동작 확인
- `python scripts/gui.py` 실행 후 UI 검토
