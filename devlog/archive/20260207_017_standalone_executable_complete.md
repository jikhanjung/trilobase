# Phase 18: 독립 실행형 앱 배포 완료

**날짜:** 2026-02-07

## 요약

PyInstaller를 사용하여 Trilobase를 Python 설치 없이 실행 가능한 단일 실행 파일로 패키징. 일반 사용자를 위한 배포 형식 구축.

## 구현 내용

### 1. `scripts/serve.py` — 런처 스크립트

- Flask 서버 시작
- 브라우저 자동 오픈 (1.5초 delay)
- PyInstaller frozen 모드 대응 (`sys._MEIPASS`)
- 에러 처리 (import 실패, 포트 충돌)

**특징:**
- `use_reloader=False`: PyInstaller와 호환
- `host='127.0.0.1'`: 로컬 전용 (보안)
- Ctrl+C 우아한 종료

### 2. `trilobase.spec` — PyInstaller 설정

**번들 포함:**
- `app.py` (Flask 앱)
- `templates/` (HTML 템플릿)
- `static/` (CSS/JS/아이콘)
- `trilobase.db` (SQLite 데이터베이스)

**Hidden imports:**
- flask, sqlite3, json, webbrowser, threading

**옵션:**
- `console=True`: 서버 로그 확인용
- `upx=True`: 압축 활성화
- 단일 파일 모드 (`onefile`)

### 3. `scripts/build.py` — 빌드 자동화

**기능:**
- PyInstaller 자동 설치 (없을 경우)
- `--clean` 옵션: 이전 빌드 정리
- 빌드 진행 상태 표시
- 결과물 크기/경로 출력

**사용법:**
```bash
python scripts/build.py [--clean]
```

### 4. 의존성 및 설정 업데이트

- `requirements.txt`: `pyinstaller` 추가
- `.gitignore`: `build/`, `dist/`, `*.spec` 제외

## 빌드 결과

```
dist/trilobase        # 14MB 단일 실행 파일 (Linux)
```

**포함 내용:**
- Python 3.12 인터프리터
- Flask + 의존성
- SQLite3
- 모든 templates/static
- trilobase.db (3.8MB)

## 사용법

### 개발자 (빌드)

```bash
# 빌드
python scripts/build.py

# 결과물
dist/trilobase        # 실행 파일
```

### 최종 사용자 (실행)

```bash
# 실행
./trilobase

# → 브라우저 자동 오픈 http://localhost:8080
# → Ctrl+C로 종료
```

## 플랫폼별 배포

| 플랫폼 | 빌드 환경 | 결과물 |
|--------|----------|--------|
| Linux | Linux | `trilobase` (ELF 64-bit) |
| Windows | Windows | `trilobase.exe` (PE 32-bit/64-bit) |
| macOS | macOS | `trilobase` (Mach-O) |

**주의:** 크로스 컴파일 불가. 각 플랫폼에서 빌드 필요.

## 제약사항

### 현재 제약

1. **포트 고정**: 8080 하드코딩
2. **DB 경로**: 실행 파일과 같은 디렉토리에 `trilobase.db` 필요
3. **브라우저**: WSL 환경에서 자동 오픈 제한
4. **첫 실행**: 압축 해제로 1-2초 지연

### 향후 개선 가능

- 포트 충돌 시 자동 변경
- GUI 진행 표시 (콘솔 대신)
- 시스템 트레이 아이콘
- macOS .app 번들
- Windows .msi 인스톨러
- 자동 업데이트 체크

## 릴리스 패키징 통합

`scripts/release.py` 수정하여 실행 파일 포함:

```
releases/trilobase-v1.0.0/
├── trilobase(.exe)      # 독립 실행 파일
├── trilobase.db         # 데이터베이스
├── metadata.json
├── checksums.sha256
└── README.md
```

(향후 작업)

## 테스트

빌드 성공 확인:
- ✓ PyInstaller 6.18.0 설치
- ✓ 14MB 실행 파일 생성
- ✓ serve.py 로직 포함
- ✓ templates/static/db 번들링

런타임 테스트 (GUI 환경에서 확인 필요):
- 브라우저 자동 오픈
- Flask 서버 시작
- API 응답 확인
- 주석 CRUD

## 수정 파일

| 파일 | 변경 | 신규/수정 |
|------|------|----------|
| `scripts/serve.py` | 런처 스크립트 | 신규 |
| `trilobase.spec` | PyInstaller 설정 | 신규 |
| `scripts/build.py` | 빌드 자동화 | 신규 |
| `requirements.txt` | pyinstaller 추가 | 수정 |
| `.gitignore` | build/dist 제외 | 수정 |

## 다음 단계

1. ~~독립 실행형 빌드~~ ✅
2. Windows/macOS 빌드 (별도 환경)
3. 릴리스 패키징 통합
4. 사용자 가이드 작성 (README 업데이트)
5. SCODA 공통 런너 설계 (장기)
