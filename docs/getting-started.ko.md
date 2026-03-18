# 시작하기

Trilobase는 세 가지 방법으로 사용할 수 있습니다: 독립 실행 파일, Python 소스, 또는 LLM 연동을 위한 MCP 서버.

---

## 옵션 1: 독립 실행 파일 (권장)

가장 간단한 사용 방법. Python 설치가 필요 없습니다.

1. [릴리스 페이지](https://github.com/jikhanjung/trilobase/releases)에서 `trilobase.exe` (Windows) 또는 `trilobase` (Linux) 다운로드
2. 실행 파일 실행
3. GUI 컨트롤 패널에서 **"▶ Start Server"** 클릭
4. 웹 브라우저가 자동으로 `http://localhost:8080` 표시

모든 데이터와 웹 서버가 단일 파일에 포함됩니다. 사용자 주석은 `trilobita_overlay.db`에 별도 저장되어 업데이트 시에도 보존됩니다.

---

## 옵션 2: Python 개발 모드

개발자 또는 소스 코드 수정이 필요한 사용자를 위한 방법.

### 요구사항

- Python 3.8+
- [scoda-engine](https://github.com/jikhanjung/scoda-engine) (런타임)

### 설치

```bash
git clone https://github.com/jikhanjung/trilobase.git
cd trilobase
pip install -e /path/to/scoda-engine[dev]
```

### 웹 서버 실행

```bash
python -m scoda_engine.serve trilobita.scoda
```

브라우저에서 `http://localhost:8080` 접속.

### 테스트 실행

```bash
pytest tests/
```

---

## 옵션 3: MCP 서버 (LLM 연동)

Trilobase는 **Model Context Protocol (MCP)** 서버를 내장하고 있어, Claude나 다른 LLM이 자연어로 삼엽충 데이터베이스를 질의할 수 있습니다.

### 방법 A: 실행 파일 사용 (권장)

Claude Desktop 설정 파일(`claude_desktop_config.json`)에 추가:

```json
{
  "mcpServers": {
    "trilobase": {
      "command": "C:\\path\\to\\trilobase_mcp.exe"
    }
  }
}
```

### 방법 B: Python 소스 사용

```bash
pip install mcp starlette uvicorn
```

```json
{
  "mcpServers": {
    "trilobase": {
      "command": "python",
      "args": ["/absolute/path/to/trilobase/mcp_server.py"],
      "cwd": "/absolute/path/to/trilobase"
    }
  }
}
```

설정 변경 후 Claude Desktop을 재시작하세요.

### 질의 예시

연결 후 Claude에게 다음과 같이 질문할 수 있습니다:

- "중국에서 발견된 삼엽충 속을 보여줘"
- "Paradoxides의 동의어를 알려줘"
- "Family Paradoxididae에 속한 속들을 나열해줘"
- "이 데이터베이스의 출처는?"
- "Agnostus에 메모 추가: 'Check formation data'"

---

## 직접 SQL 접근

SQLite로 데이터베이스를 직접 질의할 수도 있습니다:

```bash
sqlite3 db/trilobita.db "SELECT name, author, year FROM taxonomic_ranks WHERE rank='Genus' AND is_valid=1 LIMIT 10;"
```

교차 데이터베이스 질의(지리/층서 데이터)는 PaleoCore를 먼저 연결하세요:

```sql
ATTACH DATABASE 'db/paleocore.db' AS pc;

SELECT g.name, c.name AS country
FROM taxonomic_ranks g
JOIN genus_locations gl ON g.id = gl.genus_id
JOIN pc.countries c ON gl.country_id = c.id
WHERE g.name = 'Paradoxides';
```
