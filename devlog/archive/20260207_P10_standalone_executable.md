# Plan: 독립 실행형 앱 배포 (PyInstaller)

**날짜:** 2026-02-07
**목표:** Trilobase를 더블클릭으로 실행 가능한 단일 실행 파일로 패키징

## 배경

현재 Trilobase는 `python app.py` 명령으로 실행해야 한다. 일반 사용자를 위해 Python 설치 없이 실행 가능한 독립 앱이 필요하다.

## 도구: PyInstaller

- Python 앱을 단일 실행 파일로 패키징
- 모든 의존성(Flask, SQLite 등) 포함
- Windows/macOS/Linux 지원

## 구현 계획

### 1. `scripts/serve.py` 생성

브라우저 자동 오픈 + Flask 실행:

```python
#!/usr/bin/env python3
import webbrowser
from threading import Timer
import sys
import os

def open_browser():
    webbrowser.open('http://localhost:8080')

def main():
    print("Starting Trilobase SCODA Viewer...")
    print("Server running at http://localhost:8080")
    print("Press Ctrl+C to stop.\n")

    Timer(1.5, open_browser).start()

    # Flask 앱 import 및 실행
    from app import app
    app.run(debug=False, host='127.0.0.1', port=8080, use_reloader=False)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)
```

### 2. `trilobase.spec` 생성 (PyInstaller 설정)

```python
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['scripts/serve.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
        ('trilobase.db', '.'),
    ],
    hiddenimports=['flask', 'sqlite3'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='trilobase',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```

### 3. `scripts/build.py` 생성 (빌드 자동화)

```python
#!/usr/bin/env python3
"""
Build standalone executable for Trilobase

Usage:
    python scripts/build.py [--clean]
"""

import subprocess
import sys
import shutil
import os
from pathlib import Path

def main():
    print("Building Trilobase standalone executable...")

    # PyInstaller 설치 확인
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # 이전 빌드 정리
    if '--clean' in sys.argv:
        print("Cleaning previous builds...")
        for path in ['build', 'dist']:
            if os.path.exists(path):
                shutil.rmtree(path)

    # PyInstaller 실행
    cmd = [
        'pyinstaller',
        '--clean',
        '--noconfirm',
        'trilobase.spec'
    ]

    print(f"Running: {' '.join(cmd)}")
    subprocess.check_call(cmd)

    print("\n✓ Build complete!")
    print(f"Executable: dist/trilobase{'exe' if sys.platform == 'win32' else ''}")

if __name__ == '__main__':
    main()
```

### 4. `requirements.txt` 업데이트

```
flask
pyinstaller
```

### 5. `.gitignore` 업데이트

```
# PyInstaller
build/
dist/
*.spec
```

## 빌드 프로세스

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 빌드 실행
python scripts/build.py

# 3. 결과물
dist/trilobase        # 실행 파일
```

## 릴리스 패키지 구조

```
releases/trilobase-v1.0.0-windows/
├── trilobase.exe
├── trilobase.db
├── metadata.json
├── checksums.sha256
└── README.md

releases/trilobase-v1.0.0-linux/
├── trilobase
├── trilobase.db
├── metadata.json
├── checksums.sha256
└── README.md
```

## 테스트 시나리오

1. **기본 실행**: `./trilobase` 더블클릭 → 브라우저 자동 오픈
2. **DB 접근**: 웹 UI에서 genus/family 조회
3. **My Notes**: 주석 추가/삭제
4. **종료**: Ctrl+C 또는 창 닫기

## 알려진 제약사항

- **DB 경로**: 실행 파일과 같은 디렉토리에 `trilobase.db` 필요
- **용량**: ~50-70MB (Flask + 의존성 포함)
- **플랫폼별 빌드**: Windows에서 빌드 → Windows 전용, Linux에서 빌드 → Linux 전용
- **첫 실행 느림**: PyInstaller는 압축 해제 필요 (1-2초 지연)

## 향후 개선

- [ ] 포트 충돌 처리 (8080 사용 중일 때)
- [ ] GUI 진행 표시 (콘솔 없이)
- [ ] 시스템 트레이 아이콘
- [ ] 자동 업데이트 체크
- [ ] macOS .app 번들
- [ ] Windows 인스톨러 (.msi)

## 검증 방법

```bash
# 빌드
python scripts/build.py

# 실행 (콘솔 확인)
./dist/trilobase

# 브라우저에서 http://localhost:8080 확인
```
