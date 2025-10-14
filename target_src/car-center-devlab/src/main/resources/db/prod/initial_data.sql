-- PostgreSQL Initial Data for DEV/PROD Environment
-- Execute this script manually in DBeaver after schema setup
-- 
-- Instructions:
-- 1. Execute db_schema_setup.sql first to create all tables
-- 2. Execute this script to insert initial operational data
--
-- Database: carcare_dev (for development) or carcare_prod (for production)
-- Version: 1.0
-- Contains: Service types, Service centers, Admin users, Notification templates

-- =====================================================
-- SERVICE TYPES - 서비스 종류 마스터 데이터
-- =====================================================

INSERT INTO service_types (name, description, category, estimated_duration, base_price, is_active) VALUES
-- 정기점검 카테고리
('정기점검', '차량 정기 점검 서비스', '점검', 60, 50000, true),
('종합점검', '차량 전체 종합 점검 서비스', '점검', 120, 100000, true),
('출고전점검', '신차 출고 전 점검 서비스', '점검', 90, 80000, true),
('사고후점검', '사고 후 안전 점검 서비스', '점검', 150, 150000, true),
('중고차점검', '중고차 구매 전 점검 서비스', '점검', 180, 200000, true),

-- 엔진 관련 정비
('엔진오일교환', '엔진오일 및 필터 교환', '정비', 30, 80000, true),
('변속기오일교환', '변속기 오일 교환 서비스', '정비', 60, 150000, true),
('냉각수교체', '엔진 냉각수 교체 서비스', '정비', 45, 80000, true),
('에어필터교체', '엔진 에어필터 교체', '정비', 20, 35000, true),
('연료필터교체', '연료 필터 교체', '정비', 40, 60000, true),
('점화플러그교체', '점화플러그 교체', '정비', 60, 100000, true),
('타이밍벨트교체', '타이밍벨트 교체', '정비', 180, 400000, true),

-- 브레이크 시스템
('브레이크패드교체', '브레이크 패드 교체 서비스', '정비', 90, 150000, true),
('브레이크디스크교체', '브레이크 디스크 교체', '정비', 120, 300000, true),
('브레이크오일교체', '브레이크 오일 교체', '정비', 45, 80000, true),
('브레이크라이닝교체', '브레이크 라이닝 교체', '정비', 100, 200000, true),

-- 타이어 관련
('타이어교체', '타이어 교체 서비스', '정비', 45, 300000, true),
('타이어위치교환', '타이어 위치 교환 서비스', '정비', 30, 50000, true),
('타이어밸런싱', '타이어 밸런싱 조정', '정비', 40, 60000, true),
('휠얼라인먼트', '휠 얼라인먼트 조정', '정비', 60, 80000, true),
('타이어펑크수리', '타이어 펑크 수리', '정비', 30, 30000, true),

-- 배터리 및 전기계통
('배터리교체', '차량 배터리 교체 서비스', '정비', 30, 120000, true),
('배터리점검', '배터리 상태 점검', '점검', 20, 30000, true),
('전기계통점검', '차량 전기계통 종합 점검', '점검', 60, 80000, true),
('발전기교체', '발전기(알터네이터) 교체', '정비', 120, 300000, true),
('시동모터교체', '시동모터 교체', '정비', 90, 250000, true),

-- 에어컨 시스템
('에어컨점검', '에어컨 시스템 점검 및 정비', '정비', 45, 70000, true),
('에어컨가스충전', '에어컨 냉매 가스 충전', '정비', 30, 50000, true),
('에어컨필터교체', '실내 에어컨 필터 교체', '정비', 25, 40000, true),
('에어컨컴프레서교체', '에어컨 컴프레서 교체', '정비', 180, 500000, true),

-- 서스펜션 시스템
('쇼크업소버교체', '쇼크업소버 교체', '정비', 120, 300000, true),
('스프링교체', '서스펜션 스프링 교체', '정비', 150, 400000, true),
('스트럿교체', '맥퍼슨 스트럿 교체', '정비', 180, 500000, true),

