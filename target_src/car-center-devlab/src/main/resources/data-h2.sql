-- H2 Initial Data for Car Center Application
-- Spring Boot Default Data File (data-h2.sql)

-- Insert basic vehicle brand data
INSERT INTO vehicle_brands (name, name_en, code, country, description, sort_order) VALUES
('현대', 'Hyundai', 'HYN', '대한민국', '현대자동차', 1),
('기아', 'Kia', 'KIA', '대한민국', '기아자동차', 2),
('삼성', 'Samsung', 'SMS', '대한민국', '삼성자동차', 3),
('BMW', 'BMW', 'BMW', '독일', 'BMW', 4),
('벤츠', 'Mercedes-Benz', 'MBZ', '독일', '메르세데스-벤츠', 5);

-- Insert basic vehicle models data
INSERT INTO vehicle_models (brand_id, name, name_en, code, category, start_year, description, sort_order) VALUES
(1, '아반떼', 'Avante', 'AVT', '준중형', 1990, '현대자동차 준중형 세단', 1),
(1, '소나타', 'Sonata', 'SNT', '중형', 1985, '현대자동차 중형 세단', 2),
(2, 'K5', 'K5', 'K5', '중형', 2010, '기아자동차 중형 세단', 1),
(4, '3시리즈', '3 Series', '3S', '중형', 1975, 'BMW 중형 세단', 1),
(5, 'C클래스', 'C-Class', 'C', '중형', 1993, '벤츠 중형 세단', 1);

-- Insert basic service type data
INSERT INTO service_types (name, description, category, estimated_duration, base_price, is_active) VALUES
('정기점검', '차량 정기 점검 서비스', '점검', 60, 50000, true),
('오일교환', '엔진오일 교환 서비스', '정비', 30, 80000, true),
('타이어교체', '타이어 교체 서비스', '정비', 45, 300000, true),
('브레이크패드교체', '브레이크 패드 교체 서비스', '정비', 90, 150000, true),
('배터리교체', '차량 배터리 교체 서비스', '정비', 30, 120000, true),
('에어컨점검', '에어컨 시스템 점검 및 정비', '정비', 45, 70000, true),
('브레이크오일교체', '브레이크 오일 교체', '정비', 45, 80000, true),
('타이어밸런싱', '타이어 밸런싱 조정', '정비', 40, 60000, true),
('배터리점검', '배터리 상태 점검', '점검', 20, 30000, true),
('전조등교체', '헤드라이트 전구 교체', '정비', 25, 50000, true);

-- Insert service centers data
INSERT INTO service_centers (
    name, description, address, phone_number, email, 
    business_number, owner_name, latitude, longitude,
    verification_status, is_active, is_operating,
    specialized_services, facilities, address_detail, website
) VALUES 
('현대모터스 강남점', '현대자동차 공식 서비스센터 강남점', '서울특별시 강남구 테헤란로 123', '02-1234-5678', 'gangnam@hyundai.com', 
 '123-45-67890', '김현대', 37.5012, 127.0396, 'APPROVED', true, true,
 '현대차 전문정비, 무상점검, 긴급출동', '리프트 10대, 대기실, 무료WiFi, 주차장', '1층', 'https://gangnam.hyundai.com'),

('기아모터스 서초점', '기아자동차 공식 서비스센터 서초점', '서울특별시 서초구 강남대로 456', '02-2345-6789', 'seocho@kia.com',
 '234-56-78901', '박기아', 37.4847, 127.0282, 'APPROVED', true, true,
 '기아차 전문정비, 신속정비, 부품교체', '리프트 8대, 고객휴게실, 주차장', '지하1층-지상2층', 'https://seocho.kia.com'),

('BMW서비스 대구점', 'BMW 공식 서비스센터 대구점', '대구광역시 수성구 범어로 987', '053-1234-5678', 'daegu@bmw.com',
 '789-01-23456', '김독일', 35.8591, 128.6311, 'APPROVED', true, true,
 'BMW 전문정비, 순정부품 사용', '최신 BMW 전용장비, 고급 대기실', '1-3층', 'https://daegu.bmw.co.kr');

-- Insert test users data
INSERT INTO users (user_uuid, email, password, name, phone, role, is_active, email_verified) VALUES
('550e8400-e29b-41d4-a716-446655440000', 'admin@test.com', '$2a$12$8D7zQaGVF394BaWUF0gKrekUHai8G/Xb.u/yoEo.d3sBJkXyrUJlC', 
 '시스템관리자', '02-1234-5678', 'SYSTEM_ADMIN', true, true),
('550e8400-e29b-41d4-a716-446655440001', 'customer1@test.com', '$2a$12$8D7zQaGVF394BaWUF0gKrekUHai8G/Xb.u/yoEo.d3sBJkXyrUJlC',
 '홍길동', '010-1234-5678', 'CUSTOMER', true, true),
