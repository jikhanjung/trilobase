# Plan: GUI에서 MCP SSE 실행을 선택적 옵션으로 분리

**Date:** 2026-02-10
**Type:** Plan (P17)
**Goal:** GUI 기본 실행 시 Flask(8080)만 시작, MCP SSE(8081)는 별도 버튼으로 선택 실행

---

## 현재 상태

**현재 동작:**
- "▶ Start All" 클릭 → Flask(8080) + MCP SSE(8081) **동시 시작** (필수)
- "■ Stop All" 클릭 → 둘 다 동시 종료

**문제점:**
- MCP SSE가 필요 없는 사용자에게도 강제로 시작됨
- GUI = MCP SSE라는 불필요한 결합
- 향후 stdio 모드 추가 시 혼란 가능성

---

## 목표 상태

**변경 후 동작:**

```
GUI 기본 실행:
  ▶ Start Flask  → Flask(8080)만 시작
  ■ Stop Flask   → Flask만 종료

MCP SSE 옵션 (별도 버튼):
  ▶ Start MCP SSE → MCP SSE(8081) 시작
  ■ Stop MCP SSE  → MCP SSE 종료
```

---

## 변경 범위

**파일:** `scripts/gui.py`만 수정

### 1. `_create_widgets()` — 버튼 구성 변경

**현재:**
```
[▶ Start All] [■ Stop All]
```

**변경 후:**
```
[▶ Start Flask ] [■ Stop Flask  ]
[▶ Start MCP SSE] [■ Stop MCP SSE]
```

- `self.start_btn`: "▶ Start All" → "▶ Start Flask"
- `self.stop_btn`: "■ Stop All" → "■ Stop Flask"
- 신규 `self.mcp_start_btn`: "▶ Start MCP SSE" (파란색)
- 신규 `self.mcp_stop_btn`: "■ Stop MCP SSE" (보라색, 초기 disabled)

### 2. `start_server()` — MCP 자동 시작 코드 제거

**현재 (제거할 코드):**
```python
# Start MCP server
try:
    self._start_mcp_server()
    self.mcp_running = True
    self._update_status()
except Exception as mcp_error:
    self._append_log(f"WARNING: MCP server failed to start: {mcp_error}", "WARNING")
```

**변경 후:** Flask 시작만 담당, MCP 관련 코드 없음

### 3. 신규 메서드 `start_mcp()` 추가

```python
def start_mcp(self):
    """Start MCP SSE server (optional)."""
    if self.mcp_running:
        return
    if not self.server_running:
        self._append_log("Flask server must be running first.", "WARNING")
        return
    try:
        self._start_mcp_server()
        self.mcp_running = True
        self._update_status()
    except Exception as e:
        self._append_log(f"ERROR: Failed to start MCP server: {e}", "ERROR")
```

**주의:** Flask가 실행 중이어야 MCP SSE 시작 가능 여부 결정 필요
- Flask 없이도 MCP SSE 독립 실행 가능하면 조건 제거
- Flask 의존 관계가 있다면 유지

### 4. 신규 메서드 `stop_mcp()` 추가

```python
def stop_mcp(self):
    """Stop MCP SSE server."""
    if not self.mcp_running:
        return
    self._append_log("Stopping MCP server...", "INFO")
    self.mcp_running = False
    if self.mcp_process:
        try:
            self.mcp_process.terminate()
            self.mcp_process.wait(timeout=3)
            self._append_log("MCP server stopped.", "INFO")
        except subprocess.TimeoutExpired:
            self.mcp_process.kill()
            self.mcp_process.wait()
        except Exception as e:
            self._append_log(f"WARNING: {e}", "WARNING")
        finally:
            self.mcp_process = None
    self._update_status()
```

### 5. `stop_server()` — MCP 중지 코드 제거

**현재:** Flask + MCP 둘 다 중지
**변경 후:** Flask만 중지. MCP는 `stop_mcp()`가 담당

단, 앱 종료 시(`quit_app()`)는 Flask + MCP 모두 정리해야 하므로
`quit_app()`에서 `stop_mcp()` → `stop_server()` 순으로 호출

### 6. `_update_status()` — MCP 버튼 상태 분리 관리

**현재:** Flask/MCP 합쳐서 `any_running`으로 하나의 버튼 제어

**변경 후:**
```python
# Flask 버튼 독립 관리
if self.server_running:
    self.start_btn.config(state="disabled", relief="sunken")
    self.stop_btn.config(state="normal", relief="raised")
else:
    self.start_btn.config(state="normal" if self.db_exists else "disabled", relief="raised")
    self.stop_btn.config(state="disabled", relief="sunken")

# MCP SSE 버튼 독립 관리
if self.mcp_running:
    self.mcp_start_btn.config(state="disabled", relief="sunken")
    self.mcp_stop_btn.config(state="normal", relief="raised")
else:
    self.mcp_start_btn.config(state="normal" if self.db_exists else "disabled", relief="raised")
    self.mcp_stop_btn.config(state="disabled", relief="sunken")
```

---

## 열린 질문

### Q1. MCP SSE 시작 시 Flask 실행 여부 필수인가?
- MCP SSE는 Flask와 독립적으로 실행 가능 (별개 포트)
- **결론:** Flask 없이도 MCP SSE 단독 시작 가능하도록 조건 제거

### Q2. Flask 종료 시 MCP SSE도 함께 종료할까?
- **결론:** 완전 독립. `stop_server()`는 Flask만 담당. MCP SSE는 `stop_mcp()`로만 종료.

---

## P16과의 관계

이 작업(P17)은 P16(stdio 모드 추가)의 선행 작업:

```
P17 완료 (GUI MCP SSE 분리)
    ↓
P16 진행 (--mcp-stdio CLI 옵션 추가)
```

P17 완료 후 GUI 구조:
```
[▶ Start Flask ] [■ Stop Flask  ]   ← HTTP API 서버
[▶ Start MCP SSE] [■ Stop MCP SSE]  ← SSE 방식 (mcp-remote 필요)
```

P16 완료 후 전체 그림:
```
trilobase.exe               → GUI (Flask + optional MCP SSE)
trilobase.exe --mcp-stdio   → MCP stdio (Claude Desktop 직접 spawn)
```

---

## 성공 기준

- [ ] GUI 실행 시 Flask(8080)만 기본 시작
- [ ] "▶ Start MCP SSE" 버튼 클릭 시 MCP SSE(8081) 시작
- [ ] Flask/MCP 버튼이 독립적으로 동작
- [ ] 앱 종료 시 실행 중인 서버 모두 정리
- [ ] 기존 MCP SSE 기능은 그대로 동작

---

**End of Plan**
