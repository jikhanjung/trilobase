# Plan: GUI 로그 뷰어 추가 (Phase 21)

**날짜:** 2026-02-08
**목표:** GUI 컨트롤 패널에 Flask 서버 로그 실시간 표시 기능 추가

## 배경

**문제:**
- Windows GUI 실행 시 콘솔이 숨겨져 있음 (`console=False`)
- Flask 서버 에러 발생 시 사용자가 확인할 방법이 없음
- 디버깅 및 문제 해결 불가

**요구사항:**
- GUI 내에서 Flask 서버 로그를 실시간으로 확인
- 에러 발생 시 즉시 식별 가능
- 로그 저장 기능 (선택사항)

## GUI 레이아웃 변경

### 현재 (420x320)

```
┌──────────────────────────────────┐
│  Trilobase SCODA Viewer   (헤더) │
├──────────────────────────────────┤
│ [Information]                    │
│  Canonical: trilobase.db         │
│  Overlay:   trilobase_overlay.db │
│  Status:    ● Running            │
│  URL:       http://localhost:8080│
├──────────────────────────────────┤
│ [Controls]                       │
│  ▶ Start  ■ Stop                 │
│  🌐 Open Browser                 │
│  Exit                            │
└──────────────────────────────────┘
```

### 변경 후 (800x600)

```
┌────────────────────────────────────────────────────────────┐
│  Trilobase SCODA Viewer                           (헤더)   │
├────────────────────────────────────────────────────────────┤
│ [Information]                      [Controls]              │
│  Canonical: trilobase.db            ▶ Start  ■ Stop        │
│  Overlay:   trilobase_overlay.db    🌐 Open Browser        │
│  Status:    ● Running               📄 Clear Log           │
│  URL:       http://localhost:8080   Exit                   │
├────────────────────────────────────────────────────────────┤
│ [Server Log]                                               │
│ ┌────────────────────────────────────────────────────────┐ │
│ │ * Running on http://127.0.0.1:8080                    │ │
│ │ * Restarting with stat                                │ │
│ │ [2026-02-08 14:30:15] INFO: Starting server...        │ │
│ │ [2026-02-08 14:30:20] ERROR: Database connection...   │ │
│ │                                                        │ │
│ │                                                        ↕ │
│ └────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘
```

**레이아웃 상세:**
- 창 크기: 800x600 (기존 420x320에서 확대)
- 상단: 정보 + 컨트롤을 좌우로 배치
- 하단: 로그 뷰어 (전체 폭, 높이 400px)
- 로그 뷰어: Text 위젯 + Scrollbar

## 구현 방법

### 1. Flask 서버 실행 방식 변경

**현재 (`scripts/gui.py:192-206`):**

```python
def _run_server(self):
    """Run Flask server (called in thread)."""
    try:
        self.flask_app.run(debug=False, host='127.0.0.1', port=self.port, use_reloader=False)
    except OSError as e:
        # ...
```

**문제:** `flask_app.run()`의 stdout/stderr을 캡처할 수 없음.

**변경:**

```python
import subprocess
import sys
import threading
import queue

def _run_server(self):
    """Run Flask server as subprocess with log capture."""
    try:
        # Flask를 별도 프로세스로 실행
        python_exe = sys.executable
        app_py = os.path.join(self.base_path, 'app.py')

        self.server_process = subprocess.Popen(
            [python_exe, app_py],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # stderr도 stdout으로 리다이렉트
            universal_newlines=True,
            bufsize=1  # 라인 버퍼링
        )

        # 로그 읽기 스레드 시작
        self.log_reader_thread = threading.Thread(
            target=self._read_server_logs,
            daemon=True
        )
        self.log_reader_thread.start()

    except Exception as e:
        self.server_running = False
        # ...
```

### 2. 로그 읽기 스레드

```python
def _read_server_logs(self):
    """Read server logs from subprocess and display in GUI."""
    while self.server_running and self.server_process:
        try:
            line = self.server_process.stdout.readline()
            if line:
                # GUI 업데이트는 메인 스레드에서 실행
                self.root.after(0, self._append_log, line.strip())
            else:
                # EOF 또는 프로세스 종료
                break
        except Exception as e:
            print(f"Log reader error: {e}")
            break
```

### 3. 로그 표시 위젯

```python
def _create_log_viewer(self, parent):
    """Create log viewer widget."""
    log_frame = tk.LabelFrame(parent, text="Server Log", padx=5, pady=5)
    log_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))

    # Scrollbar
    scrollbar = tk.Scrollbar(log_frame)
    scrollbar.pack(side="right", fill="y")

    # Text widget (read-only)
    self.log_text = tk.Text(
        log_frame,
        wrap="word",
        yscrollcommand=scrollbar.set,
        state="disabled",  # 읽기 전용
        height=20,
        font=("Courier", 9),
        bg="#f5f5f5",
        fg="#333333"
    )
    self.log_text.pack(side="left", fill="both", expand=True)
    scrollbar.config(command=self.log_text.yview)

    # 색상 태그 정의
    self.log_text.tag_config("ERROR", foreground="red")
    self.log_text.tag_config("WARNING", foreground="orange")
    self.log_text.tag_config("INFO", foreground="blue")
    self.log_text.tag_config("SUCCESS", foreground="green")
```

### 4. 로그 추가 함수

