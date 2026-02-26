# P69: MkDocs Documentation Site (GitHub Pages + i18n)

**Date:** 2026-02-26
**Type:** Plan

## Goal

GitHub Pages로 배포되는 영어/한국어 이중 언어 문서 사이트 구축.
도구: MkDocs + Material theme + mkdocs-static-i18n plugin.

## Current State

- `docs/` 디렉토리에 순수 Markdown 문서 6개 (HANDOFF, HISTORY, paleocore_schema, scoda_*_architecture 3개)
- 루트에 README.md, CHANGELOG.md, CHANGELOG_paleocore.md
- `devlog/DEVLOG_SUMMARY.md` (29KB)
- `data/mcp_tools_trilobase.json` (MCP 도구 정의)
- 개별 devlog 174개는 **제외**

## Design Decisions

| 결정 | 선택 | 이유 |
|------|------|------|
| 문서 도구 | MkDocs + Material | Python 프로젝트에 자연스러움, Markdown 그대로 사용 |
| i18n 방식 | suffix 기반 (*.en.md / *.ko.md) | 기존 파일 구조 최소 변경, 번역 누락 시 기본 언어 fallback |
| 기본 언어 | English | 영어 우선 작성 후 한국어 번역 |
| 배포 | GitHub Actions → gh-pages 브랜치 | 기존 CI 패턴과 일관됨 |
| navigation.instant | 사용 안 함 | mkdocs-static-i18n과 비호환 |

## Phase A: Foundation (스켈레톤 + CI)

### A1. 새 파일 생성

- `mkdocs.yml` — MkDocs 설정
  - Theme: Material (teal/amber, 다크모드 토글, navigation.tabs)
  - Plugins: search, i18n (suffix, en default, ko)
  - Nav: Home → Getting Started → Database → Architecture → API → Project
- `.github/workflows/docs.yml` — GitHub Actions 배포
  - Trigger: push to main (paths: docs/**, mkdocs.yml) + workflow_dispatch
  - mkdocs gh-deploy --force
- `.gitignore` — `site/` 추가

### A2. docs/ 디렉토리 재구조화

기존 파일 이동 + i18n suffix 적용:

```
docs/
├── index.en.md                          ← NEW (README.md 기반 랜딩 페이지)
├── getting-started.en.md                ← NEW (설치/사용법)
├── database/
│   ├── schema.en.md                     ← NEW (DB 스키마 레퍼런스)
│   ├── queries.en.md                    ← NEW (SQL 예제)
│   └── paleocore-schema.ko.md           ← MOVE docs/paleocore_schema.md
├── architecture/
│   ├── scoda-package.en.md              ← MOVE docs/scoda_package_architecture.md
│   ├── scoda-registry.en.md             ← MOVE docs/scoda_registry_architecture.md
│   └── scoda-registry-detailed.ko.md    ← MOVE docs/scoda_registry_..._detailed.md
├── api/
│   └── mcp-tools.en.md                  ← NEW (mcp_tools_trilobase.json 기반)
└── project/
    ├── handoff.ko.md                    ← MOVE docs/HANDOFF.md
    ├── history.ko.md                    ← MOVE docs/HISTORY.md
    ├── devlog-summary.ko.md             ← COPY devlog/DEVLOG_SUMMARY.md
    ├── changelog.en.md                  ← COPY CHANGELOG.md
    └── changelog-paleocore.en.md        ← COPY CHANGELOG_paleocore.md
```

### A3. 로컬 테스트

```bash
pip install mkdocs-material mkdocs-static-i18n
mkdocs serve  # localhost:8000
```

## Phase B: English Content

| 페이지 | 소스 | 내용 |
|--------|------|------|
| `index.en.md` | README.md | 랜딩 페이지 (개요, 통계, 주요 기능) |
| `getting-started.en.md` | README.md | 설치 옵션 3가지, MCP 서버 설정 |
| `database/schema.en.md` | HANDOFF.md + README.md | 테이블별 스키마, 컬럼 설명 |
| `database/queries.en.md` | README.md | SQL 예제 모음 |
| `api/mcp-tools.en.md` | mcp_tools_trilobase.json | 도구별 이름/설명/파라미터 표 |

## Phase C: Korean Translation

- Phase B 영어 페이지의 한국어 버전 (`.ko.md`) 생성
- 이미 한국어인 페이지(handoff, history 등)의 영어 번역 작성
- 대용량 파일(HISTORY 46KB, DEVLOG_SUMMARY 29KB)은 후순위

## Excluded

- `devlog/` 개별 파일 174개
- `CLAUDE.md`, `GEMINI.md` (내부 도구 설정)
- `scripts/`, `tests/`, `data/` (json 제외)

## Verification

- [ ] `mkdocs serve` 로컬 빌드 오류 없음
- [ ] 언어 전환기(EN/한국어) 헤더에 표시
- [ ] 번역 없는 페이지 → 영어 fallback
- [ ] GitHub Actions docs 워크플로우 성공
- [ ] `https://jikhanjung.github.io/trilobase/` 접속 확인

## Dependencies

```
mkdocs-material>=9.5
mkdocs-static-i18n>=1.0
```
