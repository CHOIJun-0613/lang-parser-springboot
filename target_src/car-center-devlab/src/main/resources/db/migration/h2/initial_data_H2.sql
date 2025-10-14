-- H2 Initial Data for Local Development Environment
-- Simplified version for better H2 compatibility
-- 
-- Instructions:
-- 1. This script is executed automatically after schema setup
-- 2. Contains essential operational data for local development and testing
-- 3. H2 database configured with PostgreSQL compatibility mode
--
-- Database: carcare_local (H2 file-based)
-- Version: 1.0 (Simplified for H2 compatibility)

-- =====================================================
-- ADDITIONAL SERVICE TYPES - 서비스 종류 추가 데이터
-- =====================================================

INSERT INTO service_types (name, description, category, estimated_duration, base_price, is_active) VALUES
-- 추가 정비 서비스
('엔진오일교환', '엔진오일 및 필터 교환', '정비', 30, 80000, true),
('에어컨점검', '에어컨 시스템 점검 및 정비', '정비', 45, 70000, true),
('브레이크오일교체', '브레이크 오일 교체', '정비', 45, 80000, true),
('타이어밸런싱', '타이어 밸런싱 조정', '정비', 40, 60000, true),
('배터리점검', '배터리 상태 점검', '점검', 20, 30000, true),
('전기계통점검', '차량 전기계통 종합 점검', '점검', 60, 80000, true),
('에어컨가스충전', '에어컨 냉매 가스 충전', '정비', 30, 50000, true),
('전조등교체', '헤드라이트 전구 교체', '정비', 25, 50000, true),
('차량세차', '전문 차량 세차 서비스', '기타', 60, 30000, true),
('긴급출동', '24시간 긴급출동 서비스', '기타', 0, 100000, true);

-- =====================================================
-- SERVICE CENTERS - 서비스센터 정보
-- =====================================================

INSERT INTO service_centers (
    name, description, address, phone_number, email, 
    business_number, owner_name, latitude, longitude,
    verification_status, is_active, is_operating,
    specialized_services, facilities, address_detail, website
) VALUES 
-- 서울 지역 주요 서비스센터
('현대모터스 강남점', '현대자동차 공식 서비스센터 강남점', '서울특별시 강남구 테헤란로 123', '02-1234-5678', 'gangnam@hyundai.com', 
 '123-45-67890', '김현대', 37.5012, 127.0396, 'APPROVED', true, true,
 '현대차 전문정비, 무상점검, 긴급출동', '리프트 10대, 대기실, 무료WiFi, 주차장', '1층', 'https://gangnam.hyundai.com'),

('기아모터스 서초점', '기아자동차 공식 서비스센터 서초점', '서울특별시 서초구 강남대로 456', '02-2345-6789', 'seocho@kia.com',
 '234-56-78901', '박기아', 37.4847, 127.0282, 'APPROVED', true, true,
 '기아차 전문정비, 신속정비, 부품교체', '리프트 8대, 고객휴게실, 주차장', '지하1층-지상2층', 'https://seocho.kia.com'),

('삼성카서비스 잠실점', '삼성자동차 서비스센터 잠실점', '서울특별시 송파구 잠실로 789', '02-3456-7890', 'jamsil@samsung.com',
 '345-67-89012', '이삼성', 37.5133, 127.1000, 'APPROVED', true, true,
 '수입차 전문, 진단장비 완비', '최신 진단장비, VIP룸, 발렛파킹', '1-3층', 'https://jamsil.samsung.com'),

('종합모터스 영등포점', '종합 자동차 정비소 영등포점', '서울특별시 영등포구 여의대로 159', '02-4567-8901', 'ydp@motors.com',
 '456-78-90123', '정종합', 37.5185, 126.9035, 'APPROVED', true, true,
 '모든 브랜드 정비가능, 합리적 가격', '대형 정비베이, 24시간 운영', '1-2층', NULL),

-- 부산 지역 서비스센터  
('부산모터스 해운대점', '종합 자동차 정비소 해운대점', '부산광역시 해운대구 마린시티로 321', '051-1234-5678', 'haeundae@motors.com',
 '567-89-01234', '최부산', 35.1631, 129.1644, 'APPROVED', true, true,
 '모든 브랜드 정비가능, 24시간 응급서비스', '대형 정비베이, 24시간 운영', '1층', NULL),