-- 연료시스템
('연료펌프교체', '연료펌프 교체', '정비', 120, 300000, true),
('연료탱크청소', '연료탱크 청소', '정비', 180, 200000, true),
('연료라인점검', '연료라인 점검 및 청소', '점검', 60, 80000, true),

-- 기타 정비
('와이퍼교체', '와이퍼 블레이드 교체', '정비', 15, 30000, true),
('전조등교체', '헤드라이트 전구 교체', '정비', 25, 50000, true),
('미션오일교체', '미션 오일 교체', '정비', 50, 120000, true),
('파워핸들오일교체', '파워 스티어링 오일 교체', '정비', 35, 60000, true),
('머플러교체', '머플러 교체', '정비', 90, 200000, true),
('라디에이터교체', '라디에이터 교체', '정비', 150, 400000, true),

-- 특수 서비스
('차량세차', '전문 차량 세차 서비스', '기타', 60, 30000, true),
('실내청소', '차량 실내 청소 서비스', '기타', 90, 50000, true),
('왁싱코팅', '차량 왁싱 코팅 서비스', '기타', 120, 80000, true),
('하부도장', '차량 하부 도장 서비스', '기타', 180, 150000, true),
('유리교체', '자동차 유리 교체', '정비', 60, 200000, true),
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
-- 서울 지역 서비스센터
('현대모터스 강남점', '현대자동차 공식 서비스센터 강남점', '서울특별시 강남구 테헤란로 123', '02-1234-5678', 'gangnam@hyundai.com', 
 '123-45-67890', '김현대', 37.5012, 127.0396, 'APPROVED', true, true,
 '현대차 전문정비, 무상점검, 긴급출동, 엔진오버홀', '리프트 10대, 대기실, 무료WiFi, 커피, 주차장 50면', '1층', 'https://gangnam.hyundai.com'),

('기아모터스 서초점', '기아자동차 공식 서비스센터 서초점', '서울특별시 서초구 강남대로 456', '02-2345-6789', 'seocho@kia.com',
 '234-56-78901', '박기아', 37.4847, 127.0282, 'APPROVED', true, true,
 '기아차 전문정비, 신속정비, 부품교체, 판금도색', '리프트 8대, 고객휴게실, 주차장, 무료셔틀', '지하1층-지상2층', 'https://seocho.kia.com'),

('삼성카서비스 잠실점', '삼성자동차 서비스센터 잠실점', '서울특별시 송파구 잠실로 789', '02-3456-7890', 'jamsil@samsung.com',
 '345-67-89012', '이삼성', 37.5133, 127.1000, 'APPROVED', true, true,
 '수입차 전문, 진단장비 완비, 르노삼성 전문', '최신 진단장비, VIP룸, 발렛파킹, 세차서비스', '1-3층', 'https://jamsil.renaultsamsung.com'),

('종합모터스 영등포점', '종합 자동차 정비소 영등포점', '서울특별시 영등포구 여의대로 159', '02-4567-8901', 'ydp@motors.com',
 '456-78-90123', '정종합', 37.5185, 126.9035, 'APPROVED', true, true,
 '모든 브랜드 정비가능, 합리적 가격, 24시간 서비스', '대형 정비베이, 24시간 운영, 견인서비스', '1-2층', NULL),

-- 부산 지역 서비스센터  
('부산모터스 해운대점', '종합 자동차 정비소 해운대점', '부산광역시 해운대구 마린시티로 321', '051-1234-5678', 'haeundae@motors.com',
 '567-89-01234', '최부산', 35.1631, 129.1644, 'APPROVED', true, true,
 '모든 브랜드 정비가능, 24시간 응급서비스, 해변 근처', '대형 정비베이, 24시간 운영, 바다뷰 대기실', '1층', NULL),

('대우카센터 사상점', '대우자동차 전문 서비스센터', '부산광역시 사상구 대동로 654', '051-2345-6789', 'sasang@daewoo.com',
 '678-90-12345', '정대우', 35.1695, 128.9914, 'APPROVED', true, true,
 '대우차 전문, 엔진오버홀, GM계열 전문', '전문 정비시설, 부품창고, 엔진전용베이', '1-2층', NULL),

