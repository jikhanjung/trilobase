# Phase 24: GUI MCP SSE 독립 실행 분리

**Date:** 2026-02-10
**Branch:** feature/scoda-implementation
**계획 문서:** devlog/20260210_P17_gui_mcp_sse_optional.md

---

## 목표

GUI 기본 실행 시 Flask(8080)만 시작하고, MCP SSE(8081)는 별도 버튼으로 독립 실행하도록 분리.

---

## 변경 파일

- `scripts/gui.py`

---

## 주요 변경 내용

### 버튼 구성

**이전:**
```
[▶ Start All] [■ Stop All]
```

**이후:**
```
[▶ Start Flask ] [■ Stop Flask  ]
[▶ Start MCP SSE] [■ Stop MCP SSE]
```

### 메서드 변경

| 메서드 | 변경 내용 |
|--------|---------|
| `start_server()` | MCP 자동 시작 코드 제거 → Flask만 담당 |
| `stop_server()` | MCP 중지 코드 제거 → Flask만 담당 |
| `start_mcp()` | 신규 — MCP SSE 시작 버튼 핸들러 |
| `stop_mcp()` | 신규 — MCP SSE 종료 버튼 핸들러 |
| `_update_status()` | Flask/MCP 버튼 상태 완전 독립 관리 |

### 독립성

- Flask 종료 → MCP SSE 계속 실행 (영향 없음)
- MCP SSE 종료 → Flask 계속 실행 (영향 없음)
- 앱 종료 시 실행 중인 프로세스 각각 개별 정리 (기존 quit_app 로직 그대로)

---

## 배경

이 작업은 P16 (--mcp-stdio CLI 옵션 추가)의 선행 작업.
- P24 (이번): GUI에서 Flask와 MCP SSE 분리
- P25 (다음): `--mcp-stdio` CLI 옵션 추가

기존 "Start All" 방식은 GUI = MCP SSE라는 불필요한 결합이 있었음.
stdio 모드 추가 시 MCP 실행 방법이 3가지(SSE GUI / SSE mcp-remote / stdio)로
늘어나므로, GUI에서 SSE는 명시적 선택으로 전환.

---

## 테스트

WSL 환경 (tkinter 없음) → Windows에서 빌드/테스트 필요

코드 검증 (WSL):
- Python syntax check: ✅ OK
- 필수 메서드 존재: ✅ start_server, stop_server, start_mcp, stop_mcp, _update_status, _create_widgets
- "Start All" / "Stop All" 제거: ✅ 확인
- "Start MCP SSE" / "Stop MCP SSE" 추가: ✅ 확인
- start_server()에서 MCP 자동 시작 제거: ✅ 확인

---

## 다음 단계

**Phase 25:** `--mcp-stdio` CLI 옵션 추가
- `scripts/gui.py` main() 함수에 argparse 추가
- `--mcp-stdio` 옵션 시 MCP stdio 모드로 직접 실행
- `trilobase.spec`에서 `console=True`로 변경
- Claude Desktop 설정: `{"command": "trilobase.exe", "args": ["--mcp-stdio"]}`
- Node.js(mcp-remote) 의존성 제거 가능
