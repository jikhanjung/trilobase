# Phase 19: GUI 컨트롤 패널 완료

**날짜:** 2026-02-07

## 요약

콘솔 창 대신 tkinter 기반 GUI 컨트롤 패널 추가. 일반 사용자 친화적인 인터페이스로 서버 제어.

## 구현 내용

### 1. `scripts/gui.py` — GUI 컨트롤 패널

**주요 기능:**
- ▶ Start Server: Flask 서버를 백그라운드 스레드로 시작
- ■ Stop Server: 서버 중지 (스레드 마킹)
- 🌐 Open in Browser: 기본 브라우저로 http://localhost:8080 열기
- Exit: 앱 종료

**정보 표시:**
- Database: trilobase.db 경로 및 존재 여부
- Status: ● Running (녹색) / ● Stopped (빨강)
- URL: http://localhost:8080 (클릭 가능)

**UI 디자인:**
```
┌──────────────────────────────────┐
│  Trilobase SCODA Viewer   (헤더) │
├──────────────────────────────────┤
│ [Information]                    │
│  Database: trilobase.db          │
│  Status:   ● Running             │
│  URL:      http://localhost:8080 │
├──────────────────────────────────┤
│ [Controls]                       │
│  ▶ Start Server  ■ Stop Server   │
│  🌐 Open in Browser              │
│  Exit                            │
└──────────────────────────────────┘
```

**기능 상세:**

| 상태 | Start 버튼 | Stop 버튼 | Open 버튼 | URL 색상 |
|------|-----------|----------|-----------|---------|
| Stopped | 활성 (녹색) | 비활성 | 비활성 | 회색 |
| Running | 비활성 | 활성 (빨강) | 활성 | 파랑 |

**에러 처리:**
- DB 파일 없음 → 에러 대화상자 + Start 버튼 비활성화
- 포트 충돌 → 에러 대화상자
- Import 실패 → 에러 대화상자
- 종료 시 서버 실행 중 → 확인 대화상자

**자동 기능:**
- 서버 시작 후 1.5초 뒤 자동으로 브라우저 오픈
- 창 닫기(X) → 확인 후 종료

### 2. `trilobase.spec` 수정

**변경 사항:**
```python
# Entry point 변경
a = Analysis(
    ['scripts/gui.py'],  # serve.py → gui.py
    ...
)

# GUI 모드 활성화
exe = EXE(
    ...
    console=False,  # True → False (콘솔 창 숨김)
    ...
)
```

## 사용자 경험

### 실행 (Windows)

```powershell
# 더블클릭 또는
.\trilobase.exe
```

1. GUI 창 표시 (콘솔 없음)
2. "▶ Start Server" 클릭
3. 1.5초 후 브라우저 자동 오픈
4. Trilobase 웹 UI 사용
5. 종료: "Exit" 버튼 또는 창 닫기

### 실행 (Linux/macOS)

```bash
./trilobase
```

동일하게 GUI 창 표시.

## 빌드 결과

```bash
# 빌드
python scripts/build.py --clean

# 결과물
dist/trilobase        # 13.1 MB (Linux)
dist/trilobase.exe    # ~14-15 MB (Windows)
```

## 기술 구현

### tkinter 사용 이유

- Python 표준 라이브러리 (추가 의존성 없음)
- 크로스 플랫폼 (Windows/Linux/macOS)
- 경량 (~수백 KB)
- PyInstaller와 호환

### 서버 제어

```python
# 백그라운드 스레드로 Flask 실행
self.server_thread = threading.Thread(target=self._run_server, daemon=True)
self.server_thread.start()

# Flask 앱 실행
from app import app
app.run(debug=False, host='127.0.0.1', port=8080, use_reloader=False)
```

**주의사항:**
- Flask는 스레드에서 실행 시 clean shutdown 어려움
- Stop 버튼은 상태만 변경 (스레드는 계속 실행)
- 완전한 종료는 앱 재시작 필요

### PyInstaller frozen 모드 대응

```python
if getattr(sys, 'frozen', False):
    # PyInstaller bundle
    base_path = sys._MEIPASS
else:
    # Normal Python
    base_path = os.path.dirname(...)
```

## 제약사항

### 현재 제약

1. **서버 중지 불완전**: Stop 버튼은 UI 상태만 변경 (스레드는 계속 실행)
2. **포트 고정**: 8080 하드코딩
3. **로그 없음**: 콘솔이 없으므로 에러 확인 어려움
4. **tkinter 의존**: WSL 등 GUI 없는 환경에서 실행 불가

### 향후 개선

- [ ] Flask 완전 종료 (werkzeug shutdown)
- [ ] 로그 뷰어 탭 추가
- [ ] 포트 설정 UI
- [ ] DB 파일 선택 (파일 다이얼로그)
- [ ] 시스템 트레이 아이콘
- [ ] 다크 모드 테마

## 테스트

### WSL (Linux)

- ✓ 빌드 성공 (13.1 MB)
- ✗ GUI 테스트 불가 (tkinter 없음)
- → Windows에서 테스트 필요

### Windows (테스트 필요)

- [ ] GUI 창 표시
- [ ] Start 버튼 → 서버 시작
- [ ] 브라우저 자동 오픈
- [ ] Open in Browser 버튼
- [ ] Stop 버튼
- [ ] Exit 버튼
- [ ] DB 없을 때 에러 처리

## 수정 파일

| 파일 | 변경 | 신규/수정 |
|------|------|----------|
| `scripts/gui.py` | GUI 컨트롤 패널 | 신규 |
| `trilobase.spec` | Entry point + console mode | 수정 |

## Windows 테스트 방법

```powershell
# 1. 최신 코드 pull
git pull origin feature/scoda-implementation

# 2. 빌드
python scripts\build.py --clean

# 3. 실행 테스트
.\dist\trilobase.exe

# 4. 확인 사항
# - GUI 창 표시 (콘솔 창 없음)
# - Start 버튼 클릭 → 브라우저 오픈
# - 웹 UI 정상 작동
# - Exit 버튼 → 앱 종료
```

## 다음 단계

1. Windows 빌드 및 테스트
2. 사용자 가이드 업데이트 (README.md)
3. 스크린샷 추가 (GUI 캡처)
4. 릴리스 패키징 (Phase 16 연계)
