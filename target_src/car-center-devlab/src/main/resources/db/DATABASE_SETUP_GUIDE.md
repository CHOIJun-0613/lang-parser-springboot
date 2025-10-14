# Car Center Database Setup Guide

이 문서는 Car Center 애플리케이션의 데이터베이스 설정 및 migration 구성에 대한 가이드입니다.

## 📋 개요

### 환경별 데이터베이스 구성

| 환경 | 데이터베이스 | 초기화 방법 | Flyway |
|------|-------------|------------|--------|
| **local** | H2 (인메모리) | Flyway migration | ✅ 활성화 |
| **test** | H2 (인메모리) | Flyway migration | ✅ 활성화 |
| **dev** | PostgreSQL | DBeaver 수동 생성 | ❌ 비활성화 |
| **prod** | PostgreSQL | DBeaver 수동 생성 | ❌ 비활성화 |

## 🗂️ Migration 파일 구조

```
src/main/resources/db/migration/
├── V1__Create_users_table.sql
├── V2__Create_vehicle_master_tables.sql
├── V3__Create_vehicles_table.sql
├── V4__Create_service_centers_and_types_tables.sql
├── V5__Create_reservations_table.sql
├── V6__Create_quotes_and_quote_items_tables.sql
├── V7__Create_payments_table.sql
├── V8__Create_reviews_and_review_replies_tables.sql
├── V9__Create_notifications_and_settings_tables.sql
├── V10__Insert_vehicle_master_data.sql
└── h2/
    └── V1__Create_all_tables_h2.sql

src/test/resources/
└── application-test.yml

프로젝트 루트/
└── db_schema_setup.sql  # DBeaver용 통합 스크립트
```

## 🚀 환경별 설정 방법

### 1. Local 환경 (H2 + Flyway)

**특징:**
- H2 인메모리 데이터베이스 사용
- 애플리케이션 시작 시 Flyway가 자동으로 스키마 생성
- H2 Console 접근 가능: `http://localhost:8080/h2-console`

**실행 방법:**
```bash
# Local 환경으로 실행
./gradlew bootRun --args='--spring.profiles.active=local'

# 또는 배치 파일 사용
run-local.bat
```

**H2 Console 접속 정보:**
- JDBC URL: `jdbc:h2:mem:carcare_local`
- Username: `sa`
- Password: (비워둠)

### 2. Test 환경 (H2 + Flyway)

**특징:**
- 테스트 전용 H2 인메모리 데이터베이스
- 각 테스트 실행 시마다 깨끗한 스키마로 초기화
- H2 Console 비활성화 (보안)

**실행 방법:**
```bash
# 테스트 실행
./gradlew test

# 특정 프로파일로 테스트
./gradlew test --args='--spring.profiles.active=test'
```

### 3. Dev 환경 (PostgreSQL + 수동 DB 생성)

**특징:**
- PostgreSQL 데이터베이스 사용
- DBeaver로 수동 스키마 생성
- Flyway 비활성화
- Redis 연동 활성화

**설정 단계:**

1. **PostgreSQL 서버 준비**
   ```sql
   -- PostgreSQL에서 데이터베이스 생성
   CREATE DATABASE carcare_dev;
   ```

2. **DBeaver에서 스키마 생성**
   - `db_schema_setup.sql` 파일을 DBeaver에서 열기
   - carcare_dev 데이터베이스에 연결
   - 전체 스크립트 실행

3. **애플리케이션 실행**
   ```bash
   ./gradlew bootRun --args='--spring.profiles.active=dev'
   
   # 또는 배치 파일 사용
   run-dev.bat
   ```

**데이터베이스 연결 정보:**
- Host: `192.168.56.40`
- Port: `5432`
- Database: `carcare_dev`
- Username: `postgres`
- Password: `password`

### 4. Prod 환경 (PostgreSQL + 수동 DB 생성)

**특징:**
- 운영용 PostgreSQL 데이터베이스
- DBeaver로 수동 스키마 생성
- Flyway 비활성화
- 성능 최적화된 설정

**설정 단계:**

1. **PostgreSQL 서버 준비**
   ```sql
   -- PostgreSQL에서 데이터베이스 생성
   CREATE DATABASE carcare_prod;
   ```

2. **DBeaver에서 스키마 생성**
   - `db_schema_setup.sql` 파일을 DBeaver에서 열기
   - carcare_prod 데이터베이스에 연결
   - 전체 스크립트 실행

