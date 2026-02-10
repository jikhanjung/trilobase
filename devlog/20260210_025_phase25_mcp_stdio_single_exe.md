# Phase 25: Single EXE with MCP stdio Mode

**Date:** 2026-02-10
**Branch:** feature/scoda-implementation
**계획 문서:** devlog/20260210_P16_mcp_stdio_single_exe.md

---

## 목표

단일 `trilobase.exe`에서 `--mcp-stdio` CLI 옵션 지원.
Claude Desktop이 직접 spawn하여 Node.js(mcp-remote) 없이 MCP 사용 가능.

---

## 변경 파일

- `scripts/gui.py`
- `trilobase.spec`

---

## 주요 변경 내용

### scripts/gui.py — main() 함수 개선

**추가된 내용:**
1. `argparse`로 `--mcp-stdio` 옵션 처리
2. `--mcp-stdio` 시 `mcp_server.run_stdio()` 직접 호출
3. GUI 모드 시 Windows에서 콘솔 창 숨김 (`ctypes.windll.user32.ShowWindow`)

**실행 모드:**
```bash
trilobase.exe              # GUI 모드 (기본, 콘솔 숨김)
trilobase.exe --mcp-stdio  # MCP stdio 모드 (stdin/stdout 통신)
```

### trilobase.spec — console 모드 변경

```python
# 이전
console=False  # GUI mode - no console window

# 이후
console=True   # Required for --mcp-stdio mode. GUI mode hides console via ctypes.
```

**이유:** stdio 모드는 stdin/stdout이 필수. `console=True`로 빌드 후 GUI 모드에서 코드로 숨김.

---

## Claude Desktop 설정

**이전 (Node.js 필요):**
```json
{
  "mcpServers": {
    "trilobase": {
      "command": "cmd",
      "args": ["/c", "npx", "-y", "mcp-remote", "http://localhost:8081/sse"]
    }
  }
}
```

**이후 (Node.js 불필요):**
```json
{
  "mcpServers": {
    "trilobase": {
      "command": "C:\\path\\to\\trilobase.exe",
      "args": ["--mcp-stdio"]
    }
  }
}
```

---

## 프로세스 구조

```
[Claude Desktop 실행]
    → trilobase.exe --mcp-stdio  (자동 spawn, 백그라운드)
    → stdin/stdout JSON-RPC 통신
    → DB 직접 접근
    → Claude Desktop 종료 시 자동 종료

[사용자가 GUI 실행 시]
    → trilobase.exe  (더블클릭, 콘솔 숨김)
    → GUI 창 표시
    → Flask(8080) 시작 (선택)
    → MCP SSE(8081) 시작 (선택)
```

두 프로세스는 완전 독립:
- 같은 exe, 다른 모드
- 동시 실행 가능 (충돌 없음)
- 각자 DB 접근 (read-only canonical)

---

## 코드 검증 결과

| 항목 | 결과 |
|------|------|
| Python syntax | ✅ OK |
| argparse 추가 | ✅ |
| --mcp-stdio 옵션 | ✅ |
| run_stdio 호출 | ✅ |
| asyncio.run 호출 | ✅ |
| ctypes 콘솔 숨김 | ✅ |
| console=True (spec) | ✅ |
| console=False 제거 | ✅ |

---

## 빌드 및 테스트 (Windows에서 진행 필요)

```bash
# 빌드
pyinstaller trilobase.spec

# GUI 모드 테스트
dist/trilobase.exe
# → 콘솔 창 없이 GUI 열림

# stdio 모드 테스트
dist/trilobase.exe --mcp-stdio
# → 콘솔에서 stdin 대기 (MCP 프로토콜)

# Claude Desktop 통합 테스트
# claude_desktop_config.json 설정 후 Claude Desktop 재시작
# "Show me the taxonomy tree" → 14개 도구 사용 가능 확인
```
