# Review: 배포 형식 및 사용법

**날짜:** 2026-02-07
**대상:** Trilobase SCODA 구현 배포 전략

## 배경

Trilobase는 Flask 웹 앱으로 구현되어 있다. 일반 사용자에게 배포할 때 어떤 형식이 적합한가?

- 연구자/전문가 vs 일반 사용자
- Python 설치 여부
- 플랫폼 독립성
- SCODA 공통 런너로의 확장 가능성

## 배포 형식 옵션

### 1. 독립 실행형 앱 (PyInstaller/Nuitka)

단일 실행 파일로 패키징:

```
trilobase-v1.0.0/
├── trilobase(.exe)      # 단일 실행 파일
├── trilobase.db         # 데이터베이스
├── metadata.json
└── README.md
```

**실행:**
```bash
./trilobase        # → 자동으로 웹서버 시작 + 브라우저 오픈
```

| 장점 | 단점 |
|------|------|
| Python 설치 불필요 | 빌드 복잡도 높음 |
| 더블클릭 실행 가능 | 플랫폼별 빌드 필요 (Windows/Mac/Linux) |
| 일반 사용자 친화적 | 용량 큼 (50MB+) |

### 2. Python 패키지 (pip install)

PyPI 배포 또는 wheel 파일:

```bash
pip install trilobase-1.0.0.whl
trilobase serve releases/trilobase-v1.0.0/
```

| 장점 | 단점 |
|------|------|
| Python 생태계 표준 | Python 설치 필요 |
| 가벼움 | 비개발자에게 진입장벽 |
| 업데이트 쉬움 | CLI 익숙하지 않은 사용자에게 어려움 |

### 3. Docker 이미지

컨테이너 기반 배포:

```bash
docker run -p 8080:8080 \
  -v ./my_overlay.json:/overlay.json \
  trilobase:1.0.0
```

| 장점 | 단점 |
|------|------|
| 환경 독립적 | Docker 설치 필요 |
| SCODA runner로 확장 가능 | 일반 사용자에겐 낯섦 |
| 재현성 보장 | 초기 학습 곡선 |

### 4. 하이브리드: 런처 스크립트 + Python 백엔드

간단한 배치/셸 스크립트로 래핑:

```
trilobase-v1.0.0/
├── trilobase.bat/.sh    # 런처 스크립트
├── app/
│   ├── app.py
│   ├── static/
│   └── templates/
├── trilobase.db
└── README.md
```

**런처 예시 (`trilobase.bat`):**
```batch
@echo off
cd /d %~dp0
start http://localhost:8080
python app/app.py
```

| 장점 | 단점 |
|------|------|
| 구현 간단 | Python 설치 필요 |
| Python만 있으면 실행 가능 | Python 버전 체크 필요 |
| 플랫폼 독립적 (스크립트만 분리) | 에러 처리 제한적 |

## 단계적 배포 전략

### Phase 1: Python 패키지 (현재 ~ 첫 릴리스)

**대상:** 연구자, 개발자, 분류학 전문가

**형식:**
```bash
pip install trilobase
trilobase serve releases/trilobase-v1.0.0/
```

**구현:**
- `scripts/serve.py` 추가 (간단한 CLI 런처)
- `setup.py` 또는 `pyproject.toml` 작성
- PyPI 배포 (optional)

**장점:**
- 즉시 구현 가능
- 초기 사용자(연구자)는 Python에 익숙함
- 피드백 수집에 적합

### Phase 2: 독립 실행형 앱 (일반 배포)

**대상:** 일반 사용자, 교육용, 박물관 키오스크

**형식:**
```
trilobase-v1.0.0-windows.exe
trilobase-v1.0.0-macos
trilobase-v1.0.0-linux
```

**도구:** PyInstaller 또는 Nuitka

**장점:**
- 일반 사용자 접근성 극대화
- 설치 과정 단순화

**시점:** 첫 stable 릴리스 (v1.0.0) 이후

### Phase 3: SCODA 공통 Runner (장기)

**비전:** 여러 SCODA 아티팩트를 하나의 뷰어로

