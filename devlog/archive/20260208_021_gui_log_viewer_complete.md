# Phase 21: GUI 로그 뷰어 완료

**날짜:** 2026-02-08

## 요약

GUI 컨트롤 패널에 Flask 서버 로그 실시간 표시 기능 추가. Windows 환경에서 콘솔 없이 서버 에러 디버깅 가능.

## 배경

**문제:**
- Windows GUI 실행 시 콘솔 숨김 (`console=False`)
- Flask 서버 에러 발생 시 확인 불가능
- 500 Internal Server Error 발생 시 원인 파악 불가

**해결:**
- GUI 내에 로그 뷰어 추가
- Flask stdout/stderr 실시간 캡처
- 에러 자동 감지 및 색상 표시

## 구현 내용

### 1. GUI 레이아웃 변경

**크기:**
- 420x320 → 800x600
- 리사이즈 가능 (최소 600x400)

**레이아웃:**

```
┌────────────────────────────────────────────────────────────┐
│  Trilobase SCODA Viewer                           (헤더)   │
├────────────────────────────────────────────────────────────┤
│ [Information]                    [Controls]                │
│  Canonical: trilobase.db          ▶ Start  ■ Stop          │
│  Overlay:   trilobase_overlay.db  🌐 Open Browser          │
│  Status:    ● Running             📄 Clear Log             │
│  URL:       localhost:8080        Exit                     │
├────────────────────────────────────────────────────────────┤
│ [Server Log]                                               │
│ ┌────────────────────────────────────────────────────────┐ │
│ │ [14:30:15] Trilobase SCODA Viewer initialized         │ │
│ │ [14:30:15] Canonical DB: trilobase.db                 │ │
│ │ [14:30:15] Overlay DB: trilobase_overlay.db           │ │
│ │ [14:30:16] Starting Flask server...                   │ │
│ │ [14:30:17] * Running on http://127.0.0.1:8080         │ │
│ │ [14:30:20] 127.0.0.1 - - GET /api/tree HTTP/1.1 200   │ │
│ │                                                        ↕ │
│ └────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘
```

### 2. Flask 서버 실행 방식 변경

**이전 (Phase 19):**

```python
# threading.Thread로 Flask 내장 서버 실행
from app import app
self.flask_app = app
self.server_thread = threading.Thread(target=self._run_server, daemon=True)
self.server_thread.start()

def _run_server(self):
    self.flask_app.run(debug=False, host='127.0.0.1', port=self.port)
```

**문제:** stdout/stderr 캡처 불가능

**변경 (Phase 21):**

```python
# subprocess.Popen으로 별도 프로세스 실행
self.server_process = subprocess.Popen(
    [sys.executable, app_py],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,  # stderr도 stdout으로
    universal_newlines=True,
    bufsize=1,  # 라인 버퍼링
    cwd=self.base_path
)

# 로그 읽기 스레드 시작
self.log_reader_thread = threading.Thread(
    target=self._read_server_logs,
    daemon=True
)
self.log_reader_thread.start()
```

### 3. 로그 읽기 스레드

```python
def _read_server_logs(self):
    """Read server logs from subprocess and display in GUI."""
    while self.server_running and self.server_process:
        try:
            line = self.server_process.stdout.readline()
            if line:
                # GUI 업데이트는 메인 스레드에서
                self.root.after(0, self._append_log, line.strip())
            else:
                break  # EOF
        except Exception as e:
            self._append_log(f"Log reader error: {e}", "ERROR")
            break

    # 프로세스 종료 코드 확인
    if self.server_process:
        returncode = self.server_process.poll()
        if returncode is not None and returncode != 0:
            self.root.after(0, self._append_log,
                          f"Server process exited with code {returncode}", "ERROR")
```

### 4. 로그 표시 (_append_log)