3. **애플리케이션 실행**
   ```bash
   ./gradlew bootRun --args='--spring.profiles.active=prod'
   
   # 또는 배치 파일 사용
   run-prod.bat
   ```

## 📊 데이터베이스 스키마 구조

### 주요 테이블

1. **users** - 사용자 정보
2. **vehicle_brands** - 차량 브랜드 마스터 데이터
3. **vehicle_models** - 차량 모델 마스터 데이터
4. **vehicles** - 사용자 차량 정보
5. **service_types** - 서비스 종류 마스터 데이터
6. **service_centers** - 서비스센터 정보
7. **service_center_operating_hours** - 서비스센터 운영시간
8. **reservations** - 서비스 예약 정보
9. **quotes** - 견적서 정보
10. **quote_items** - 견적 항목 정보
11. **payments** - 결제 정보
12. **reviews** - 서비스 리뷰 정보
13. **review_replies** - 리뷰 답글 정보
14. **notifications** - 알림 정보
15. **notification_settings** - 사용자별 알림 설정
16. **notification_templates** - 알림 템플릿

### ERD 관계

```
users (1) ←→ (N) vehicles
users (1) ←→ (N) reservations
users (1) ←→ (N) notifications
users (1) ←→ (1) notification_settings

vehicle_brands (1) ←→ (N) vehicle_models
vehicle_brands (1) ←→ (N) vehicles
vehicle_models (1) ←→ (N) vehicles

service_centers (1) ←→ (N) reservations
service_centers (1) ←→ (1) service_center_operating_hours
service_types (1) ←→ (N) reservations

reservations (1) ←→ (N) quotes
reservations (1) ←→ (N) payments
reservations (1) ←→ (N) reviews

quotes (1) ←→ (N) quote_items
quotes (1) ←→ (N) payments

reviews (1) ←→ (N) review_replies
```

## 🔧 개발 시 주의사항

### PostgreSQL vs H2 차이점

| 기능 | PostgreSQL | H2 |
|------|------------|-----|
| UUID 타입 | `UUID` | `VARCHAR(36)` |
| JSON 타입 | `JSONB` | `CLOB` |
| 시퀀스 | `BIGSERIAL` | `BIGINT AUTO_INCREMENT` |
| 타임스탬프 | `TIMESTAMP WITH TIME ZONE` | `TIMESTAMP` |

### Migration 파일 작성 규칙

1. **파일명 규칙**: `V{버전}___{설명}.sql`
2. **PostgreSQL 우선**: PostgreSQL 문법으로 작성
3. **H2 호환성**: H2용 별도 파일 제공
4. **역순 호환**: 기존 데이터 손실 방지

### 새로운 Migration 추가 시

1. **PostgreSQL용 migration 파일 생성**
   ```sql
   -- src/main/resources/db/migration/V11__Add_new_feature.sql
   ```

2. **H2용 스키마 업데이트**
   ```sql
   -- src/main/resources/db/migration/h2/V1__Create_all_tables_h2.sql 수정
   ```

3. **DBeaver용 스크립트 업데이트**
   ```sql
   -- db_schema_setup.sql 수정
   ```

## 🛠️ 트러블슈팅

### 일반적인 문제들

1. **H2 Console 접속 안됨**
   - URL 확인: `http://localhost:8080/h2-console`
   - JDBC URL: `jdbc:h2:mem:carcare_local` 정확히 입력

2. **PostgreSQL 연결 실패**
   - 서버 상태 확인: `192.168.56.40:5432`
   - 방화벽 설정 확인
   - 데이터베이스 존재 여부 확인

3. **Flyway Migration 실패**
   - 기존 스키마 정리: `DROP SCHEMA public CASCADE; CREATE SCHEMA public;`
   - Migration 파일 문법 오류 확인

4. **H2/PostgreSQL 호환성 문제**
   - UUID vs VARCHAR(36)
   - JSONB vs CLOB
   - TIMESTAMP 타입 차이

### 로그 확인

```yaml
# application.yml에 추가
logging:
  level:
    org.flywaydb: DEBUG
    com.zaxxer.hikari: DEBUG
```

## 📚 참고 자료

- [Flyway Documentation](https://flywaydb.org/documentation/)
- [H2 Database Documentation](http://h2database.com/html/main.html)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Spring Boot Database Initialization](https://docs.spring.io/spring-boot/docs/current/reference/htmlsingle/#howto.data-initialization)

---

**업데이트:** 2024년 12월 기준 최신 스키마 구조
**작성자:** Car Center Development Team 