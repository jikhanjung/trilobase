# 작업 로그 027: GUI 콘솔 독립 실행 (DETACHED_PROCESS)

**작업일:** 2026-02-10
**브랜치:** `feature/scoda-implementation`
**계획 문서:** `devlog/20260210_P19_gui_console_detach.md`

## 문제

cmd.exe에서 `trilobase.exe` 실행 시 콘솔 창이 최소화된 채 대기 상태에 머묾.
GUI를 닫을 때까지 cmd.exe가 블로킹됨.

## 원인

Phase 25에서 `--mcp-stdio` 지원을 위해 `console=True`로 변경.
Windows는 Console subsystem 앱을 cmd.exe에서 실행하면 프로세스 종료까지 대기.
기존 `ShowWindow(hwnd, 0)` 코드는 콘솔 창을 숨기기만 할 뿐, cmd.exe 블로킹 해제 불가.

## 변경 내용

**파일:** `scripts/gui.py`

### 추가: `--gui-detached` 숨겨진 플래그

```python
parser.add_argument('--gui-detached', action='store_true', help=argparse.SUPPRESS)
```

재실행 루프 방지용 내부 플래그. 사용자에게 `--help`에 표시되지 않음.

### 변경: GUI 모드 블록

**이전:**
```python
# GUI mode: hide console window on Windows when frozen
if getattr(sys, 'frozen', False) and sys.platform == 'win32':
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
```

**이후:**
```python
# GUI mode: re-spawn as DETACHED_PROCESS on Windows (frozen) to free the console.
if getattr(sys, 'frozen', False) and sys.platform == 'win32' and not args.gui_detached:
    DETACHED_PROCESS = 0x00000008
    subprocess.Popen(
        [sys.executable, '--gui-detached'],
        creationflags=DETACHED_PROCESS,
        close_fds=True
    )
    sys.exit(0)
```

## 실행 흐름

```
[cmd.exe]  trilobase.exe
               ↓
       [원본 프로세스]
       frozen=True, win32, not detached
               ↓ re-spawn(DETACHED_PROCESS)
       sys.exit(0)  ←── cmd.exe 즉시 해방
               ↓
    [재실행 프로세스] (--gui-detached)
    frozen=True, win32, detached=True → 조건 미충족 → GUI 실행
```

## 시나리오별 동작

| 실행 방법 | 동작 |
|----------|------|
| cmd.exe에서 `trilobase.exe` | 원본 즉시 종료 → cmd.exe 해방 → 재실행 프로세스가 GUI 실행 |
| 더블클릭 | 원본 즉시 종료 → 콘솔 창 닫힘 → 재실행 프로세스가 콘솔 없이 GUI 실행 |
| `trilobase.exe --mcp-stdio` | re-spawn 로직 건너뜀 (영향 없음) |
| `python scripts/gui.py` | frozen=False → re-spawn 건너뜀 (영향 없음) |

## 테스트

- `ast.parse()` 문법 검사 통과
- `ShowWindow` 코드 완전 제거 확인
- `DETACHED_PROCESS`, `--gui-detached` 정상 삽입 확인