```python
def _append_log(self, line, tag=None):
    """Append log line to text widget."""
    self.log_text.config(state="normal")  # 쓰기 가능

    # 자동 레벨 감지
    if tag is None:
        if "ERROR" in line or "Exception" in line:
            tag = "ERROR"
        elif "WARNING" in line:
            tag = "WARNING"
        elif "Running on" in line:
            tag = "INFO"
        elif "200 GET" in line:
            tag = "SUCCESS"
        elif "Address already in use" in line:
            tag = "ERROR"
            # 포트 충돌 알림
            messagebox.showerror("Port Error", ...)

    # 타임스탬프 + 로그
    timestamp = time.strftime("[%H:%M:%S] ")
    if tag:
        self.log_text.insert("end", timestamp + line + "\n", tag)
    else:
        self.log_text.insert("end", timestamp + line + "\n")

    # 자동 스크롤
    self.log_text.see("end")

    self.log_text.config(state="disabled")  # 읽기 전용

    # 로그 크기 제한 (1000줄 초과 시 상위 500줄 삭제)
    line_count = int(self.log_text.index('end-1c').split('.')[0])
    if line_count > 1000:
        self.log_text.config(state="normal")
        self.log_text.delete('1.0', '500.0')
        self.log_text.config(state="disabled")
```

### 5. 로그 뷰어 위젯

```python
# Text 위젯 + Scrollbar
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

# 색상 태그 정의
self.log_text.tag_config("ERROR", foreground="red")
self.log_text.tag_config("WARNING", foreground="orange")
self.log_text.tag_config("INFO", foreground="blue")
self.log_text.tag_config("SUCCESS", foreground="green")
```

### 6. Clear Log 버튼

```python
def clear_log(self):
    """Clear log viewer."""
    self.log_text.config(state="normal")
    self.log_text.delete('1.0', 'end')
    self.log_text.config(state="disabled")
    self._append_log("Log cleared")
```

### 7. 서버 종료 개선

```python
def stop_server(self):
    """Stop Flask server."""
    if not self.server_running:
        return

    self.server_running = False

    if self.server_process:
        self._append_log("Stopping Flask server...", "INFO")
        self.server_process.terminate()
        try:
            self.server_process.wait(timeout=3)
            self._append_log("Server stopped successfully", "INFO")
        except subprocess.TimeoutExpired:
            self._append_log("Server did not stop gracefully, forcing...", "WARNING")
            self.server_process.kill()
            self.server_process.wait()
            self._append_log("Server forcefully stopped", "WARNING")
        self.server_process = None

    self._update_status()
```

**개선점:**
- Phase 19: "Server marked as stopped" 메시지만 표시 (프로세스는 계속 실행)
- Phase 21: 실제로 프로세스 종료 (terminate → kill)

### 8. 초기 로그 메시지

```python
# __init__ 마지막에 추가
self._append_log("Trilobase SCODA Viewer initialized")
self._append_log(f"Canonical DB: {os.path.basename(self.canonical_db_path)}")
self._append_log(f"Overlay DB: {os.path.basename(self.overlay_db_path)}")
if not self.db_exists:
    self._append_log("WARNING: Canonical database not found!", "WARNING")
```

## 색상 코드

| 태그 | 색상 | 용도 |
|------|------|------|
| ERROR | 빨강 | 에러, Exception, Traceback |
| WARNING | 주황 | 경고, 비정상 종료 |
| INFO | 파랑 | 서버 시작, 일반 정보 |
| SUCCESS | 초록 | 200 OK, 정상 요청 |
| (기본) | 검정 | 기타 로그 |

## 자동 에러 감지

### 1. 포트 충돌

로그에서 "Address already in use" 감지 시:
- 빨간색으로 표시
- 에러 대화상자 자동 표시

### 2. DB 없음

서버 시작 전 확인:
- Canonical DB 없음 → 에러 대화상자 + 로그 기록
- Start 버튼 비활성화

### 3. 프로세스 비정상 종료

returncode != 0 감지 시:
- 로그에 빨간색으로 exit code 표시

## 코드 통계