-- 대구 지역 서비스센터
('BMW서비스 대구점', 'BMW 공식 서비스센터 대구점', '대구광역시 수성구 범어로 987', '053-1234-5678', 'daegu@bmw.com',
 '789-01-23456', '김독일', 35.8591, 128.6311, 'APPROVED', true, true,
 'BMW 전문정비, 순정부품 사용, 수입차 전문', '최신 BMW 전용장비, 고급 대기실, 전용주차장', '1-3층', 'https://daegu.bmw.co.kr'),

('벤츠서비스 달서점', '메르세데스-벤츠 공식 서비스센터', '대구광역시 달서구 월배로 246', '053-2345-6789', 'dalseo@benz.com',
 '890-12-34567', '박벤츠', 35.8242, 128.5374, 'APPROVED', true, true,
 '벤츠 전문정비, 고급차 전문, AMG 서비스', '프리미엄 서비스, 고객라운지, 프리미엄 주차', '1-2층', 'https://dalseo.mercedes-benz.co.kr'),

-- 인천 지역 서비스센터
('종합모터스 인천점', '종합 자동차 정비소 인천점', '인천광역시 남동구 구월로 135', '032-1234-5678', 'incheon@motors.com',
 '901-23-45678', '오인천', 37.4486, 126.7315, 'APPROVED', true, true,
 '모든 차종 정비, 합리적 가격, 공항 근처', '넓은 정비공간, 고객편의시설, 공항셔틀', '1층', NULL),

-- 광주 지역 서비스센터
('광주카센터 서구점', '광주 종합 자동차 서비스센터', '광주광역시 서구 상무대로 468', '062-1234-5678', 'seogu@gwangju.com',
 '012-34-56789', '김광주', 35.1522, 126.8889, 'APPROVED', true, true,
 '친환경 정비, 디젤차 전문, 하이브리드 전문', '친환경 정비시설, 대기실, 하이브리드 전용베이', '1층', NULL),

-- 대전 지역 서비스센터
('대전모터스 유성점', '대전 종합 자동차 정비소', '대전광역시 유성구 대학로 579', '042-1234-5678', 'yuseong@daejeon.com',
 '123-45-67890', '이대전', 36.3398, 127.3940, 'APPROVED', true, true,
 '학생할인, 합리적 가격, 대학가 위치', '학생 할인혜택, 무료 셔틀, 야간진료', '1층', NULL),

-- 울산 지역 서비스센터
('울산정비 남구점', '울산 종합 자동차 정비소', '울산광역시 남구 삼산로 789', '052-1234-5678', 'namgu@ulsan.com',
 '234-56-78901', '박울산', 35.5396, 129.3114, 'APPROVED', true, true,
 '현대차 본고장, 공업지역 특화, 상용차 전문', '상용차 전용베이, 대형차 정비가능, 24시간', '1-2층', NULL);

-- =====================================================
-- ADMIN USERS - 관리자 및 시스템 사용자
-- =====================================================

INSERT INTO users (user_uuid, email, password, name, phone, role, is_active, email_verified) VALUES
-- 시스템 관리자
('550e8400-e29b-41d4-a716-446655440000', 'system_admin@test.com', '$2a$12$8D7zQaGVF394BaWUF0gKrekUHai8G/Xb.u/yoEo.d3sBJkXyrUJlC', 
 '시스템관리자', '02-1234-5678', 'SYSTEM_ADMIN', true, true),

-- 고객 계정
('550e8400-e29b-41d4-a716-446655440001', 'customer_01@test.com', '$2a$12$8D7zQaGVF394BaWUF0gKrekUHai8G/Xb.u/yoEo.d3sBJkXyrUJlC',
 '최고관리자', '02-1234-5679', 'CUSTOMER', true, true),
('550e8400-e29b-41d4-a716-446655440002', 'customer_02@test.com', '$2a$12$8D7zQaGVF394BaWUF0gKrekUHai8G/Xb.u/yoEo.d3sBJkXyrUJlC',
 '최고관리자', '02-1234-5679', 'CUSTOMER', true, true),


