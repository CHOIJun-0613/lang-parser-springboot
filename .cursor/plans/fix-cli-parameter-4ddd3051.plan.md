<!-- 4ddd3051-54a0-4362-b8c3-88f63fc4476f 2c51d0ac-da01-421c-80f5-bfa1dc8b60f7 -->
# CRUD Matrix 레이아웃 변경

## 변경 사항

### 1. 컬럼 순서 및 구조 변경

- **현재**: Class Name | Package | Tables | Operations
- **변경**: Package | Class Name | Schema | Table | Operations

### 2. 테이블 표시 방식 변경

- **현재**: 한 행에 모든 테이블을 쉼표로 구분하여 표시
- **변경**: 한 행에 테이블 1개만 표시, 클래스가 여러 테이블 사용 시 각각 별도 행으로

### 3. Schema 컬럼 추가

- Table 노드의 `schema` 속성값을 표시
- Neo4j에서 Table 노드 조회 시 schema 정보도 함께 가져와야 함

## 수정 대상 파일

### csa/cli/main.py

`crud_matrix` 함수 (1337-1390행) 수정:

1. 헤더 변경: Package | Class Name | Schema | Table | Operations
2. 데이터 표시 로직 변경: 테이블별로 별도 행 생성
3. Schema 정보 표시 추가

### csa/services/graph_db.py

`get_crud_matrix` 메서드 수정 가능성 확인:

- Table 노드의 schema 속성을 포함하여 반환하도록 수정 필요 여부 확인
- 반환 데이터 구조 변경 필요 여부 확인

## 예상 출력 형식

```
Package                        Class Name                Schema    Table                Operations
------------------------------------------------------------------------------------------------
com.carcare.domain.notification NotificationRepository   carcare   notifications        R, D, C, U
com.carcare.domain.payment     PaymentRepository         carcare   payments             R, D, C, U
com.carcare.domain.payment     PaymentRepository         carcare   reservations         R
com.carcare.domain.quote       QuoteRepository           carcare   quotes               R, D, C, U
com.carcare.domain.quote       QuoteRepository           carcare   quote_items          R
com.carcare.domain.quote       QuoteRepository           carcare   reservations         R
```

### To-dos

- [ ] 10개 CLI 함수의 매개변수 이름을 final_project_name에서 project_name으로 변경
- [ ] 각 함수 내부에서 사용하는 final_project_name 변수를 project_name으로 변경
- [ ] 예외 처리 개선: exit(1)을 return으로 변경하여 정상 종료하도록 수정