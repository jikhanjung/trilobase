# Phase 23: MCP Server SSE Integration - Planning Document

**작성일:** 2026-02-10
**상태:** 📋 Planning
**이전 Phase:** Phase 22 (MCP Server - stdio 모드)
**브랜치:** `feature/scoda-implementation`

---

## 1. 목표

MCP 서버를 GUI에 통합하여 **SSE (Server-Sent Events) 모드**로 실행, Trilobase 실행 시 Flask + MCP 서버가 동시에 자동 실행되도록 개선.

**핵심 문제:**
- 현재 MCP 서버는 stdio 모드만 지원 → Claude Desktop이 매번 프로세스 spawn 필요
- 매 세션마다 DB 연결 초기화 → 시작 지연
- GUI에서 "미리 실행" 불가능

**해결책:**
- SSE 모드 추가: HTTP 서버로 실행 (http://localhost:8081)
- GUI 시작 시 Flask(8080) + MCP(8081) 동시 실행
- DB 연결 유지 → 빠른 응답

---

## 2. 현재 상태 분석

### 2.1 현재 MCP 서버 (`mcp_server.py`)

- **통신 방식:** stdio only (JSON-RPC over stdin/stdout)
- **실행 방법:** `python mcp_server.py`
- **Claude Desktop 설정:**
  ```json
  {
    "mcpServers": {
      "trilobase": {
        "command": "python",
        "args": ["/path/to/mcp_server.py"]
      }
    }
  }
  ```

### 2.2 현재 GUI (`scripts/gui.py`)

- **실행 서버:** Flask만 (8080 포트)
- **모드:**
  - Frozen (PyInstaller): threading 모드
  - Dev: subprocess 모드
- **DB:** Canonical + Overlay (ATTACH)

---

## 3. 작업 범위

### 3.1 MCP 서버 수정 (`mcp_server.py`)

**현재:**
```python
async with stdio_server() as (read_stream, write_stream):
    await app.run(read_stream, write_stream, app.create_initialization_options())
```

**추가할 기능:**
1. **SSE 모드 지원:**
   ```python
   # 명령줄 인자: --mode sse --port 8081
   if args.mode == 'sse':
       run_sse_server(port=args.port)
   else:
       run_stdio_server()
   ```

2. **HTTP 엔드포인트:**
   - `GET /sse` - SSE 연결
   - `POST /message` - MCP 메시지 전송
   - `GET /health` - 헬스체크

3. **DB 연결 관리:**
   - SSE 모드: 서버 시작 시 DB 연결, 유지
   - stdio 모드: 기존과 동일 (요청마다 연결)

### 3.2 GUI 수정 (`scripts/gui.py`)

**추가 기능:**

1. **MCP 서버 시작/중지:**
   ```python
   def start_mcp_server():
       # frozen: threading으로 SSE 서버 실행
       # dev: subprocess로 실행
       pass

   def stop_mcp_server():
       pass
   ```

2. **GUI 레이아웃 업데이트:**
   ```
   ┌─ Server Status ──────────────┐
   │ Flask:  ● Running (8080)     │
   │ MCP:    ● Running (8081)     │
   │ Canonical DB: trilobase.db   │
   │ Overlay DB: overlay.db       │
   └──────────────────────────────┘

   [▶ Start Servers] [⏹ Stop Servers] [🌐 Open Browser]
   ```

3. **로그 통합:**
   - Flask 로그: 파란색
   - MCP 로그: 보라색
   - 하나의 로그 뷰어에 통합 표시

### 3.3 Claude Desktop 설정 변경

**기존 (stdio):**
```json
{
  "mcpServers": {
    "trilobase": {
      "command": "python",
      "args": ["/path/to/mcp_server.py"]
    }
  }
}
```

**신규 (SSE):**
```json
{
  "mcpServers": {
    "trilobase": {
      "url": "http://localhost:8081"
    }
  }
}
```

### 3.4 PyInstaller 번들 업데이트

**trilobase.spec:**
```python
datas=[
    ('app.py', '.'),
    ('mcp_server.py', '.'),  # ← 추가
    ('templates', 'templates'),
    ('static', 'static'),
    ('trilobase.db', '.'),
],
hiddenimports=[
    'flask',
    'mcp',           # ← 추가
    'sqlite3',
    # ...
],
```

---

## 4. 구현 계획

### 4.1 Phase 1: MCP SSE 모드 구현

**파일:** `mcp_server.py`

1. argparse 추가:
   ```python
   parser.add_argument('--mode', choices=['stdio', 'sse'], default='stdio')
   parser.add_argument('--port', type=int, default=8081)
   parser.add_argument('--host', default='localhost')
   ```

2. SSE 서버 구현:
   ```python
   from aiohttp import web

   async def sse_handler(request):
       # SSE 연결 유지
       pass

   async def message_handler(request):
       # MCP 메시지 처리
       pass

   def run_sse_server(host, port):
       app = web.Application()
       app.router.add_get('/sse', sse_handler)
       app.router.add_post('/message', message_handler)
       app.router.add_get('/health', health_handler)
       web.run_app(app, host=host, port=port)
   ```

3. DB 연결 싱글톤:
   ```python
   class MCPDatabase:
       _instance = None

       @classmethod
       def get_instance(cls):
           if cls._instance is None:
               cls._instance = cls()
           return cls._instance
   ```

**예상 코드 추가량:** +200 lines

### 4.2 Phase 2: GUI 통합

**파일:** `scripts/gui.py`

1. MCP 서버 스레드 추가:
   ```python
   self.mcp_thread = None
   self.mcp_running = False
   self.mcp_port = 8081
   ```

2. 시작/중지 함수:
   ```python
   def start_mcp_server(self):
       if getattr(sys, 'frozen', False):
           # Threading mode
           self.mcp_thread = threading.Thread(
               target=run_mcp_sse, args=(self.mcp_port,)
           )
           self.mcp_thread.start()
       else:
           # Subprocess mode
           self.mcp_process = subprocess.Popen([
               sys.executable, 'mcp_server.py',
               '--mode', 'sse', '--port', str(self.mcp_port)
           ])
   ```

3. GUI 레이아웃:
   - 서버 상태 라벨 2개 (Flask, MCP)
   - "Start All" / "Stop All" 버튼

**예상 코드 추가량:** +150 lines

### 4.3 Phase 3: 테스트

1. **MCP SSE 모드 테스트:**
   ```bash
   python mcp_server.py --mode sse --port 8081
   curl http://localhost:8081/health
   ```

2. **GUI 통합 테스트:**
   ```bash
   python scripts/gui.py
   # "Start All" 클릭 → Flask + MCP 둘 다 실행 확인
   ```

3. **Claude Desktop 연결 테스트:**
   - 설정 파일 수정
   - Claude Desktop 재시작
   - "중국에서 발견된 삼엽충 속은?" 쿼리 테스트

4. **PyInstaller 빌드 테스트:**
   ```bash
   python scripts/build.py --platform linux
   ./dist/trilobase  # 실행 확인
   ```

### 4.4 Phase 4: 문서화

1. **HANDOVER.md 업데이트:**
   - Phase 23 완료 기록
   - MCP SSE 모드 설명

2. **README.md 업데이트:**
   - Claude Desktop 설정 (SSE 모드)
   - GUI에서 MCP 서버 시작 방법

3. **완료 로그 작성:**
   - `devlog/20260210_023_phase23_mcp_sse_integration.md`

---

## 5. 의존성

### 5.1 신규 의존성

**aiohttp** (MCP SSE 서버용):
```bash
pip install aiohttp
```

**requirements.txt 업데이트:**
```
flask
pyinstaller
mcp>=1.0.0
aiohttp       # ← 추가
pytest
pytest-asyncio
```

### 5.2 MCP SDK SSE 지원 확인

MCP Python SDK가 SSE 모드를 지원하는지 확인 필요:
- 공식 문서: https://modelcontextprotocol.io/docs/concepts/transports
- SSE transport 예제 확인

**대안:** 만약 MCP SDK가 SSE를 지원하지 않으면, 수동으로 SSE 프로토콜 구현 필요.

---

## 6. 리스크 및 고려사항

### 6.1 리스크

1. **MCP SDK SSE 미지원:**
   - 완화: 수동 SSE 구현 (JSON-RPC over SSE)
   - 예상 작업량: +300 lines

2. **PyInstaller frozen 모드에서 threading 충돌:**
   - 완화: Flask와 동일한 패턴 사용 (이미 검증됨)

3. **포트 충돌 (8081이 이미 사용 중):**
   - 완화: 설정 파일로 포트 변경 가능하도록

### 6.2 고려사항

1. **stdio 모드 유지 여부:**
   - ✅ 둘 다 유지: `--mode stdio|sse`
   - 이유: 일부 사용자는 stdio를 선호할 수도

2. **보안:**
   - SSE 서버는 localhost만 바인딩 (외부 접근 차단)
   - 인증 불필요 (로컬 전용)

3. **성능:**
   - DB 연결 풀링 고려 (SQLite는 단일 연결로 충분)
   - SSE keep-alive 설정

---

## 7. 성공 기준

- ✅ `mcp_server.py --mode sse` 실행 시 HTTP 서버 시작
- ✅ GUI 시작 시 Flask + MCP 자동 실행
- ✅ Claude Desktop에서 `http://localhost:8081`로 연결 성공
- ✅ 자연어 쿼리 정상 작동 ("중국에서 발견된 삼엽충 속은?")
- ✅ PyInstaller 빌드 정상 작동
- ✅ 모든 기존 테스트 통과 (test_app.py, test_mcp.py)
- ✅ 문서 3종 세트 업데이트 (HANDOVER, README, 완료 로그)

---

## 8. 예상 일정

| Phase | 작업 | 예상 시간 |
|-------|------|----------|
| Phase 1 | MCP SSE 모드 구현 | 2-3시간 |
| Phase 2 | GUI 통합 | 1-2시간 |
| Phase 3 | 테스트 | 1시간 |
| Phase 4 | 문서화 | 30분 |
| **총계** | | **4-6.5시간** |

---

## 9. 참고 자료

- **MCP 프로토콜 - Transports:** https://modelcontextprotocol.io/docs/concepts/transports
- **MCP Python SDK - SSE:** https://github.com/modelcontextprotocol/python-sdk
- **SSE 프로토콜:** https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events
- **aiohttp 문서:** https://docs.aiohttp.org/

---

## 10. 다음 단계

1. ✅ 계획 문서 작성 (이 문서)
2. ⏳ MCP SDK SSE 지원 확인
3. ⏳ SSE 모드 구현
4. ⏳ GUI 통합
5. ⏳ 테스트 및 검증
6. ⏳ 문서화 및 커밋

---

**작성자:** Claude Sonnet 4.5
**검토 필요:** MCP SDK SSE transport 지원 여부
