# SCODA Registry & Dependency Distribution — Detailed Design
(index.json schema · resolver pseudocode · GitHub Releases+Pages automation · lockfile spec)

---

## 0. 목표와 전제

### 목표
- **필수(required) dependency**를 가진 SCODA 패키지(PaleoCore, Trilobase 등)를
  - 버전 범위(semver range)로 관리하고
  - 런타임이 자동으로 resolve + 다운로드 + 무결성 검증 + 캐시
  - 필요 시 lockfile로 재현성까지 보장

### 전제
- 패키지는 `.scoda`(ZIP) 단일 파일이며 불변 스냅샷이다.
- Registry는 “백엔드 서버” 없이 **정적 파일**로 구성한다.
- 패키지 실파일은 **GitHub Releases**(또는 추후 object storage)에서 배포한다.
- Registry 인덱스는 **GitHub Pages**에서 호스팅한다.

---

## 1. Registry 구성 개요

Registry는 아래 3요소로 최소 구성한다.

1. `index.json` (정적) — 패키지/버전/URL/무결성 메타데이터
2. `.scoda` 파일들 — 실제 아카이브(대용량 가능)
3. (선택) `index.json.sig` — 인덱스 서명(향후)

권장 URL 구조(예시):

- index: `https://<org>.github.io/scoda-registry/index.json`
- artifact: GitHub Releases asset URL (버전별 `.scoda`, `checksums.sha256`)

---

## 2. index.json “정식” 스키마

### 2.1 설계 원칙
- **정적 JSON 1개**로 resolver가 필요한 모든 정보를 제공한다.
- “latest”는 편의 기능일 뿐, **resolver는 semver range**로 결정한다.
- integrity는 최소한 `sha256`를 제공한다.
- 패키지 메타데이터(요약, 제공 모듈 등)는 UX/검색을 위해 포함 가능하나, resolver 핵심은
  - `name`, `version`, `url`, `sha256`, `size`, (option) `published_at`
  이다.

### 2.2 JSON 스키마(논리 명세)

```json
{
  "schema_version": "1.0.0",
  "generated_at": "2026-02-12T00:00:00Z",
  "registry": {
    "name": "scoda-registry",
    "base_url": "https://<org>.github.io/scoda-registry/"
  },
  "packages": {
    "<package_name>": {
      "description": "…",
      "homepage": "…",
      "latest": "1.0.0",
      "versions": {
        "<version>": {
          "url": "https://…/download/…/<file>.scoda",
          "sha256": "<hex>",
          "size": 12345678,
          "content_type": "application/zip",
          "published_at": "2026-02-12T00:00:00Z",
          "yanked": false,
          "requires": [
            {
              "name": "paleocore",
              "range": ">=0.3.0,<0.4.0",
              "required": true
            }
          ],
          "provides": ["taxonomy"],
          "files": [
            {
              "name": "<file>.scoda",
              "sha256": "<hex>",
              "size": 12345678
            },
            {
              "name": "<file>.checksums.sha256",
              "sha256": "<hex>",
              "size": 4321
            }
          ]
        }
      }
    }
  }
}
```

### 2.3 필드 정의(핵심만)

- `schema_version` : index 스키마 버전 (semver)
- `generated_at` : index 생성 시각(UTC ISO-8601)
- `packages` : package name → metadata
- `packages[p].versions[v]` : 특정 패키지 버전 엔트리

버전 엔트리의 핵심 필드:
- `url` : `.scoda` 다운로드 URL(직접 다운로드 가능해야 함)
- `sha256` : `.scoda` 파일 무결성
- `size` : 바이트 단위
- `published_at` : 릴리스 시각 (정렬/UX 용)
- `yanked` : true면 resolver에서 기본 제외(명시적 허용 시만 선택)
- `requires` : dependency 목록 (range + required)
- `provides` : 이 패키지가 제공하는 모듈/도메인(검색/UX)
- `files` : 부속 파일(체크섬 파일 등) 목록(선택)

### 2.4 “yanked” 동작 규칙
- 기본 resolver는 `yanked=true` 버전을 제외
- 다만 lockfile이 특정 yanked 버전을 가리키면 **경고 후 허용** 가능(정책 선택)