-- 서비스센터 계정들
('550e8400-e29b-41d4-a716-446655440010', 'center_admin@hyundai.com', '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM.lbESZnQ8lKOD2kp4e',
 '현대모터스강남점', '02-1234-5678', 'CENTER_MANAGER', true, true);

-- =====================================================
-- SAMPLE VEHICLES - 테스트용 차량 데이터
-- =====================================================

INSERT INTO vehicles (vehicle_uuid, user_id, make, model, year, license_plate, vin, fuel_type, mileage, color, brand_id, model_id) VALUES
('550e8400-e29b-41d4-a716-446655440030', 2, '현대', '아반떼', 2022, '12가3456', 'KMHL14JA5NA123456', 'GASOLINE', 25000, '흰색', 1, 1),
('550e8400-e29b-41d4-a716-446655440031', 2, '기아', 'K5', 2021, '23나4567', 'KNAG34LA5MA234567', 'GASOLINE', 35000, '검은색', 2, 2),
('550e8400-e29b-41d4-a716-446655440032', 3, 'BMW', '320i', 2020, '34다5678', 'WBA8E5G57LNT12345', 'GASOLINE', 45000, '은색', 10, 22),
('550e8400-e29b-41d4-a716-446655440033', 3, '벤츠', 'C200', 2023, '45라6789', 'WDD2050831F123456', 'GASOLINE', 15000, '검은색', 9, 26);

-- =====================================================
-- NOTIFICATION TEMPLATES - 알림 템플릿
-- =====================================================

INSERT INTO notification_templates (
    template_uuid, name, type, channel, language, subject, title_template, content_template, variables, is_active
) VALUES
-- 예약 관련 템플릿
('template-reservation-confirmed-sms', '예약확인_SMS', 'RESERVATION_CONFIRMED', 'SMS', 'ko', NULL,
 '예약이 확인되었습니다', '안녕하세요 {{customerName}}님. {{serviceDate}}에 {{serviceCenterName}}에서 {{serviceType}} 예약이 확인되었습니다. 예약번호: {{reservationNumber}}',
 '{"customerName": "고객명", "serviceDate": "서비스 날짜", "serviceCenterName": "서비스센터명", "serviceType": "서비스 종류", "reservationNumber": "예약번호"}', true),

('template-reservation-confirmed-email', '예약확인_이메일', 'RESERVATION_CONFIRMED', 'EMAIL', 'ko', '[차케어] 예약이 확인되었습니다',
 '예약 확인 안내', '안녕하세요 {{customerName}}님.<br/><br/>{{serviceDate}}에 {{serviceCenterName}}에서 {{serviceType}} 예약이 확인되었습니다.<br/><br/>예약정보:<br/>- 예약번호: {{reservationNumber}}<br/>- 서비스: {{serviceType}}<br/>- 일시: {{serviceDate}}<br/>- 장소: {{serviceCenterName}}<br/>- 주소: {{serviceCenterAddress}}<br/>- 연락처: {{serviceCenterPhone}}<br/><br/>예약 시간 30분 전까지 도착해주시기 바랍니다.<br/><br/>감사합니다.',
 '{"customerName": "고객명", "serviceDate": "서비스 날짜", "serviceCenterName": "서비스센터명", "serviceType": "서비스 종류", "reservationNumber": "예약번호", "serviceCenterAddress": "서비스센터 주소", "serviceCenterPhone": "서비스센터 전화번호"}', true),

('template-reservation-reminder-sms', '예약알림_SMS', 'RESERVATION_REMINDER', 'SMS', 'ko', NULL,
 '예약 알림', '{{customerName}}님, 내일({{serviceDate}}) {{serviceCenterName}}에서 {{serviceType}} 예정입니다. 예약번호: {{reservationNumber}}',
 '{"customerName": "고객명", "serviceDate": "서비스 날짜", "serviceCenterName": "서비스센터명", "serviceType": "서비스 종류", "reservationNumber": "예약번호"}', true),

