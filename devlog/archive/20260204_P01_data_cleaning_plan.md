# Trilobase 데이터 정제 및 데이터베이스 구축 계획

## 프로젝트 개요

Jell & Adrain (2002) PDF에서 추출한 삼엽충 genus 목록 데이터를 정제하고, 정규화된 데이터베이스로 구축하는 프로젝트.

## 현재 데이터 상태 분석

### 발견된 문제 유형

#### 1. 깨진 문자 (Broken Characters)

**1.1 체코어 이름 깨짐** (~197건 이상)
- `.NAJDR` → `ŠNAJDR`
- `PIBYL` → `PŘIBYL`
- `VAN˛K` → `VANĚK`
- 원인: PDF 텍스트 추출 시 특수 악센트 문자(háček 등) 인코딩 실패

**1.2 완전히 깨진 줄**
- 예: 줄 74 `˘ˇ˘. ˇ˙˝` - 의미 없는 문자열
- 줄 69-73: 빈 줄 또는 불완전한 데이터
- 원인: `Actinopeltis` 엔트리가 심각하게 손상됨

**1.3 Soft Hyphen 문제**
- `Ver­mont` → `Vermont` (U+00AD 포함)
- `Que­ensland` → `Queensland`
- 원인: PDF의 줄바꿈 하이픈이 추출 시 soft hyphen으로 변환

#### 2. 포맷팅 오류

**2.1 줄 병합 (Missing Line Break)** (~50건 이상 추정)
두 개 이상의 genera가 한 줄에 합쳐진 경우:
```
Albansia HOWELL, 1937 [pusilla] ... MCAM. Albertella WALCOTT, 1908 [helena] ...
```
패턴: `]; [A-Z]+\. [A-Z][a-z]+ [A-Z]+,` (마침표 뒤에 새 genus가 시작)

**2.2 줄 분리 (Incorrect Line Break)**
하나의 엔트리가 여러 줄로 분리된 경우:
```
줄 49: Acidusus OPIK, 1979 [Ptychagnostus (Acidusus) acidusus] ... MCAM
줄 50: [j.s.s. of Ptychagnostus, fide PENG & ROBISON, 2000].
```

**2.3 빈 줄**
- 줄 70-73, 2630 등에 빈 줄 존재

#### 3. 오타 (Typos)

- Genus name, author name의 철자 오류
- Temporal range 코드 오류
- Formation/Location 명칭 오류
- 수동 검증 필요

---

## 작업 단계

### Phase 1: 줄 정리 (한 Genus = 한 줄)

#### Step 1.1: Soft Hyphen 제거
- U+00AD (soft hyphen) 제거 및 단어 연결
- 줄 병합 전에 먼저 처리해야 단어가 올바르게 연결됨

#### Step 1.2: 분리된 줄 병합
한 엔트리가 여러 줄로 쪼개진 경우 병합:
- 줄이 `[`로 시작하는 경우 → 이전 줄에 병합
- 줄이 소문자로 시작하는 경우 → 이전 줄에 병합
- 줄이 공백으로 시작하는 경우 → 이전 줄에 병합

#### Step 1.3: 합쳐진 줄 분리
두 개 이상의 genera가 한 줄에 있는 경우 분리:
```
패턴: ]. [A-Z][a-z]+ [A-Z]+, [0-9]{4}
```
→ 마침표+공백 뒤에 새로운 genus 시작 시 줄바꿈 삽입

#### Step 1.4: 빈 줄 및 깨진 줄 제거
- 빈 줄 제거
- 의미 없는 깨진 문자만 있는 줄 제거 (예: `˘ˇ˘. ˇ˙˝`)
- 줄 69-74의 `Actinopeltis` 엔트리는 원본 PDF 확인 후 복원 필요

**Commit: "fix: normalize line breaks (one genus per line)"**

### Phase 2: 깨진 문자 및 오타 수정

#### Step 2.1: 체코어 저자명 복원
알려진 매핑 적용:
- `.NAJDR` → `ŠNAJDR` (Jiří Šnajdr)
- `PIBYL` → `PŘIBYL` (Alois Přibyl)
- `VAN˛K` → `VANĚK` (Jiří Vaněk)

#### Step 2.2: 기타 깨진 문자 수정
- 기타 악센트 문자 복원
- 인코딩 오류 수정

#### Step 2.3: 오타 수정
- Genus name 철자 오류
- Temporal range 코드 오류
- Formation/Location 명칭 오류

**Commit: "fix: restore broken characters and fix typos"**

### Phase 3: 데이터 검증

#### Step 3.1: Genus Name 검증
- 알파벳 순서 일관성 확인
- 중복 엔트리 확인
- 알려진 오타 수정

#### Step 3.2: Temporal Range 코드 검증
유효한 코드 목록:
- LCAM, MCAM, UCAM (Cambrian)
- LORD, MORD, UORD (Ordovician)
- LSIL, USIL (Silurian)
- LDEV, MDEV, UDEV (Devonian)
- MISS (Mississippian)
- PENN (Pennsylvanian)
- LPERM, PERM, UPERM (Permian)

#### Step 3.3: Authority Citation 형식 검증
- `AUTHOR, YEAR` 형식 일관성 확인

