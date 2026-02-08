# Plan: GUI 컨트롤 패널 추가

**날짜:** 2026-02-07
**목표:** 콘솔 대신 간단한 GUI 컨트롤 패널로 서버 제어

## 배경

현재 독립 실행형 앱은 콘솔 창으로 실행된다. 일반 사용자를 위해 다음 기능을 가진 GUI 패널이 필요:
- 현재 데이터베이스 표시
- 서버 시작/중지
- 브라우저 열기
- 상태 표시

## 도구: tkinter

Python 표준 라이브러리 (추가 설치 불필요)

## UI 디자인

```
┌─────────────────────────────────────┐
│  Trilobase SCODA Viewer             │
├─────────────────────────────────────┤
│                                     │
│  Database: trilobase.db             │
│  Status:   ● Running                │
│  URL:      http://localhost:8080    │
│                                     │
│  ┌─────────┐  ┌─────────┐          │
│  │  Start  │  │  Stop   │          │
│  └─────────┘  └─────────┘          │
│                                     │
│  ┌───────────────────────┐          │
│  │  Open in Browser      │          │
│  └───────────────────────┘          │
│                                     │
│  ┌───────────────────────┐          │
│  │       Quit            │          │
│  └───────────────────────┘          │
│                                     │
└─────────────────────────────────────┘
```

## 구현 계획

### 1. `scripts/gui.py` 생성 (신규)

```python
#!/usr/bin/env python3
"""
Trilobase GUI Control Panel

Provides a simple graphical interface to control the Flask server.
"""

import tkinter as tk
from tkinter import ttk
import threading
import webbrowser
import os
import sys


class TrilobaseGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Trilobase SCODA Viewer")
        self.root.geometry("400x300")
        self.root.resizable(False, False)

        self.server_thread = None
        self.server_running = False
        self.port = 8080

        self._create_widgets()
        self._update_status()

    def _create_widgets(self):
        # Header
        header = tk.Label(self.root, text="Trilobase SCODA Viewer",
                         font=("Arial", 14, "bold"))
        header.pack(pady=10)

        # Info frame
        info_frame = tk.Frame(self.root)
        info_frame.pack(pady=10, padx=20, fill="x")

        # Database
        tk.Label(info_frame, text="Database:", anchor="w").grid(row=0, column=0, sticky="w")
        self.db_label = tk.Label(info_frame, text="trilobase.db", anchor="w", fg="blue")
        self.db_label.grid(row=0, column=1, sticky="w", padx=10)

        # Status
        tk.Label(info_frame, text="Status:", anchor="w").grid(row=1, column=0, sticky="w")
        self.status_label = tk.Label(info_frame, text="● Stopped", anchor="w", fg="red")
        self.status_label.grid(row=1, column=1, sticky="w", padx=10)

        # URL
        tk.Label(info_frame, text="URL:", anchor="w").grid(row=2, column=0, sticky="w")
        self.url_label = tk.Label(info_frame, text=f"http://localhost:{self.port}",
                                  anchor="w", fg="gray")
        self.url_label.grid(row=2, column=1, sticky="w", padx=10)

        # Buttons frame
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=20)

        # Start/Stop buttons
        self.start_btn = tk.Button(btn_frame, text="Start", width=10,
                                   command=self.start_server, bg="#4CAF50", fg="white")
        self.start_btn.grid(row=0, column=0, padx=5)

        self.stop_btn = tk.Button(btn_frame, text="Stop", width=10,
                                  command=self.stop_server, state="disabled",
                                  bg="#f44336", fg="white")
        self.stop_btn.grid(row=0, column=1, padx=5)

        # Open browser button
        self.browser_btn = tk.Button(self.root, text="Open in Browser", width=25,
                                     command=self.open_browser, state="disabled")
        self.browser_btn.pack(pady=5)

        # Quit button
        quit_btn = tk.Button(self.root, text="Quit", width=25,
                            command=self.quit_app)
        quit_btn.pack(pady=5)

    def start_server(self):
        """Start Flask server in background thread."""
        if self.server_running:
            return

        self.server_running = True
        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()

        self._update_status()

    def stop_server(self):
        """Stop Flask server."""
        # Flask doesn't have clean shutdown in thread, so we just mark as stopped
        self.server_running = False
        self._update_status()

    def _run_server(self):
        """Run Flask server (called in thread)."""
        try:
            from app import app
            app.run(debug=False, host='127.0.0.1', port=self.port, use_reloader=False)
        except Exception as e:
            print(f"Server error: {e}")
            self.server_running = False
            self._update_status()

    def open_browser(self):
        """Open default browser."""
        webbrowser.open(f'http://localhost:{self.port}')

    def quit_app(self):
        """Quit application."""
        self.root.quit()
        self.root.destroy()
        sys.exit(0)

    def _update_status(self):
        """Update UI based on server status."""
        if self.server_running:
            self.status_label.config(text="● Running", fg="green")
            self.start_btn.config(state="disabled")
            self.stop_btn.config(state="normal")
            self.browser_btn.config(state="normal")
            self.url_label.config(fg="blue")
        else:
            self.status_label.config(text="● Stopped", fg="red")
            self.start_btn.config(state="normal")
            self.stop_btn.config(state="disabled")
            self.browser_btn.config(state="disabled")
            self.url_label.config(fg="gray")

    def run(self):
        """Start GUI main loop."""
        self.root.mainloop()


def main():
    # Change to base directory
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    os.chdir(base_path)

    # Run GUI
    gui = TrilobaseGUI()
    gui.run()


if __name__ == '__main__':
    main()
```