**scripts/gui.py 변경:**
- 이전: ~270줄
- 이후: ~400줄
- 추가: ~130줄

**주요 변경:**
- `__init__`: server_process, log_reader_thread 추가
- `_create_widgets`: 레이아웃 완전 재구성
- `start_server`: subprocess.Popen 사용
- `stop_server`: 프로세스 종료 로직 추가
- `_run_server` → `_read_server_logs`: 메서드 교체
- `_append_log`: 신규 추가 (로그 표시)
- `clear_log`: 신규 추가
- `quit_app`: 프로세스 정리 추가

## 테스트 (Windows 필요)

### 정상 시나리오

1. **서버 시작:**
   - Start 버튼 클릭
   - 로그: "Starting Flask server..." (파랑)
   - 로그: "* Running on http://127.0.0.1:8080" (파랑)
   - 브라우저 자동 오픈
   - 상태: ● Running (초록)

2. **API 요청:**
   - 웹 페이지 로드
   - 로그: "GET /api/tree HTTP/1.1 200" (초록)
   - 로그: "GET /api/manifest HTTP/1.1 200" (초록)

3. **서버 중지:**
   - Stop 버튼 클릭
   - 로그: "Stopping Flask server..." (파랑)
   - 로그: "Server stopped successfully" (파랑)

4. **로그 정리:**
   - Clear Log 버튼 클릭
   - 로그 화면 초기화
   - 로그: "Log cleared"

### 에러 시나리오

1. **DB 없음:**
   - trilobase.db 삭제
   - Start 버튼 클릭
   - 로그: "ERROR: Canonical database not found!" (빨강)
   - 에러 대화상자 표시

2. **포트 충돌:**
   - 8080 포트 이미 사용 중
   - Start 버튼 클릭
   - 로그: "ERROR: Address already in use" (빨강)
   - 에러 대화상자 표시

3. **Import 에러:**
   - app.py 삭제 또는 손상
   - 로그: "ERROR: app.py not found" (빨강)

4. **런타임 에러:**
   - DB 쿼리 실패 등
   - 로그에 Traceback 표시 (빨강)
   - 사용자가 즉시 식별 가능

## 예상 효과

### 1. 디버깅 용이성

**이전 (Phase 19):**
- 500 에러 발생 → 원인 불명
- WSL 터미널에서 `python app.py` 수동 실행 필요

**이후 (Phase 21):**
- 500 에러 발생 → 로그 창에 즉시 표시
- GUI만으로 모든 진단 가능

### 2. 사용자 경험

- 전문가가 아닌 사용자도 문제 파악 가능
- "빨간 글씨 = 에러" 직관적 이해
- 에러 메시지 복사 → 이슈 리포트 간편

### 3. 개발 효율

- Windows 환경에서 디버깅 시간 50% 단축
- 로그 저장 기능 (향후) 추가 시 버그 리포트 품질 향상

## 제약사항

### 현재 미구현

- [ ] 로그 파일 저장 기능
- [ ] 로그 검색 기능
- [ ] 로그 필터 (레벨별 표시/숨김)

### 알려진 이슈

1. **로그 인코딩:** Windows에서 한글 로그 깨질 수 있음 (universal_newlines=True로 완화)
2. **로그 버퍼링:** Flask의 일부 로그가 지연 표시될 수 있음 (bufsize=1로 완화)

## 다음 단계

1. **Windows 테스트:** 사용자가 실제 환경에서 검증
2. **에러 수정:** 발견된 버그 수정
3. **빌드:** PyInstaller로 새 실행 파일 생성
4. **배포:** Phase 20 + Phase 21 통합 릴리스

## 수정 파일

| 파일 | 변경 | 라인 수 |
|------|------|---------|
| `scripts/gui.py` | 로그 뷰어 추가 | +130 |
| `devlog/20260208_P13_gui_log_viewer.md` | 계획 문서 | 신규 |
| `devlog/20260208_021_gui_log_viewer_complete.md` | 완료 로그 | 신규 |
