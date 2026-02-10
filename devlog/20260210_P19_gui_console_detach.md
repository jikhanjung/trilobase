# Plan P19: GUI 실행 시 콘솔 독립 실행 (DETACHED_PROCESS)

**작성일:** 2026-02-10
**브랜치:** `feature/scoda-implementation`

## 문제

cmd.exe에서 `trilobase.exe`를 실행하면:
1. tkinter GUI 창이 열리고
2. 콘솔 창이 최소화된 채 대기 상태에 머무름

사용자가 GUI를 닫을 때까지 cmd.exe가 블로킹됨.

## 근본 원인

Phase 25에서 `--mcp-stdio` 지원을 위해 PyInstaller spec을 `console=True`로 변경.

Windows는 실행 파일의 **서브시스템(subsystem)** 으로 대기 여부를 결정:
- `console=False` → GUI subsystem → cmd.exe 즉시 반환 (이전 동작)
- `console=True` → Console subsystem → cmd.exe 프로세스 종료까지 대기 (현재 동작)

현재 코드의 `ShowWindow(hwnd, 0)` 은 콘솔 창을 숨기기만 할 뿐, cmd.exe의 대기 상태는 해제하지 못함.

## 해결 방법

GUI 모드(frozen + Windows)에서 **`DETACHED_PROCESS`** 플래그로 자기 자신을 재실행(re-spawn)하고 즉시 종료.

```
[사용자 실행]
    trilobase.exe
        ↓
[원본 프로세스] → re-spawn(DETACHED_PROCESS) → [재실행 프로세스] → GUI 시작
        ↓ 즉시 종료
[cmd.exe 해방]
```

재실행 루프 방지를 위해 숨겨진 `--gui-detached` 플래그 추가.

## 동작 시나리오별 결과

| 실행 방법 | 동작 |
|----------|------|
| `trilobase.exe` (cmd.exe에서) | 원본 즉시 종료 → cmd.exe 해방 → 재실행 프로세스가 GUI 실행 |
| `trilobase.exe` (더블클릭) | 원본 즉시 종료 → 잠깐 생성된 콘솔 창 닫힘 → 재실행 프로세스가 콘솔 없이 GUI 실행 |
| `trilobase.exe --mcp-stdio` | re-spawn 로직 완전히 건너뜀 (영향 없음) |
| `python scripts/gui.py` (개발 모드) | `sys.frozen`이 False이므로 re-spawn 건너뜀 (영향 없음) |

## 변경 내용

### `scripts/gui.py`의 `main()` 함수

**argparse에 숨겨진 플래그 추가:**
```python
parser.add_argument('--gui-detached', action='store_true', help=argparse.SUPPRESS)
```

**GUI 모드 블록 교체:**
```python
else:
    # Windows frozen 모드에서 DETACHED_PROCESS로 재실행 (콘솔 독립)
    if getattr(sys, 'frozen', False) and sys.platform == 'win32' and not args.gui_detached:
        DETACHED_PROCESS = 0x00000008
        subprocess.Popen(
            [sys.executable, '--gui-detached'],
            creationflags=DETACHED_PROCESS,
            close_fds=True
        )
        sys.exit(0)

    # (ShowWindow 코드 제거 — 재실행된 프로세스는 콘솔 자체가 없음)
    try:
        gui = TrilobaseGUI()
        gui.run()
    ...
```

**제거:**
- `ShowWindow(hwnd, 0)` 블록 (불필요 — 재실행 프로세스는 콘솔이 없음)

## 변경 파일

- `scripts/gui.py`

## 테스트 계획

- `python scripts/gui.py` 실행 → re-spawn 없이 정상 GUI 실행 (frozen=False)
- (Windows) `trilobase.exe` cmd에서 실행 → cmd 즉시 해방, GUI 정상 실행
- (Windows) `trilobase.exe --mcp-stdio` → MCP stdio 정상 동작 확인