('550e8400-e29b-41d4-a716-446655440002', 'customer2@test.com', '$2a$12$8D7zQaGVF394BaWUF0gKrekUHai8G/Xb.u/yoEo.d3sBJkXyrUJlC',
 '김영희', '010-2345-6789', 'CUSTOMER', true, true),
('550e8400-e29b-41d4-a716-446655440010', 'center@test.com', '$2a$12$8D7zQaGVF394BaWUF0gKrekUHai8G/Xb.u/yoEo.d3sBJkXyrUJlC',
 '현대모터스강남점', '02-1234-5678', 'CENTER_MANAGER', true, true);

-- Insert test vehicles data
INSERT INTO vehicles (vehicle_uuid, user_id, make, model, vehicle_year, license_plate, vin, fuel_type, mileage, color, brand_id, model_id) VALUES
('550e8400-e29b-41d4-a716-446655440030', 2, '현대', '아반떼', 2022, '12가3456', 'KMHL14JA5NA123456', 'GASOLINE', 25000, '흰색', 1, 1),
('550e8400-e29b-41d4-a716-446655440031', 2, '기아', 'K5', 2021, '23나4567', 'KNAG34LA5MA234567', 'GASOLINE', 35000, '검은색', 2, 3),
('550e8400-e29b-41d4-a716-446655440032', 3, 'BMW', '320i', 2020, '34다5678', 'WBA8E5G57LNT12345', 'GASOLINE', 45000, '은색', 4, 4),
('550e8400-e29b-41d4-a716-446655440033', 3, '벤츠', 'C200', 2023, '45라6789', 'WDD2050831F123456', 'GASOLINE', 15000, '검은색', 5, 5);

-- Insert basic notification templates
INSERT INTO notification_templates (
    template_uuid, name, type, channel, language, subject, title_template, content_template, variables, is_active
) VALUES
('template-reservation-sms', '예약확인_SMS', 'RESERVATION_CONFIRMED', 'SMS', 'ko', NULL,
 '예약이 확인되었습니다', '안녕하세요. 예약이 확인되었습니다. 예약번호: {{reservationNumber}}',
 '{"reservationNumber": "예약번호"}', true),
('template-payment-sms', '결제완료_SMS', 'PAYMENT_COMPLETED', 'SMS', 'ko', NULL,
 '결제가 완료되었습니다', '결제가 완료되었습니다. 결제번호: {{paymentId}}',
 '{"paymentId": "결제번호"}', true),
('template-service-sms', '서비스완료_SMS', 'SERVICE_COMPLETED', 'SMS', 'ko', NULL,
 '서비스가 완료되었습니다', '서비스가 완료되었습니다. 차량을 픽업해주세요.',
 '{}', true);

-- Insert service center operating hours
INSERT INTO service_center_operating_hours (
    service_center_id, current_status, weekly_schedule, default_settings
) VALUES
(1, 'CLOSED', 
 '{"monday": {"open": "09:00", "close": "18:00", "isOpen": true}, "tuesday": {"open": "09:00", "close": "18:00", "isOpen": true}, "wednesday": {"open": "09:00", "close": "18:00", "isOpen": true}, "thursday": {"open": "09:00", "close": "18:00", "isOpen": true}, "friday": {"open": "09:00", "close": "18:00", "isOpen": true}, "saturday": {"open": "09:00", "close": "15:00", "isOpen": true}, "sunday": {"isOpen": false}}',
 '{"breakStartTime": "12:00", "breakEndTime": "13:00"}'),
(2, 'CLOSED',
 '{"monday": {"open": "08:30", "close": "17:30", "isOpen": true}, "tuesday": {"open": "08:30", "close": "17:30", "isOpen": true}, "wednesday": {"open": "08:30", "close": "17:30", "isOpen": true}, "thursday": {"open": "08:30", "close": "17:30", "isOpen": true}, "friday": {"open": "08:30", "close": "17:30", "isOpen": true}, "saturday": {"open": "08:30", "close": "14:00", "isOpen": true}, "sunday": {"isOpen": false}}',
 '{"breakStartTime": "12:00", "breakEndTime": "13:00"}'),
(3, 'CLOSED',
 '{"monday": {"open": "09:00", "close": "19:00", "isOpen": true}, "tuesday": {"open": "09:00", "close": "19:00", "isOpen": true}, "wednesday": {"open": "09:00", "close": "19:00", "isOpen": true}, "thursday": {"open": "09:00", "close": "19:00", "isOpen": true}, "friday": {"open": "09:00", "close": "19:00", "isOpen": true}, "saturday": {"open": "09:00", "close": "16:00", "isOpen": true}, "sunday": {"isOpen": false}}',
 '{"breakStartTime": "12:00", "breakEndTime": "13:00"}');

-- Insert notification settings for users
INSERT INTO notification_settings (user_id, sms_enabled, push_enabled, email_enabled, in_app_enabled) VALUES
(1, true, true, true, true),  -- admin
(2, true, true, true, true),  -- customer1
(3, true, true, true, true),  -- customer2
(4, true, false, true, true); -- center manager 