-- 결제 관련 템플릿  
('template-payment-completed-sms', '결제완료_SMS', 'PAYMENT_COMPLETED', 'SMS', 'ko', NULL,
 '결제가 완료되었습니다', '{{customerName}}님의 {{amount}}원 결제가 완료되었습니다. 결제번호: {{paymentId}}',
 '{"customerName": "고객명", "amount": "결제금액", "paymentId": "결제번호"}', true),

('template-payment-completed-email', '결제완료_이메일', 'PAYMENT_COMPLETED', 'EMAIL', 'ko', '[차케어] 결제가 완료되었습니다',
 '결제 완료 안내', '{{customerName}}님의 결제가 완료되었습니다.<br/><br/>결제정보:<br/>- 결제금액: {{amount}}원<br/>- 결제방법: {{paymentMethod}}<br/>- 결제번호: {{paymentId}}<br/>- 결제일시: {{paymentDate}}<br/><br/>영수증은 첨부파일을 확인해주세요.<br/><br/>감사합니다.',
 '{"customerName": "고객명", "amount": "결제금액", "paymentMethod": "결제방법", "paymentId": "결제번호", "paymentDate": "결제일시"}', true),

('template-payment-failed-sms', '결제실패_SMS', 'PAYMENT_FAILED', 'SMS', 'ko', NULL,
 '결제가 실패했습니다', '{{customerName}}님의 결제가 실패했습니다. 다시 시도해주세요. (사유: {{failureReason}})',
 '{"customerName": "고객명", "failureReason": "실패사유"}', true),

-- 서비스 관련 템플릿
('template-service-started-sms', '서비스시작_SMS', 'SERVICE_STARTED', 'SMS', 'ko', NULL,
 '서비스가 시작되었습니다', '{{customerName}}님의 {{serviceType}} 서비스가 시작되었습니다. 완료까지 약 {{estimatedTime}}분 소요됩니다.',
 '{"customerName": "고객명", "serviceType": "서비스 종류", "estimatedTime": "예상시간"}', true),

('template-service-completed-sms', '서비스완료_SMS', 'SERVICE_COMPLETED', 'SMS', 'ko', NULL,
 '서비스가 완료되었습니다', '{{customerName}}님의 {{serviceType}} 서비스가 완료되었습니다. 차량을 픽업해주세요.',
 '{"customerName": "고객명", "serviceType": "서비스 종류"}', true),

('template-service-completed-push', '서비스완료_푸시', 'SERVICE_COMPLETED', 'PUSH', 'ko', NULL,
 '서비스 완료', '{{serviceType}} 서비스가 완료되었습니다. 차량 픽업이 가능합니다.',
 '{"serviceType": "서비스 종류"}', true),

-- 견적 관련 템플릿
('template-quote-created-email', '견적서발송_이메일', 'QUOTE_CREATED', 'EMAIL', 'ko', '[차케어] 견적서가 발송되었습니다',
 '견적서 안내', '{{customerName}}님께 견적서를 발송드립니다.<br/><br/>견적정보:<br/>- 견적번호: {{quoteNumber}}<br/>- 총 금액: {{totalAmount}}원<br/>- 유효기간: {{validUntil}}<br/><br/>자세한 내용은 첨부된 견적서를 확인해주세요.<br/><br/>감사합니다.',
 '{"customerName": "고객명", "quoteNumber": "견적번호", "totalAmount": "총금액", "validUntil": "유효기간"}', true),

-- 리뷰 관련 템플릿
('template-review-request-sms', '리뷰요청_SMS', 'REVIEW_REQUEST', 'SMS', 'ko', NULL,
 '서비스 만족도를 알려주세요', '{{customerName}}님, {{serviceCenterName}}의 서비스는 어떠셨나요? 리뷰 작성하고 포인트 받으세요!',
 '{"customerName": "고객명", "serviceCenterName": "서비스센터명"}', true);

-- =====================================================
-- SERVICE CENTER OPERATING HOURS - 운영시간 설정
-- =====================================================