---

## 3. Resolver 상세 설계

### 3.1 용어
- **Constraint / Range**: `>=0.3.0,<0.4.0`
- **Candidate**: range를 만족하는 가능한 버전들
- **Selection**: 후보 중 최종 선택 버전(기본: 최대 버전)

### 3.2 정책(기본값 추천)
1. **Lock 우선**: lockfile이 있으면 그 버전을 최우선 사용
2. **캐시 우선**: range를 만족하는 버전이 로컬 캐시에 있으면 다운로드 없이 사용 가능
3. **최대 버전 선택**: 후보 중 highest semver를 선택
4. **yanked 제외**: 후보 필터링에서 제외
5. **필수 dependency 미해결 시 실패**: partial mount 금지

### 3.3 Resolver 의사코드

#### 3.3.1 Resolve entrypoint

```text
function open_package(pkg_file_or_ref):
    pkg = load_manifest(pkg_file_or_ref)         # trilobase manifest
    lock = try_load_lock(pkg)                    # optional

    resolved = {}
    resolved[pkg.name] = pkg.version

    deps = pkg.dependencies
    for dep in deps:
        dep_version = resolve_dependency(dep, lock)
        resolved[dep.name] = dep_version

    ensure_all_downloaded(resolved)
    verify_all_integrity(resolved)

    mount_all(resolved)                          # runtime mounts all .scoda
    return MountedEnvironment(resolved)
```

#### 3.3.2 Dependency resolution

```text
function resolve_dependency(dep, lock):
    # dep: {name, range, required=true}
    if lock exists and lock.resolved_dependencies contains dep.name:
        v = lock.resolved_dependencies[dep.name]
        if satisfies(v, dep.range):
            return v
        else:
            error("Lockfile version violates range: " + dep.name)

    # otherwise resolve via registry index
    index = load_registry_index()                # index.json
    versions = list(index.packages[dep.name].versions.keys)

    candidates = []
    for v in versions:
        meta = index.packages[dep.name].versions[v]
        if meta.yanked == true: continue
        if satisfies(v, dep.range):
            candidates.append(v)

    if candidates empty:
        if dep.required:
            error("No compatible version for required dependency: " + dep.name)
        else:
            return null

    sort candidates by semver ascending
    return last(candidates)                      # highest compatible
```

#### 3.3.3 Download + cache

```text
function ensure_all_downloaded(resolved):
    for (name, version) in resolved:
        if local_cache_has(name, version):
            continue
        url = index.packages[name].versions[version].url
        tmp = download(url)
        sha = sha256(tmp)
        expected = index.packages[name].versions[version].sha256
        if sha != expected:
            error("Checksum mismatch: " + name + "@" + version)
        move_to_cache(tmp, name, version)
```

### 3.4 순환 의존성(cycle) 정책
- 초기 버전에서는 **cycle을 금지**하는 게 좋다.
- resolver는 `visiting` set으로 cycle을 탐지하고 즉시 오류를 낸다.

---

## 4. Lockfile 포맷 명세

### 4.1 목적
- 자동 resolve(최대버전 선택)는 “시간에 따라 결과가 변할 수 있음”
- lockfile은 **재현성**을 제공한다.
- lockfile은 “실행 환경”에 가깝고, 패키지 자체는 immutable 유지

### 4.2 파일명 규칙
- `<package_name>-<package_version>.lock.json`
  - 예: `trilobase-1.0.0.lock.json`

### 4.3 JSON 스키마(정식)

```json
{
  "lock_schema_version": "1.0.0",
  "generated_at": "2026-02-12T00:00:00Z",
  "root": {
    "name": "trilobase",
    "version": "1.0.0",
    "sha256": "<hex>"
  },
  "registry": {
    "index_url": "https://<org>.github.io/scoda-registry/index.json",
    "index_sha256": "<hex>"
  },
  "resolved_dependencies": {
    "paleocore": {
      "version": "0.3.2",
      "sha256": "<hex>",
      "url": "https://…/paleocore-0.3.2.scoda"
    }
  },
  "policy": {
    "allow_yanked": false,
    "offline_ok": true
  }
}
```