-- 대구 지역 서비스센터
('BMW서비스 대구점', 'BMW 공식 서비스센터 대구점', '대구광역시 수성구 범어로 987', '053-1234-5678', 'daegu@bmw.com',
 '789-01-23456', '김독일', 35.8591, 128.6311, 'APPROVED', true, true,
 'BMW 전문정비, 순정부품 사용', '최신 BMW 전용장비, 고급 대기실', '1-3층', 'https://daegu.bmw.co.kr');

-- =====================================================
-- TEST USERS - 테스트용 사용자
-- =====================================================

INSERT INTO users (user_uuid, email, password, name, phone, role, is_active, email_verified) VALUES
-- 시스템 관리자
('550e8400-e29b-41d4-a716-446655440000', 'admin@test.com', '$2a$12$8D7zQaGVF394BaWUF0gKrekUHai8G/Xb.u/yoEo.d3sBJkXyrUJlC', 
 '시스템관리자', '02-1234-5678', 'SYSTEM_ADMIN', true, true),

-- 테스트 고객
('550e8400-e29b-41d4-a716-446655440001', 'customer1@test.com', '$2a$12$8D7zQaGVF394BaWUF0gKrekUHai8G/Xb.u/yoEo.d3sBJkXyrUJlC',
 '홍길동', '010-1234-5678', 'CUSTOMER', true, true),
('550e8400-e29b-41d4-a716-446655440002', 'customer2@test.com', '$2a$12$8D7zQaGVF394BaWUF0gKrekUHai8G/Xb.u/yoEo.d3sBJkXyrUJlC',
 '김영희', '010-2345-6789', 'CUSTOMER', true, true),

-- 서비스센터 관리자
('550e8400-e29b-41d4-a716-446655440010', 'center@test.com', '$2a$12$8D7zQaGVF394BaWUF0gKrekUHai8G/Xb.u/yoEo.d3sBJkXyrUJlC',
 '현대모터스강남점', '02-1234-5678', 'CENTER_MANAGER', true, true);

-- =====================================================
-- TEST VEHICLES - 테스트용 차량 데이터
-- =====================================================

INSERT INTO vehicles (vehicle_uuid, user_id, make, model, vehicle_year, license_plate, vin, fuel_type, mileage, color, brand_id, model_id) VALUES
('550e8400-e29b-41d4-a716-446655440030', 2, '현대', '아반떼', 2022, '12가3456', 'KMHL14JA5NA123456', 'GASOLINE', 25000, '흰색', 1, 1),
('550e8400-e29b-41d4-a716-446655440031', 2, '기아', 'K5', 2021, '23나4567', 'KNAG34LA5MA234567', 'GASOLINE', 35000, '검은색', 2, 3),
('550e8400-e29b-41d4-a716-446655440032', 3, 'BMW', '320i', 2020, '34다5678', 'WBA8E5G57LNT12345', 'GASOLINE', 45000, '은색', 4, 4),
('550e8400-e29b-41d4-a716-446655440033', 3, '벤츠', 'C200', 2023, '45라6789', 'WDD2050831F123456', 'GASOLINE', 15000, '검은색', 5, 5);

-- =====================================================
-- NOTIFICATION TEMPLATES - 기본 알림 템플릿
-- =====================================================

INSERT INTO notification_templates (
    template_uuid, name, type, channel, language, subject, title_template, content_template, variables, is_active
) VALUES
-- 예약 관련 기본 템플릿
('template-reservation-sms', '예약확인_SMS', 'RESERVATION_CONFIRMED', 'SMS', 'ko', NULL,
 '예약이 확인되었습니다', '안녕하세요. 예약이 확인되었습니다. 예약번호: {{reservationNumber}}',
 '{"reservationNumber": "예약번호"}', true),

('template-reservation-email', '예약확인_이메일', 'RESERVATION_CONFIRMED', 'EMAIL', 'ko', '[차케어] 예약 확인',
 '예약 확인 안내', '안녕하세요. 예약이 확인되었습니다.<br/>예약번호: {{reservationNumber}}<br/>감사합니다.',
 '{"reservationNumber": "예약번호"}', true),

-- 결제 관련 기본 템플릿  
('template-payment-sms', '결제완료_SMS', 'PAYMENT_COMPLETED', 'SMS', 'ko', NULL,
 '결제가 완료되었습니다', '결제가 완료되었습니다. 결제번호: {{paymentId}}',
 '{"paymentId": "결제번호"}', true),

-- 서비스 관련 기본 템플릿
('template-service-sms', '서비스완료_SMS', 'SERVICE_COMPLETED', 'SMS', 'ko', NULL,
 '서비스가 완료되었습니다', '서비스가 완료되었습니다. 차량을 픽업해주세요.',
 '{}', true);