### 2. `trilobase.spec` 수정

GUI 모드로 변경 (콘솔 숨김):

```python
exe = EXE(
    ...
    console=False,  # False로 변경 (GUI 모드)
    ...
)
```

엔트리포인트 변경:

```python
a = Analysis(
    ['scripts/gui.py'],  # serve.py → gui.py
    ...
)
```

### 3. `requirements.txt` — 변경 없음

tkinter는 Python 표준 라이브러리이므로 추가 의존성 없음.

## 기능 명세

| 기능 | 동작 |
|------|------|
| **Start** | Flask 서버를 백그라운드 스레드로 시작 |
| **Stop** | 서버 중지 (스레드 종료) |
| **Open in Browser** | 기본 브라우저로 http://localhost:8080 열기 |
| **Quit** | 앱 종료 (서버도 함께 종료) |
| **Status** | Running(녹색) / Stopped(빨강) 표시 |
| **Database** | 현재 DB 파일명 표시 |

## UI 상태 전환

```
초기 상태:
  Status: ● Stopped (빨강)
  Start: 활성
  Stop: 비활성
  Open in Browser: 비활성

Start 클릭 후:
  Status: ● Running (녹색)
  Start: 비활성
  Stop: 활성
  Open in Browser: 활성
```

## 빌드 및 테스트

```bash
# 빌드 (GUI 모드)
python scripts/build.py

# 실행 (Windows)
.\dist\trilobase.exe
# → 콘솔 창 없이 GUI 창만 표시

# 실행 (Linux/macOS)
./dist/trilobase
# → GUI 창 표시
```

## 향후 개선

- [ ] DB 파일 선택 (파일 다이얼로그)
- [ ] 포트 번호 변경 옵션
- [ ] 로그 뷰어 (콘솔 출력 표시)
- [ ] 시스템 트레이 아이콘
- [ ] 자동 시작 옵션
- [ ] 테마 변경 (다크 모드)

## 제약사항

- tkinter는 크로스 플랫폼이지만 플랫폼별 UI 스타일 차이 존재
- Flask 서버를 스레드로 실행하므로 완전한 종료가 어려움 (프로세스 종료 시 함께 종료)
- 콘솔이 없으므로 에러 메시지 확인 어려움 → 향후 로그 뷰어 추가 필요