### 4.4 규칙
- 런타임은 lock이 존재하면 `resolved_dependencies`를 우선 사용
- 단, root manifest의 range를 위반하면 실패
- `index_sha256`는 선택이지만 강력 추천(인덱스 변조 탐지)

---

## 5. GitHub Releases + Pages 자동 배포 워크플로우

### 5.1 레포 구성(권장)
- repo A: `scoda-packages` (빌드/릴리즈 소스)
- repo B: `scoda-registry` (정적 index.json + Pages)

(단일 레포도 가능하지만, 권한/릴리즈/페이지를 분리하면 운영이 편함)

### 5.2 릴리즈 아티팩트 규칙
Release asset으로 업로드:
- `<name>-<version>.scoda`
- `<name>-<version>.checksums.sha256` (선택)

Release tag:
- `<name>-v<version>` 또는 `v<version>` (정책 택1)

### 5.3 CI 파이프라인 개요
트리거:
- tag push (예: `paleocore-v0.3.2`)
- 또는 GitHub Release publish

단계:
1) `.scoda` 빌드
2) sha256/size 계산
3) GitHub Release에 업로드
4) registry repo의 `index.json` 갱신 PR/커밋
5) registry Pages 자동 배포

### 5.4 GitHub Actions 설계(논리)

#### (A) 패키지 릴리즈 워크플로우 (repo: scoda-packages)
- on: `workflow_dispatch` + `push tags`
- steps:
  1. Build `.scoda`
  2. Compute sha256 + size
  3. Create/Update GitHub Release
  4. Upload artifacts
  5. Update registry index (repo dispatch or PR)

#### (B) registry index 갱신 워크플로우 (repo: scoda-registry)
- on: `repository_dispatch` (payload: package, version, url, sha256, size, requires…)
- steps:
  1. Checkout
  2. Load current `index.json`
  3. Insert/Update `packages[name].versions[version]`
  4. Set `latest` if semver higher
  5. Write back `index.json`
  6. Commit to `main`
  7. Pages deploy (Pages는 main 브랜치 기반 또는 Actions 기반 둘 다 가능)

### 5.5 “requires” 정보는 어디서 오나
두 가지 방식 중 택1:

- 방식 1(권장): 패키지의 `manifest.json`을 CI에서 파싱해 `requires`를 index에 복사
- 방식 2: 릴리즈 워크플로우에서 `requires`를 별도 YAML로 관리

방식 1이 “중복 정의 방지” 측면에서 유리하다.

---

## 6. 무결성/보안 권장사항

최소:
- `.scoda` sha256 검증

추가(향후):
- `index.json` 서명(예: minisign/sigstore)
- `.scoda` 서명
- TLS 고정(선택)

---

## 7. 오프라인/저비용 운영 모드

- 런타임은 캐시가 있으면 index 접근 없이도 열 수 있게(옵션)
- 단, dependency가 누락이면 실패
- lockfile이 있으면 index 없이도 정확한 버전 지정 가능

---

## 8. 구현 체크리스트

### index.json
- [ ] schema_version 도입
- [ ] yanked 지원
- [ ] requires/provides 포함
- [ ] published_at 기록
- [ ] index 생성/갱신 Action 구축

### resolver
- [ ] semver range parser
- [ ] yanked 필터링
- [ ] lock 우선 적용
- [ ] 캐시 우선 적용
- [ ] sha256 검증
- [ ] cycle 탐지

### CI/CD
- [ ] package release action
- [ ] registry update action
- [ ] Pages publish 확인
- [ ] release asset URL 안정성 확보(redirect 대응)

### lockfile
- [ ] 포맷 v1.0.0 고정
- [ ] index_sha256 포함
- [ ] 정책 필드(allow_yanked/offline_ok) 지원

---

## 9. MVP 권장 조합

- Registry: `index.json` + GitHub Releases
- Resolver: highest compatible + sha256 검증
- Cache: `~/.scoda/registry_cache/<name>/<version>/`
- Lockfile: optional (테스트/재현성 목적이면 조기 도입 추천)

---