-- =====================================================
-- SERVICE CENTER OPERATING HOURS - 운영시간 설정
-- =====================================================

INSERT INTO service_center_operating_hours (
    service_center_id, current_status, weekly_schedule, default_settings
) VALUES
-- 현대모터스 강남점
(1, 'CLOSED', 
 '{"monday": {"open": "09:00", "close": "18:00", "isOpen": true}, "tuesday": {"open": "09:00", "close": "18:00", "isOpen": true}, "wednesday": {"open": "09:00", "close": "18:00", "isOpen": true}, "thursday": {"open": "09:00", "close": "18:00", "isOpen": true}, "friday": {"open": "09:00", "close": "18:00", "isOpen": true}, "saturday": {"open": "09:00", "close": "15:00", "isOpen": true}, "sunday": {"isOpen": false}}',
 '{"breakStartTime": "12:00", "breakEndTime": "13:00"}'),

-- 기아모터스 서초점
(2, 'CLOSED',
 '{"monday": {"open": "08:30", "close": "17:30", "isOpen": true}, "tuesday": {"open": "08:30", "close": "17:30", "isOpen": true}, "wednesday": {"open": "08:30", "close": "17:30", "isOpen": true}, "thursday": {"open": "08:30", "close": "17:30", "isOpen": true}, "friday": {"open": "08:30", "close": "17:30", "isOpen": true}, "saturday": {"open": "08:30", "close": "14:00", "isOpen": true}, "sunday": {"isOpen": false}}',
 '{"breakStartTime": "12:00", "breakEndTime": "13:00"}'),

-- 삼성카서비스 잠실점
(3, 'CLOSED',
 '{"monday": {"open": "09:00", "close": "19:00", "isOpen": true}, "tuesday": {"open": "09:00", "close": "19:00", "isOpen": true}, "wednesday": {"open": "09:00", "close": "19:00", "isOpen": true}, "thursday": {"open": "09:00", "close": "19:00", "isOpen": true}, "friday": {"open": "09:00", "close": "19:00", "isOpen": true}, "saturday": {"open": "09:00", "close": "16:00", "isOpen": true}, "sunday": {"isOpen": false}}',
 '{"breakStartTime": "12:00", "breakEndTime": "13:00"}');

-- =====================================================
-- NOTIFICATION SETTINGS - 사용자별 알림 설정
-- =====================================================

INSERT INTO notification_settings (user_id, sms_enabled, push_enabled, email_enabled, in_app_enabled) VALUES
(1, true, true, true, true),  -- admin
(2, true, true, true, true),  -- customer1
(3, true, true, true, true),  -- customer2
(4, true, false, true, true); -- center manager

-- =====================================================
-- 데이터 삽입 완료 확인
-- =====================================================

-- 데이터 삽입 확인 쿼리 (H2 호환)
SELECT 
    'Service Types' as table_name, COUNT(*) as record_count FROM service_types WHERE is_active = true
UNION ALL
SELECT 
    'Service Centers' as table_name, COUNT(*) as record_count FROM service_centers WHERE is_active = true
UNION ALL
SELECT 
    'Users' as table_name, COUNT(*) as record_count FROM users WHERE is_active = true
UNION ALL
SELECT 
    'Vehicles' as table_name, COUNT(*) as record_count FROM vehicles WHERE is_active = true
UNION ALL
SELECT 
    'Notification Templates' as table_name, COUNT(*) as record_count FROM notification_templates WHERE is_active = true
UNION ALL
SELECT 
    'Operating Hours' as table_name, COUNT(*) as record_count FROM service_center_operating_hours
UNION ALL
SELECT 
    'Notification Settings' as table_name, COUNT(*) as record_count FROM notification_settings;

-- 초기 데이터 삽입 완료 (H2 호환 단순화 버전)
-- 총 서비스 타입: 15개 (기본 5개 + 추가 10개)
-- 총 서비스센터: 6개 (주요 도시)
-- 총 사용자: 4개 (관리자 1, 서비스센터 1, 고객 2)
-- 총 차량: 4대 (테스트용)
-- 총 알림 템플릿: 4개 (기본 템플릿만)
-- 
-- H2 호환성 개선사항:
-- 1. 복잡한 JSON 구조 단순화
-- 2. 데이터량 최소화로 초기화 속도 향상
-- 3. 필수 데이터만 포함하여 안정성 확보
-- 4. 모든 외래키 참조 유효성 검증
-- 
-- 실행 완료 후 H2 Console에서 확인: http://localhost:8080/h2-console 