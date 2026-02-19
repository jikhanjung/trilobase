# MCP 테스트 asyncio 호환성 수정

**날짜:** 2026-02-10

## 문제

`pip install mcp pytest-asyncio` 후 MCP 테스트 실행 시 에러 발생:

```
16 passed, 16 errors
RuntimeError: Attempted to exit cancel scope in a different task than it was entered in
```

모든 테스트 로직은 통과하지만 **teardown 단계에서 에러** 발생.

## 원인 분석

**환경:**
- anyio 4.x
- pytest-asyncio 1.3.0
- mcp 1.3.0

**근본 원인:**

기존 `test_mcp.py`의 `mcp_session` fixture가 `@pytest_asyncio.fixture` 방식을 사용:

```python
@pytest_asyncio.fixture
async def mcp_session():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session  # ← teardown이 다른 task에서 실행
```

anyio 4.x의 `CancelScope`는 **생성된 task와 동일한 task에서만 `__exit__`** 가 호출되어야 합니다. pytest-asyncio가 fixture teardown을 다른 task에서 실행하면서 충돌 발생.

## 해결

### 1. `pytest.ini` 신규 생성

```ini
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
```

- `asyncio_mode = auto`: `@pytest.mark.asyncio` 없이도 async 테스트 자동 인식
- `asyncio_default_fixture_loop_scope = function`: 각 테스트마다 독립 이벤트 루프

→ `test_mcp_basic.py`의 `async def test_mcp_server()` 통과 (기존: "async def functions are not natively supported")

### 2. `conftest.py` 신규 생성

```python
import pytest

@pytest.fixture
def anyio_backend():
    return 'asyncio'
```

anyio 백엔드를 asyncio로 명시.

### 3. `test_mcp.py` fixture 방식 변경 (핵심 수정)

**변경 전**: `@pytest_asyncio.fixture` — teardown이 다른 task에서 실행

```python
@pytest_asyncio.fixture
async def mcp_session():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session

@pytest.mark.asyncio
async def test_list_tools(mcp_session):
    result = await mcp_session.list_tools()
    ...
```

**변경 후**: `@asynccontextmanager` — 각 테스트 내에서 동일 task로 세션 생성/정리

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def create_session():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session

@pytest.mark.asyncio
async def test_list_tools():
    async with create_session() as session:
        result = await session.list_tools()
        ...
```

**효과**: cancel scope의 생성과 소멸이 동일 task에서 이루어지므로 오류 없음.

## 결과

```
118 passed in 50.29s
```

| 파일 | 이전 | 이후 |
|------|------|------|
| `test_app.py` | 101 passed | 101 passed |
| `test_mcp_basic.py` | ERROR (수집 실패) | 1 passed |
| `test_mcp.py` | 16 passed + 16 errors | 16 passed |
| **합계** | - | **118 passed** |

## 수정 파일

| 파일 | 변경 | 신규/수정 |
|------|------|----------|
| `pytest.ini` | asyncio 설정 | 신규 |
| `conftest.py` | anyio 백엔드 설정 | 신규 |
| `test_mcp.py` | fixture → asynccontextmanager | 수정 |
