# Phase 2: 깨진 문자 및 오타 수정

**작업일:** 2026-02-04

## 수정 내역

### 체코어 저자명 복원

| 패턴 | 수정 | 건수 |
|------|------|------|
| `.NAJDR` | `ŠNAJDR` | 85 |
| `P\x02IBYL` (깨진 Ř) | `PŘIBYL` | 145 |
| `VAN˛K` | `VANĚK` | 118 |
| `RUZICKA` | `RŮŽIČKA` | 12 |
| `KLOU!EK` | `KLOUČEK` | 9 |

### 체코어 지명 복원

| 패턴 | 수정 | 건수 |
|------|------|------|
| `.arka Fm` | `Šárka Fm` | 27 |
| `T"enice` | `Třenice` | 4 |

### Genus 이름 수정

| 패턴 | 수정 | 건수 |
|------|------|------|
| `.najdria` | `Šnajdria` | 1 |

### 오타 수정 (불필요한 쉼표)

| 패턴 | 수정 | 건수 |
|------|------|------|
| `Glabrella,` | `Glabrella` | 1 |
| `Natalina,` | `Natalina` | 1 |
| `Strenuella,` | `Strenuella` | 1 |

## 총 수정 건수

- 체코어 저자명: **369건**
- 체코어 지명: **31건**
- Genus 이름: **1건**
- 오타: **3건**
- **총합: 404건**

## 추가 수정 (PDF 확인 후)

### 불완전한 엔트리 수정
```
Before: Actinopeltis HAWLE & CORDA, 1847 [carolialexandri] Kral
After:  Actinopeltis HAWLE & CORDA, 1847 [carolialexandri] Králův Dvůr Fm, Czech Republic; CHEIRURIDAE; UORD.
```
- 원본 PDF (actinopeltis.png) 확인하여 완전한 엔트리로 복원

### NOVÁK 수정
- `NOVAK` → `NOVÁK`: 19건
- 다른 체코어 저자명과 일관성 유지

## 기술 노트

### 깨진 문자 원인
PDF에서 텍스트 추출 시 특수 문자 인코딩 문제 발생:
- `Ř` → `\x02` (STX 제어문자)
- `Š` → `.` (마침표)
- `ě` → `˛` (ogonek)
- `Č` → `!` (느낌표)
- `ř` → `"` (따옴표)

### 사용된 명령어
```bash
# 제어문자가 포함된 패턴 수정
sed -i $'s/P\x02IBYL/PŘIBYL/g' file.txt

# 일반 패턴 수정
sed -i 's/\.arka Fm/Šárka Fm/g' file.txt
```
