# 20260204_007_phase7_order_integration.md

## Phase 7: Order 통합 및 계층 구조 구축

### 목표
Family를 Order로 그룹화하고, 더 나아가 Suborder, Superfamily를 포함하는 완전한 삼엽충 분류 계층 구조를 데이터베이스에 반영한다.

### 초기 접근 및 변경 사항
- **초기 계획**: 간단한 `orders` 테이블을 생성하여 Order 이름과 해당 Family 수를 저장할 예정이었다.
- **변경 이유**: 사용자 요청에 따라 `adrain2011.txt` 파일에 있는 Class, Order, Suborder, Superfamily, Family의 복잡한 계층 구조를 모두 담을 수 있는 유연한 데이터 모델이 필요해졌다.
- **새로운 접근**: self-referential (`parent_id`) 구조를 가진 `taxonomic_ranks` 테이블을 설계하여 모든 분류 계층을 단일 테이블에 저장하고 부모-자식 관계로 연결하기로 결정했다.

### 데이터 소스
- `adrain2011.txt`: Adrain (2011)의 분류 체계를 정리한 텍스트 파일. 이 파일은 들여쓰기 대신 'Order', 'Suborder', 'Superfamily', 'Family'와 같은 키워드로 계층 구조를 나타낸다.

### DB 스키마 변경
- 기존의 `orders` 테이블(계획되었으나 생성되지 않음)은 삭제되었다.
- `taxonomic_ranks` 테이블이 새로 생성되었다.
  ```sql
  CREATE TABLE taxonomic_ranks (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      rank TEXT NOT NULL, -- Class, Order, Suborder, Superfamily, Family
      parent_id INTEGER,
      author TEXT,
      notes TEXT,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (parent_id) REFERENCES taxonomic_ranks(id)
  );
  ```
- `taxa` 테이블의 `family_id` 필드는 향후 `taxonomic_ranks.id`와 연결되도록 계획되었다.

### 데이터 추출 및 정규화 스크립트
- `scripts/populate_taxonomic_ranks.py` 스크립트를 새로 작성하여 `adrain2011.txt` 파일을 파싱하고 `taxonomic_ranks` 테이블을 채웠다.
- **스크립트 로직**:
    1.  파일의 첫 줄에서 "Class Trilobita Walch, 1771"을 추출하여 `Class` 등급의 최상위 노드로 삽입했다 (`parent_id`는 NULL).
    2.  이후 각 줄의 시작 키워드('Order', 'Suborder', 'Superfamily', 'Family')를 기반으로 등급을 식별했다.
    3.  `last_seen_id` 딕셔너리를 사용하여 각 등급의 가장 최근에 삽입된 ID를 추적하고, 이를 통해 현재 항목의 `parent_id`를 정확하게 결정했다.
    4.  이름, 저자, 노트(괄호 안의 정보)를 정규 표현식을 사용하여 추출했다.

### 검증
- `taxonomic_ranks` 테이블의 데이터 삽입 후, self-join SQL 쿼리를 통해 계층 구조의 무결성을 검증했다.
  ```sql
  SELECT
    T1.name AS taxon_name,
    T1.rank AS taxon_rank,
    T2.name AS parent_name,
    T2.rank AS parent_rank
  FROM taxonomic_ranks AS T1
  LEFT JOIN taxonomic_ranks AS T2
    ON T1.parent_id = T2.id
  ORDER BY T1.id;
  ```
- 쿼리 결과, 'Class'부터 'Family'까지 모든 계층 관계가 올바르게 설정되었음이 확인되었다.

### 다음 단계
- `taxa` 테이블의 `family` 필드를 `taxonomic_ranks` 테이블의 해당 Family 항목과 연결하는 작업이 필요하다.
- `families` 테이블을 `taxonomic_ranks` 테이블로 통합하거나 참조하는 방안을 고려한다.
