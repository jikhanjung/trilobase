# Plan P19: EXE 두 개 분리 (GUI / MCP stdio)

**작성일:** 2026-02-10
**브랜치:** `feature/scoda-implementation`

## 배경

현재 단일 `trilobase.exe` (`console=True`)의 문제:
- GUI 모드에서 PowerShell/cmd.exe가 프로세스 종료 전까지 블로킹
- `console=False`로 변경하면 MCP stdio 통신에서 stdin/stdout 핸들이 NUL로 교체됨 (PyInstaller 부트로더 동작)

## 해결 방향

EXE를 역할에 따라 두 개로 분리:

| 파일 | console | 진입점 | 용도 |
|------|---------|--------|------|
| `trilobase.exe` | `False` | `scripts/gui.py` | GUI 뷰어 (콘솔 블로킹 없음) |
| `trilobase_mcp.exe` | `True` | `mcp_server.py` | MCP stdio 서버 (인자 없이 실행) |

**Claude Desktop 설정 (단순화됨):**
```json
{
  "mcpServers": {
    "trilobase": {
      "command": "C:\\path\\to\\trilobase_mcp.exe"
    }
  }
}
```

## 변경 파일 및 내용

### 1. `trilobase.spec`

기존 단일 `EXE` 블록을 두 개로 분리.

**`trilobase.exe` (GUI):**
- `Analysis` 진입점: `scripts/gui.py`
- `console=False`
- `datas`: `app.py`, `templates`, `static`, `trilobase.db`

**`trilobase_mcp.exe` (MCP stdio):**
- `Analysis` 진입점: `mcp_server.py`
- `console=True`
- `datas`: `trilobase.db` (templates/static 불필요)
- `hiddenimports`: mcp 관련 패키지

두 EXE가 각자 독립적인 `Analysis` / `PYZ` / `EXE` 블록을 가짐.

### 2. `scripts/gui.py`

`main()` 함수 대폭 단순화:
- `argparse` 전체 제거 (GUI 전용이므로 인자 불필요)
- `--mcp-stdio` 분기 제거
- `ShowWindow` 제거 (`console=False`이므로 콘솔 창 자체가 없음)
- GUI 실행만 남음

**변경 후 `main()`:**
```python
def main():
    try:
        gui = TrilobaseGUI()
        gui.run()
    except Exception as e:
        import traceback
        print("GUI Error:", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
```

### 3. `mcp_server.py`

변경 없음. 기존 `__main__` → `main()` → `--mode` 기본값 `stdio` 동작으로 충분.

- `trilobase_mcp.exe` 실행 시: 인자 없이 `asyncio.run(run_stdio())` 호출
- 개발 모드: `python mcp_server.py --mode sse` 등 기존 사용법 유지

## 파일 구조 (dist/)

```
dist/
├── trilobase.exe          # GUI 뷰어 (console=False)
└── trilobase_mcp.exe      # MCP stdio 서버 (console=True)
```

사용자는 평소에 `trilobase.exe`만 사용.
Claude Desktop은 `trilobase_mcp.exe`만 사용.

## 미해결 항목

- `trilobase_mcp.exe`가 `trilobase_overlay.db`를 찾는 경로:
  현재 `os.path.dirname(sys.executable)` 기준 → 두 exe가 같은 디렉토리에 있으면 overlay DB를 공유함 (의도된 동작)

## 테스트 계획

1. `python scripts/gui.py` — GUI 정상 실행 (argparse 제거 후)
2. `python mcp_server.py` — 기본 stdio 모드 진입 확인
3. Windows 빌드 후:
   - `trilobase.exe` — PowerShell 즉시 반환, GUI 정상 표시
   - `trilobase_mcp.exe` — Claude Desktop에서 MCP 정상 통신