```bash
scoda-viewer open trilobase-v1.0.0/
scoda-viewer open fossil-plants-v2.1.0/
scoda-viewer open marine-invertebrates-v1.5.0/
```

**구조:**
- SCODA manifest 파싱
- 범용 UI 렌더러
- 플러그인 시스템 (도메인별 커스터마이징)

**장점:**
- SCODA 생태계 구축
- 사용자는 하나의 도구로 여러 데이터셋 탐색
- 커뮤니티 기여 확대

## 즉시 적용 가능한 구현

### `scripts/serve.py` (신규)

간단한 CLI 런처 — 웹서버 시작 + 브라우저 자동 오픈:

```python
#!/usr/bin/env python3
"""
Trilobase SCODA Viewer

Usage:
    python scripts/serve.py [--port PORT] [--no-browser]
"""

import argparse
import sys
import webbrowser
import os
from threading import Timer


def open_browser(port):
    """Open default browser after delay."""
    webbrowser.open(f'http://localhost:{port}')


def main():
    parser = argparse.ArgumentParser(description='Start Trilobase web viewer')
    parser.add_argument('--port', type=int, default=8080,
                        help='Port to run server on (default: 8080)')
    parser.add_argument('--no-browser', action='store_true',
                        help='Do not open browser automatically')
    args = parser.parse_args()

    print(f"Starting Trilobase SCODA viewer...")
    print(f"Server will run on http://localhost:{args.port}")
    print(f"Press Ctrl+C to stop.")

    if not args.no_browser:
        Timer(1.5, lambda: open_browser(args.port)).start()

    # Import and run Flask app
    try:
        from app import app
        app.run(debug=False, host='0.0.0.0', port=args.port)
    except ImportError:
        print("Error: Could not import app.py", file=sys.stderr)
        print("Make sure you're running from the trilobase directory.", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)


if __name__ == '__main__':
    main()
```

### 사용법

```bash
# 기본 실행 (포트 8080, 브라우저 자동 오픈)
python scripts/serve.py

# 포트 변경
python scripts/serve.py --port 5000

# 브라우저 자동 오픈 비활성화
python scripts/serve.py --no-browser
```

### README.md 업데이트 (사용자 가이드 추가)

```markdown
## Quick Start

### Option 1: Run directly
```bash
python scripts/serve.py
```
Your browser will open automatically at http://localhost:8080

### Option 2: Run manually
```bash
python app.py
```
Then open http://localhost:8080 in your browser

### Requirements
- Python 3.8+
- Flask
```

## 릴리스 구조 제안

### 현재 (Phase 16 완료 후)

```
releases/trilobase-v1.0.0/
├── trilobase.db          # read-only DB
├── metadata.json         # SCODA metadata
├── checksums.sha256      # integrity check
└── README.md             # usage notes
```

### Phase 1 배포 시

```
releases/trilobase-v1.0.0/
├── trilobase.db
├── metadata.json
├── checksums.sha256
├── README.md
├── serve.py              # 런처 (복사본)
└── app/                  # Flask 앱 (복사본)
    ├── app.py
    ├── static/
    └── templates/
```

또는 wheel 패키지로:
```bash
pip install trilobase-1.0.0-py3-none-any.whl
trilobase serve
```

## 권장 사항

### 단기 (즉시 ~ v1.0.0)
1. `scripts/serve.py` 추가
2. README.md 사용자 가이드 작성
3. 릴리스 패키지에 앱 파일 포함

### 중기 (v1.0.0 ~ v1.1.0)
1. PyPI 패키지 배포 (`pip install trilobase`)
2. 독립 실행형 빌드 파이프라인 구축 (PyInstaller)
3. 플랫폼별 인스톨러 (Windows .exe, macOS .app)

### 장기
1. SCODA 공통 뷰어 설계
2. Docker 이미지 제공
3. 웹 기반 뷰어 (GitHub Pages + WebAssembly?)

## 결론

**즉시 적용:** `scripts/serve.py` 추가로 사용자 경험 개선 (브라우저 자동 오픈)

**첫 릴리스:** Python 패키지 형태로 배포 (연구자 대상)

**장기:** 독립 실행형 앱 + SCODA 공통 런너로 확장