INSERT INTO service_center_operating_hours (
    service_center_id, current_status,
    weekly_schedule, default_settings
) VALUES
-- 현대모터스 강남점
(1, 'CLOSED', 
 '{"monday": {"open": "09:00", "close": "18:00", "isOpen": true}, "tuesday": {"open": "09:00", "close": "18:00", "isOpen": true}, "wednesday": {"open": "09:00", "close": "18:00", "isOpen": true}, "thursday": {"open": "09:00", "close": "18:00", "isOpen": true}, "friday": {"open": "09:00", "close": "18:00", "isOpen": true}, "saturday": {"open": "09:00", "close": "15:00", "isOpen": true}, "sunday": {"open": "", "close": "", "isOpen": false}}',
 '{"breakStartTime": "12:00", "breakEndTime": "13:00", "lastReservationTime": "17:00"}'),

-- 기아모터스 서초점
(2, 'CLOSED',
 '{"monday": {"open": "08:30", "close": "17:30", "isOpen": true}, "tuesday": {"open": "08:30", "close": "17:30", "isOpen": true}, "wednesday": {"open": "08:30", "close": "17:30", "isOpen": true}, "thursday": {"open": "08:30", "close": "17:30", "isOpen": true}, "friday": {"open": "08:30", "close": "17:30", "isOpen": true}, "saturday": {"open": "08:30", "close": "14:00", "isOpen": true}, "sunday": {"open": "", "close": "", "isOpen": false}}',
 '{"breakStartTime": "12:00", "breakEndTime": "13:00", "lastReservationTime": "16:30"}'),

-- 삼성카서비스 잠실점
(3, 'CLOSED',
 '{"monday": {"open": "09:00", "close": "19:00", "isOpen": true}, "tuesday": {"open": "09:00", "close": "19:00", "isOpen": true}, "wednesday": {"open": "09:00", "close": "19:00", "isOpen": true}, "thursday": {"open": "09:00", "close": "19:00", "isOpen": true}, "friday": {"open": "09:00", "close": "19:00", "isOpen": true}, "saturday": {"open": "09:00", "close": "16:00", "isOpen": true}, "sunday": {"open": "", "close": "", "isOpen": false}}',
 '{"breakStartTime": "12:00", "breakEndTime": "13:00", "lastReservationTime": "18:00"}');

-- =====================================================
-- NOTIFICATION SETTINGS - 사용자별 알림 설정
-- =====================================================

INSERT INTO notification_settings (user_id, sms_enabled, push_enabled, email_enabled, in_app_enabled) VALUES
(1, true, true, true, true),  -- admin
(2, true, true, true, true),  -- customer_01
(3, true, true, true, true),  -- customer_02
(4, true, false, true, true); -- 현대모터스강남점


-- =====================================================
-- 데이터 삽입 완료 확인
-- =====================================================

-- 데이터 삽입 확인 쿼리
SELECT 
    'Service Types' as table_name, COUNT(*) as count FROM service_types WHERE is_active = true
UNION ALL
SELECT 
    'Service Centers' as table_name, COUNT(*) as count FROM service_centers WHERE is_active = true
UNION ALL
SELECT 
    'Users' as table_name, COUNT(*) as count FROM users WHERE is_active = true
UNION ALL
SELECT 
    'Vehicles' as table_name, COUNT(*) as count FROM vehicles WHERE is_active = true
UNION ALL
SELECT 
    'Notification Templates' as table_name, COUNT(*) as count FROM notification_templates WHERE is_active = true
UNION ALL
SELECT 
    'Operating Hours' as table_name, COUNT(*) as count FROM service_center_operating_hours
UNION ALL
SELECT 
    'Notification Settings' as table_name, COUNT(*) as count FROM notification_settings;

-- 초기 데이터 삽입 완료
-- 총 서비스 타입: 40+개
-- 총 서비스센터: 12개 (전국 주요 도시)
-- 총 사용자: 7개 (관리자 2, 서비스센터 3, 고객 2)
-- 총 차량: 4대 (테스트용)
-- 총 알림 템플릿: 12개 (SMS, EMAIL, PUSH)
-- 
-- 실행 완료 후 애플리케이션에서 정상 동작 확인 가능 