**Commit: "fix: correct typos and data errors"**

### Phase 4: 데이터베이스 설계 및 구축

#### Step 4.1: 스키마 설계
```
taxa
├── id (PK)
├── name
├── rank (genus, family, superfamily, suborder, order, class)
├── parent_id (FK → taxa.id, nullable) -- 상위 분류군 참조
├── is_valid (boolean)                 -- 현재 유효한 이름인지
├── author
├── year
├── type_specimen
├── formation_id (FK → formations.id, nullable)
├── location
├── temporal_range_start
├── temporal_range_end
├── notes
├── created_at
├── updated_at

synonyms
├── id (PK)
├── junior_id (FK → taxa.id)           -- 무효한 이름 (synonym)
├── senior_id (FK → taxa.id)           -- 유효한 이름 (valid name)
├── type (enum)                        -- synonym 유형
│   ├── 'subjective'                   -- j.s.s. (junior subjective synonym)
│   ├── 'objective'                    -- j.o.s. (junior objective synonym)
│   ├── 'replacement'                  -- replacement name
│   ├── 'preoccupied'                  -- preocc. (선점된 이름)
│   ├── 'suppressed'                   -- suppressed by ICZN
│   └── 'nomen_oblitum'                -- 망각명
├── fide_author                        -- 동의어 관계 확립 저자
├── fide_year                          -- 동의어 관계 확립 연도
├── notes
├── created_at

formations
├── id (PK)
├── name
├── normalized_name
├── country
├── region

temporal_ranges
├── id (PK)
├── code (LCAM, MCAM, etc.)
├── name (Lower Cambrian, etc.)
├── start_mya
├── end_mya
```

**taxa 테이블 계층 구조 예시:**
```
Trilobita (class, parent_id=NULL)
└── Phacopida (order, parent_id=Trilobita)
    └── Phacopoidea (superfamily, parent_id=Phacopida)
        └── Phacopidae (family, parent_id=Phacopoidea)
            └── Phacops (genus, parent_id=Phacopidae)
```

**synonyms 테이블 예시:**
```
-- Acadagnostus는 Peronopsis의 junior subjective synonym
junior_id: Acadagnostus
senior_id: Peronopsis
type: 'subjective'
fide_author: ROBISON
fide_year: 1995
```

#### Step 4.2: Parser 개발
- Python 또는 JavaScript로 텍스트 파일 파서 개발
- 정규표현식 기반 필드 추출

#### Step 4.3: 데이터 임포트
- SQLite 또는 PostgreSQL로 초기 임포트
- 데이터 무결성 검증

**Commit: "feat: implement database schema and data import"**

### Phase 5: 데이터 정규화

#### Step 5.1: Formation 정규화
- 동일 formation의 다양한 표기 통합
- Formation 테이블 구축

#### Step 5.2: Location 정규화
- 국가/지역 명칭 표준화
- 역사적 지명 → 현대 지명 매핑

#### Step 5.3: Temporal Range 정규화
- 복합 범위 처리 (예: LCAM-UCAM)
- 숫자 연대(Ma) 매핑

#### Step 5.4: Synonym 관계 구축
- `j.s.s.` (junior subjective synonym) 파싱 → `type='subjective'`
- `j.o.s.` (junior objective synonym) 파싱 → `type='objective'`
- `replacement name for X` 파싱 → `type='replacement'`
- `preocc.` (preoccupied) 파싱 → `type='preoccupied'`
- `suppressed by ICZN` 파싱 → `type='suppressed'`
- `nomen oblitum` 파싱 → `type='nomen_oblitum'`
- `fide AUTHOR, YEAR` 파싱 → `fide_author`, `fide_year`
- Junior taxon의 `is_valid = false` 설정

**Commit: "feat: normalize formation, location, and temporal data"**

### Phase 6: 상위 분류군 통합

#### Step 6.1: Family 데이터 통합
- `trilobite_family_list.txt` 파싱
- Family → Genus 관계 설정

#### Step 6.2: Order/Suborder 정보 추가
- 외부 소스에서 상위 분류 정보 수집
- Tree structure 구축

**Commit: "feat: integrate family and higher taxa hierarchy"**

---

## 기술 스택 (제안)

- **데이터베이스**: SQLite (개발/프로토타입) → PostgreSQL (프로덕션)
- **파서**: Python (pandas, regex)
- **검증**: pytest
- **마이그레이션**: Alembic 또는 raw SQL scripts

---

## 우선순위

1. **[Critical]** Phase 1 - 줄 정리 (한 Genus = 한 줄)
2. **[High]** Phase 2 - 깨진 문자 및 오타 수정
3. **[High]** Phase 3 - 데이터 검증
4. **[High]** Phase 4 - 데이터베이스 구축
5. **[Medium]** Phase 5 - 정규화
6. **[Medium]** Phase 6 - 상위 분류군 통합

---

## 참고사항

- 원본 PDF (Jell & Adrain, 2002)가 필요한 경우 복원 작업 필요
- 각 Phase 완료 시 반드시 git commit으로 기록
- Commit message 형식: `type: description` (fix, feat, docs, refactor)