```python
def _append_log(self, line):
    """Append log line to text widget (called from main thread)."""
    self.log_text.config(state="normal")  # 쓰기 가능

    # 에러 감지 및 색상 지정
    tag = None
    if "ERROR" in line or "error" in line.lower() or "Exception" in line:
        tag = "ERROR"
    elif "WARNING" in line or "warning" in line.lower():
        tag = "WARNING"
    elif "INFO" in line or "Running on" in line:
        tag = "INFO"
    elif "200 GET" in line or "200 POST" in line:
        tag = "SUCCESS"

    # 타임스탬프 추가
    timestamp = time.strftime("[%H:%M:%S] ")

    if tag:
        self.log_text.insert("end", timestamp + line + "\n", tag)
    else:
        self.log_text.insert("end", timestamp + line + "\n")

    # 자동 스크롤 (맨 아래로)
    self.log_text.see("end")

    self.log_text.config(state="disabled")  # 읽기 전용 복원

    # 로그 라인 수 제한 (1000줄 초과 시 상위 500줄 삭제)
    line_count = int(self.log_text.index('end-1c').split('.')[0])
    if line_count > 1000:
        self.log_text.config(state="normal")
        self.log_text.delete('1.0', '500.0')
        self.log_text.config(state="disabled")
```

### 5. Clear Log 버튼

```python
def clear_log(self):
    """Clear log viewer."""
    self.log_text.config(state="normal")
    self.log_text.delete('1.0', 'end')
    self.log_text.config(state="disabled")
```

### 6. 서버 종료 시 프로세스 정리

```python
def stop_server(self):
    """Stop Flask server."""
    if not self.server_running:
        return

    self.server_running = False

    # 서버 프로세스 종료
    if self.server_process:
        self.server_process.terminate()
        try:
            self.server_process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.server_process.kill()
        self.server_process = None

    self._update_status()
    self._append_log("Server stopped by user")
```

## 추가 기능

### 1. 로그 파일 저장 (선택사항)

```python
def save_log(self):
    """Save log to file."""
    from tkinter import filedialog

    file_path = filedialog.asksaveasfilename(
        defaultextension=".log",
        filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")]
    )

    if file_path:
        log_content = self.log_text.get('1.0', 'end')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(log_content)
        messagebox.showinfo("Saved", f"Log saved to:\n{file_path}")
```

### 2. 로그 검색 (선택사항)

```python
def search_log(self):
    """Search in log viewer."""
    search_term = simpledialog.askstring("Search", "Enter search term:")
    if search_term:
        # 이전 검색 하이라이트 제거
        self.log_text.tag_remove("search", "1.0", "end")

        # 검색 및 하이라이트
        idx = "1.0"
        while True:
            idx = self.log_text.search(search_term, idx, nocase=1, stopindex="end")
            if not idx:
                break
            lastidx = f"{idx}+{len(search_term)}c"
            self.log_text.tag_add("search", idx, lastidx)
            idx = lastidx

        # 검색 태그 스타일
        self.log_text.tag_config("search", background="yellow")
```

## 윈도우 크기 및 리사이즈

```python
def __init__(self):
    self.root = tk.Tk()
    self.root.title("Trilobase SCODA Viewer")
    self.root.geometry("800x600")
    self.root.resizable(True, True)  # 리사이즈 허용

    # 최소 크기 설정
    self.root.minsize(600, 400)
```

## 초기 로그 메시지

```python
def __init__(self):
    # ...
    self._create_widgets()
    self._update_status()

    # 초기 로그 메시지
    self._append_log("Trilobase SCODA Viewer initialized")
    self._append_log(f"Canonical DB: {self.canonical_db_path}")
    self._append_log(f"Overlay DB: {self.overlay_db_path}")
    if not self.db_exists:
        self._append_log("WARNING: Canonical database not found!", tag="WARNING")
```

## 에러 처리

### 1. 서버 시작 실패

```python
def start_server(self):
    # ...
    try:
        self.server_process = subprocess.Popen(...)
    except FileNotFoundError:
        self._append_log("ERROR: Python executable not found", tag="ERROR")
        messagebox.showerror("Error", "Could not find Python executable")
        return
    except Exception as e:
        self._append_log(f"ERROR: Failed to start server: {e}", tag="ERROR")
        messagebox.showerror("Server Error", f"Could not start server:\n{e}")
        return
```

### 2. 포트 충돌

로그에서 자동 감지:

```python
def _append_log(self, line):
    # ...
    if "Address already in use" in line:
        self._append_log(f"ERROR: Port {self.port} is already in use!", tag="ERROR")
        messagebox.showerror(
            "Port Error",
            f"Port {self.port} is already in use.\n"
            "Please close other applications using this port."
        )
```

## 테스트 시나리오

1. **정상 시작:**
   - Start Server 클릭
   - 로그에 "Running on http://127.0.0.1:8080" 표시
   - 로그 색상 정상 (INFO = 파랑)

2. **에러 발생:**
   - DB 파일 삭제 후 시작
   - 로그에 빨간색 에러 메시지 표시
   - 사용자가 문제 식별 가능

3. **API 요청:**
   - Open Browser 클릭
   - 로그에 "200 GET /api/tree" 등 초록색으로 표시

4. **Clear Log:**
   - Clear Log 버튼 클릭
   - 로그 화면 초기화

5. **로그 제한:**
   - 1000줄 이상 로그 생성
   - 자동으로 상위 500줄 삭제 확인

## 수정 파일

| 파일 | 변경 | 비고 |
|------|------|------|
| `scripts/gui.py` | 로그 뷰어 추가 | 600줄 → ~800줄 |

## 예상 효과

1. **디버깅 용이성:** 사용자가 에러를 즉시 확인 가능
2. **사용자 경험:** GUI만으로 모든 정보 확인 가능
3. **개발 효율:** Windows 환경에서 디버깅 시간 단축

## 다음 단계

1. `scripts/gui.py` 수정 구현
2. Windows에서 테스트
   - 정상 시작
   - DB 파일 없을 때 에러 표시
   - 포트 충돌 시 에러 표시
3. Linux에서도 테스트 (WSL)
4. devlog 완료 기록 작성
5. HANDOVER.md 업데이트
