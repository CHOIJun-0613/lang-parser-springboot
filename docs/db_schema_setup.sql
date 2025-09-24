-- PostgreSQL Database Schema Setup Script for DEV/PROD Environment
-- Execute this script manually in DBeaver for dev and prod environments
-- 
-- Instructions:
-- 1. Connect to PostgreSQL server using DBeaver
-- 2. Create database 'carcare_dev' for development or 'carcare_prod' for production
-- 3. Execute this script in the database
--
-- Database: carcare_dev (for development) or carcare_prod (for production)
-- Version: 1.0
-- Generated from existing PostgreSQL structure

-- Drop existing tables if they exist (for clean setup)
DROP TABLE IF EXISTS notification_templates CASCADE;
DROP TABLE IF EXISTS notification_settings CASCADE;
DROP TABLE IF EXISTS notifications CASCADE;
DROP TABLE IF EXISTS review_replies CASCADE;
DROP TABLE IF EXISTS reviews CASCADE;
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS quote_items CASCADE;
DROP TABLE IF EXISTS quotes CASCADE;
DROP TABLE IF EXISTS reservations CASCADE;
DROP TABLE IF EXISTS service_center_operating_hours CASCADE;
DROP TABLE IF EXISTS service_centers CASCADE;
DROP TABLE IF EXISTS service_types CASCADE;
DROP TABLE IF EXISTS vehicles CASCADE;
DROP TABLE IF EXISTS vehicle_models CASCADE;
DROP TABLE IF EXISTS vehicle_brands CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- 1. Users table - 사용자 정보 관리
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    user_uuid VARCHAR(36) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    role VARCHAR(20) DEFAULT 'CUSTOMER',
    is_active BOOLEAN DEFAULT true,
    email_verified BOOLEAN DEFAULT false,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Check constraints for users
ALTER TABLE users ADD CONSTRAINT users_role_check 
    CHECK (role IN ('CUSTOMER', 'CENTER_MANAGER', 'SYSTEM_ADMIN'));

-- Indexes for users
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_phone ON users(phone);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_created_at ON users(created_at);

-- 2. Vehicle brands table - 차량 브랜드 마스터 데이터
CREATE TABLE vehicle_brands (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    name_en VARCHAR(100) NOT NULL,
    code VARCHAR(10) UNIQUE,
    country VARCHAR(50) NOT NULL,
    description TEXT,
    logo_url VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for vehicle_brands
CREATE INDEX idx_vehicle_brands_name ON vehicle_brands(name);
CREATE INDEX idx_vehicle_brands_name_en ON vehicle_brands(name_en);
CREATE INDEX idx_vehicle_brands_code ON vehicle_brands(code);
CREATE INDEX idx_vehicle_brands_country ON vehicle_brands(country);
CREATE INDEX idx_vehicle_brands_is_active ON vehicle_brands(is_active);
CREATE INDEX idx_vehicle_brands_sort_order ON vehicle_brands(sort_order);

-- 3. Vehicle models table - 차량 모델 마스터 데이터
CREATE TABLE vehicle_models (
    id BIGSERIAL PRIMARY KEY,
    brand_id BIGINT NOT NULL,
    name VARCHAR(100) NOT NULL,
    name_en VARCHAR(100) NOT NULL,
    code VARCHAR(20),
    category VARCHAR(50),
    start_year INTEGER,
    end_year INTEGER,
    description TEXT,
    image_url VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_vehicle_models_brand_id FOREIGN KEY (brand_id) REFERENCES vehicle_brands(id)
);

-- Check constraints for vehicle_models
ALTER TABLE vehicle_models ADD CONSTRAINT chk_vehicle_models_years 
    CHECK (end_year IS NULL OR start_year IS NULL OR end_year >= start_year);

-- Indexes for vehicle_models
CREATE INDEX idx_vehicle_models_brand_id ON vehicle_models(brand_id);
CREATE INDEX idx_vehicle_models_name ON vehicle_models(name);
CREATE INDEX idx_vehicle_models_name_en ON vehicle_models(name_en);
CREATE INDEX idx_vehicle_models_code ON vehicle_models(code);
CREATE INDEX idx_vehicle_models_category ON vehicle_models(category);
CREATE INDEX idx_vehicle_models_start_year ON vehicle_models(start_year);
CREATE INDEX idx_vehicle_models_is_active ON vehicle_models(is_active);
CREATE INDEX idx_vehicle_models_sort_order ON vehicle_models(sort_order);

-- 4. Vehicles table - 사용자 차량 정보
CREATE TABLE vehicles (
    id BIGSERIAL PRIMARY KEY,
    vehicle_uuid VARCHAR(36) NOT NULL UNIQUE,
    user_id BIGINT NOT NULL,
    make VARCHAR(100) NOT NULL,
    model VARCHAR(100) NOT NULL,
    year INTEGER NOT NULL,
    license_plate VARCHAR(20) NOT NULL UNIQUE,
    vin VARCHAR(17) UNIQUE,
    engine_type VARCHAR(50),
    fuel_type VARCHAR(20),
    mileage INTEGER DEFAULT 0,
    color VARCHAR(50),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    brand_id BIGINT,
    model_id BIGINT,
    CONSTRAINT vehicles_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT fk_vehicles_brand_id FOREIGN KEY (brand_id) REFERENCES vehicle_brands(id),
    CONSTRAINT fk_vehicles_model_id FOREIGN KEY (model_id) REFERENCES vehicle_models(id)
);

-- Check constraints for vehicles
ALTER TABLE vehicles ADD CONSTRAINT vehicles_year_check 
    CHECK (year >= 1900 AND year <= EXTRACT(YEAR FROM CURRENT_DATE) + 1);
ALTER TABLE vehicles ADD CONSTRAINT vehicles_fuel_type_check 
    CHECK (fuel_type IN ('GASOLINE', 'DIESEL', 'HYBRID', 'ELECTRIC', 'LPG'));

-- Indexes for vehicles
CREATE INDEX idx_vehicles_user_id ON vehicles(user_id);
CREATE INDEX idx_vehicles_license_plate ON vehicles(license_plate);
CREATE INDEX idx_vehicles_make_model ON vehicles(make, model);
CREATE INDEX idx_vehicles_vin ON vehicles(vin);
CREATE INDEX idx_vehicles_brand_id ON vehicles(brand_id);
CREATE INDEX idx_vehicles_model_id ON vehicles(model_id);

-- 5. Service types table - 서비스 종류 마스터 데이터
CREATE TABLE service_types (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL,
    estimated_duration INTEGER,
    base_price NUMERIC(10,2),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Service centers table - 서비스센터 정보
CREATE TABLE service_centers (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    address TEXT NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    email VARCHAR(255),
    average_rating NUMERIC(2,1) DEFAULT 0.0,
    review_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    address_detail VARCHAR(100),
    website VARCHAR(255),
    business_number VARCHAR(20) NOT NULL,
    owner_name VARCHAR(50) NOT NULL,
    latitude NUMERIC(10,8),
    longitude NUMERIC(11,8),
    verification_status VARCHAR(20) DEFAULT 'PENDING',
    verification_date TIMESTAMP,
    is_operating BOOLEAN DEFAULT false,
    specialized_services TEXT,
    facilities TEXT,
    special_notes TEXT,
    image_url VARCHAR(255),
    created_by BIGINT,
    updated_by BIGINT
);

-- Check constraints for service_centers
ALTER TABLE service_centers ADD CONSTRAINT service_centers_rating_check 
    CHECK (average_rating >= 0.0 AND average_rating <= 5.0);

-- Indexes for service_centers
CREATE INDEX idx_service_centers_is_active ON service_centers(is_active);
CREATE INDEX idx_service_centers_rating ON service_centers(average_rating);

-- 7. Service center operating hours table - 서비스센터 운영시간 관리
CREATE TABLE service_center_operating_hours (
    id BIGSERIAL PRIMARY KEY,
    service_center_id BIGINT NOT NULL UNIQUE,
    weekly_schedule JSONB,
    special_dates JSONB,
    temporary_closures JSONB,
    default_settings JSONB,
    current_status VARCHAR(20) DEFAULT 'CLOSED',
    next_status_change_at TIMESTAMP WITH TIME ZONE,
    last_status_update_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by BIGINT,
    updated_by BIGINT,
    CONSTRAINT fk_operating_hours_service_center FOREIGN KEY (service_center_id) REFERENCES service_centers(id),
    CONSTRAINT uk_operating_hours_service_center_id UNIQUE (service_center_id)
);

-- Check constraints for service_center_operating_hours
ALTER TABLE service_center_operating_hours ADD CONSTRAINT chk_operating_hours_current_status 
    CHECK (current_status IN ('OPEN', 'CLOSED', 'BREAK', 'HOLIDAY'));

-- Indexes for service_center_operating_hours
CREATE INDEX idx_operating_hours_service_center_id ON service_center_operating_hours(service_center_id);
CREATE INDEX idx_operating_hours_current_status ON service_center_operating_hours(current_status);
CREATE INDEX idx_operating_hours_next_change ON service_center_operating_hours(next_status_change_at);
CREATE INDEX idx_operating_hours_created_at ON service_center_operating_hours(created_at);

-- 8. Reservations table - 서비스 예약 정보
CREATE TABLE reservations (
    id BIGSERIAL PRIMARY KEY,
    reservation_uuid VARCHAR(36) NOT NULL UNIQUE,
    user_id BIGINT NOT NULL,
    vehicle_id BIGINT NOT NULL,
    service_center_id BIGINT NOT NULL,
    service_type_id BIGINT NOT NULL,
    status VARCHAR(20) DEFAULT 'PENDING',
    scheduled_date TIMESTAMP NOT NULL,
    estimated_duration INTEGER,
    customer_notes TEXT,
    mechanic_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    confirmed_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    cancellation_reason TEXT,
    CONSTRAINT reservations_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT reservations_vehicle_id_fkey FOREIGN KEY (vehicle_id) REFERENCES vehicles(id),
    CONSTRAINT reservations_service_center_id_fkey FOREIGN KEY (service_center_id) REFERENCES service_centers(id),
    CONSTRAINT reservations_service_type_id_fkey FOREIGN KEY (service_type_id) REFERENCES service_types(id)
);

-- Check constraints for reservations
ALTER TABLE reservations ADD CONSTRAINT reservations_status_check 
    CHECK (status IN ('PENDING', 'CONFIRMED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED', 'NO_SHOW'));

-- Indexes for reservations
CREATE INDEX idx_reservations_user_id ON reservations(user_id);
CREATE INDEX idx_reservations_vehicle_id ON reservations(vehicle_id);
CREATE INDEX idx_reservations_service_center_id ON reservations(service_center_id);
CREATE INDEX idx_reservations_status ON reservations(status);
CREATE INDEX idx_reservations_scheduled_date ON reservations(scheduled_date);

-- 9. Quotes table - 견적서 정보
CREATE TABLE quotes (
    id BIGSERIAL PRIMARY KEY,
    quote_uuid UUID NOT NULL UNIQUE,
    reservation_id BIGINT NOT NULL,
    labor_cost NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    parts_cost NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    tax_amount NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    total_amount NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    status VARCHAR(20) DEFAULT 'DRAFT',
    valid_until TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    discount_amount NUMERIC(10,2) DEFAULT 0.00,
    approved_at TIMESTAMP WITH TIME ZONE,
    rejected_at TIMESTAMP WITH TIME ZONE,
    rejection_reason TEXT,
    CONSTRAINT quotes_reservation_id_fkey FOREIGN KEY (reservation_id) REFERENCES reservations(id)
);

-- Check constraints for quotes
ALTER TABLE quotes ADD CONSTRAINT quotes_status_check 
    CHECK (status IN ('DRAFT', 'PENDING', 'APPROVED', 'REJECTED', 'EXPIRED'));

-- Indexes for quotes
CREATE INDEX idx_quotes_reservation_id ON quotes(reservation_id);
CREATE INDEX idx_quotes_status ON quotes(status);
CREATE INDEX idx_quotes_valid_until ON quotes(valid_until);

-- 10. Quote items table - 견적 항목 정보
CREATE TABLE quote_items (
    id BIGSERIAL PRIMARY KEY,
    quote_id BIGINT NOT NULL,
    item_type VARCHAR(20) NOT NULL,
    description TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price NUMERIC(10,2) NOT NULL,
    total_price NUMERIC(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    warranty_period INTEGER,
    notes TEXT,
    CONSTRAINT quote_items_quote_id_fkey FOREIGN KEY (quote_id) REFERENCES quotes(id)
);

-- Indexes for quote_items
CREATE INDEX idx_quote_items_quote_id ON quote_items(quote_id);

-- 11. Payments table - 결제 정보
CREATE TABLE payments (
    id BIGSERIAL PRIMARY KEY,
    payment_uuid VARCHAR(36) NOT NULL UNIQUE,
    reservation_id BIGINT NOT NULL,
    quote_id BIGINT,
    amount NUMERIC(10,2) NOT NULL,
    payment_method VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'PENDING',
    transaction_id VARCHAR(255),
    payment_gateway VARCHAR(50),
    paid_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    receipt_url VARCHAR(500),
    CONSTRAINT payments_reservation_id_fkey FOREIGN KEY (reservation_id) REFERENCES reservations(id),
    CONSTRAINT payments_quote_id_fkey FOREIGN KEY (quote_id) REFERENCES quotes(id)
);

-- Check constraints for payments
ALTER TABLE payments ADD CONSTRAINT payments_status_check 
    CHECK (status IN ('PENDING', 'COMPLETED', 'FAILED', 'CANCELLED', 'REFUNDED', 'PARTIAL_REFUND'));
ALTER TABLE payments ADD CONSTRAINT payments_payment_method_check 
    CHECK (payment_method IN ('CARD', 'BANK_TRANSFER', 'CASH', 'VIRTUAL_ACCOUNT', 'MOBILE_PAYMENT'));

-- Indexes for payments
CREATE INDEX idx_payments_reservation_id ON payments(reservation_id);
CREATE INDEX idx_payments_status ON payments(status);
CREATE INDEX idx_payments_paid_at ON payments(paid_at);

-- 12. Reviews table - 서비스 리뷰 정보
CREATE TABLE reviews (
    id BIGSERIAL PRIMARY KEY,
    review_uuid VARCHAR(36) NOT NULL UNIQUE,
    reservation_id BIGINT NOT NULL,
    rating INTEGER NOT NULL,
    comment TEXT,
    is_visible BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    review_images TEXT,
    CONSTRAINT reviews_reservation_id_fkey FOREIGN KEY (reservation_id) REFERENCES reservations(id)
);

-- Check constraints for reviews
ALTER TABLE reviews ADD CONSTRAINT reviews_rating_check 
    CHECK (rating >= 1 AND rating <= 5);

-- Indexes for reviews
CREATE INDEX idx_reviews_reservation_id ON reviews(reservation_id);
CREATE INDEX idx_reviews_rating ON reviews(rating);
CREATE INDEX idx_reviews_is_visible ON reviews(is_visible);

-- 13. Review replies table - 리뷰 답글 정보
CREATE TABLE review_replies (
    id BIGSERIAL PRIMARY KEY,
    review_id BIGINT NOT NULL,
    author_id BIGINT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT review_replies_review_id_fkey FOREIGN KEY (review_id) REFERENCES reviews(id),
    CONSTRAINT review_replies_author_id_fkey FOREIGN KEY (author_id) REFERENCES users(id)
);

-- Indexes for review_replies
CREATE INDEX idx_review_replies_review_id ON review_replies(review_id);
CREATE INDEX idx_review_replies_author_id ON review_replies(author_id);

-- 14. Notifications table - 알림 정보
CREATE TABLE notifications (
    id BIGSERIAL PRIMARY KEY,
    notification_uuid VARCHAR(36) NOT NULL UNIQUE,
    user_id BIGINT NOT NULL,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT false,
    related_entity_type VARCHAR(50),
    related_entity_id BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Indexes for notifications
CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_type ON notifications(type);
CREATE INDEX idx_notifications_is_read ON notifications(is_read);
CREATE INDEX idx_notifications_created_at ON notifications(created_at);

-- 15. Notification settings table - 사용자별 알림 설정
CREATE TABLE notification_settings (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE,
    sms_enabled BOOLEAN DEFAULT true,
    push_enabled BOOLEAN DEFAULT true,
    email_enabled BOOLEAN DEFAULT true,
    in_app_enabled BOOLEAN DEFAULT true,
    night_mode_enabled BOOLEAN DEFAULT false,
    quiet_start_hour INTEGER DEFAULT 22,
    quiet_end_hour INTEGER DEFAULT 8,
    promotion_enabled BOOLEAN DEFAULT true,
    timezone VARCHAR(50) DEFAULT 'Asia/Seoul',
    language VARCHAR(10) DEFAULT 'ko',
    type_settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT notification_settings_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Indexes for notification_settings
CREATE INDEX idx_notification_settings_user_id ON notification_settings(user_id);

-- 16. Notification templates table - 알림 템플릿
CREATE TABLE notification_templates (
    id BIGSERIAL PRIMARY KEY,
    template_uuid VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(100) NOT NULL,
    channel VARCHAR(50) NOT NULL,
    language VARCHAR(10) NOT NULL DEFAULT 'ko',
    subject VARCHAR(500),
    title_template TEXT,
    content_template TEXT NOT NULL,
    variables JSONB,
    is_active BOOLEAN DEFAULT true,
    version INTEGER DEFAULT 1,
    description TEXT,
    created_by BIGINT,
    updated_by BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for notification_templates
CREATE INDEX idx_notification_templates_type ON notification_templates(type);
CREATE INDEX idx_notification_templates_channel ON notification_templates(channel);
CREATE INDEX idx_notification_templates_language ON notification_templates(language);
CREATE INDEX idx_notification_templates_active ON notification_templates(is_active);
CREATE INDEX idx_notification_templates_type_channel ON notification_templates(type, channel);
CREATE INDEX idx_notification_templates_type_channel_lang ON notification_templates(type, channel, language);

-- Insert basic vehicle brand data
INSERT INTO vehicle_brands (name, name_en, code, country, description, sort_order) VALUES
('현대', 'Hyundai', 'HYN', '대한민국', '현대자동차', 1),
('기아', 'Kia', 'KIA', '대한민국', '기아자동차', 2),
('삼성', 'Samsung', 'SMS', '대한민국', '삼성자동차 (구 르노삼성)', 3),
('쌍용', 'SsangYong', 'SSY', '대한민국', '쌍용자동차', 4),
('대우', 'Daewoo', 'DAE', '대한민국', '대우자동차 (구 GM대우)', 5),
('토요타', 'Toyota', 'TOY', '일본', '토요타자동차', 6),
('혼다', 'Honda', 'HON', '일본', '혼다자동차', 7),
('닛산', 'Nissan', 'NIS', '일본', '닛산자동차', 8),
('벤츠', 'Mercedes-Benz', 'MBZ', '독일', '메르세데스-벤츠', 9),
('BMW', 'BMW', 'BMW', '독일', 'BMW', 10),
('아우디', 'Audi', 'AUD', '독일', '아우디', 11),
('폭스바겐', 'Volkswagen', 'VW', '독일', '폭스바겐', 12),
('포드', 'Ford', 'FOR', '미국', '포드자동차', 13),
('쉐보레', 'Chevrolet', 'CHE', '미국', '쉐보레', 14),
('캐딜락', 'Cadillac', 'CAD', '미국', '캐딜락', 15),
('볼보', 'Volvo', 'VOL', '스웨덴', '볼보자동차', 16),
('재규어', 'Jaguar', 'JAG', '영국', '재규어', 17),
('랜드로버', 'Land Rover', 'LR', '영국', '랜드로버', 18),
('렉서스', 'Lexus', 'LEX', '일본', '렉서스', 19),
('인피니티', 'Infiniti', 'INF', '일본', '인피니티', 20);

-- Insert popular vehicle models data
INSERT INTO vehicle_models (brand_id, name, name_en, code, category, start_year, end_year, description, sort_order) VALUES
-- Hyundai models
(1, '아반떼', 'Avante', 'AVT', '준중형', 1990, NULL, '현대자동차 준중형 세단', 1),
(1, '소나타', 'Sonata', 'SNT', '중형', 1985, NULL, '현대자동차 중형 세단', 2),
(1, '그랜저', 'Grandeur', 'GRD', '대형', 1986, NULL, '현대자동차 대형 세단', 3),
(1, '투싼', 'Tucson', 'TCS', 'SUV', 2004, NULL, '현대자동차 중형 SUV', 4),
(1, '싼타페', 'Santa Fe', 'STF', 'SUV', 2000, NULL, '현대자동차 대형 SUV', 5),
(1, '코나', 'Kona', 'KON', 'SUV', 2017, NULL, '현대자동차 소형 SUV', 6),
-- Kia models
(2, 'K3', 'K3', 'K3', '준중형', 2012, NULL, '기아자동차 준중형 세단', 1),
(2, 'K5', 'K5', 'K5', '중형', 2010, NULL, '기아자동차 중형 세단', 2),
(2, 'K7', 'K7', 'K7', '대형', 2009, NULL, '기아자동차 대형 세단', 3),
(2, '스포티지', 'Sportage', 'SPT', 'SUV', 1993, NULL, '기아자동차 중형 SUV', 4),
(2, '쏘렌토', 'Sorento', 'SOR', 'SUV', 2002, NULL, '기아자동차 대형 SUV', 5),
(2, '셀토스', 'Seltos', 'SEL', 'SUV', 2019, NULL, '기아자동차 소형 SUV', 6),
-- Toyota models
(6, '캠리', 'Camry', 'CAM', '중형', 1982, NULL, '토요타 중형 세단', 1),
(6, '아발론', 'Avalon', 'AVL', '대형', 1994, NULL, '토요타 대형 세단', 2),
(6, 'RAV4', 'RAV4', 'RAV4', 'SUV', 1994, NULL, '토요타 중형 SUV', 3),
(6, '하이랜더', 'Highlander', 'HLD', 'SUV', 2000, NULL, '토요타 대형 SUV', 4),
(6, '프리우스', 'Prius', 'PRI', '하이브리드', 1997, NULL, '토요타 하이브리드 세단', 5),
-- BMW models
(10, '3시리즈', '3 Series', '3S', '중형', 1975, NULL, 'BMW 중형 세단', 1),
(10, '5시리즈', '5 Series', '5S', '대형', 1972, NULL, 'BMW 대형 세단', 2),
(10, '7시리즈', '7 Series', '7S', '최고급', 1977, NULL, 'BMW 최고급 세단', 3),
(10, 'X3', 'X3', 'X3', 'SUV', 2003, NULL, 'BMW 중형 SUV', 4),
(10, 'X5', 'X5', 'X5', 'SUV', 1999, NULL, 'BMW 대형 SUV', 5),
-- Mercedes-Benz models
(9, 'C클래스', 'C-Class', 'C', '중형', 1993, NULL, '벤츠 중형 세단', 1),
(9, 'E클래스', 'E-Class', 'E', '대형', 1993, NULL, '벤츠 대형 세단', 2),
(9, 'S클래스', 'S-Class', 'S', '최고급', 1972, NULL, '벤츠 최고급 세단', 3),
(9, 'GLC', 'GLC', 'GLC', 'SUV', 2015, NULL, '벤츠 중형 SUV', 4),
(9, 'GLE', 'GLE', 'GLE', 'SUV', 2015, NULL, '벤츠 대형 SUV', 5);

-- Insert basic service type data
INSERT INTO service_types (name, description, category, estimated_duration, base_price) VALUES
('정기점검', '차량 정기 점검 서비스', '점검', 60, 50000),
('오일교환', '엔진오일 교환 서비스', '정비', 30, 80000),
('타이어교체', '타이어 교체 서비스', '정비', 45, 300000),
('브레이크패드교체', '브레이크 패드 교체 서비스', '정비', 90, 150000),
('에어컨점검', '에어컨 시스템 점검 및 정비', '점검', 45, 70000),
('배터리교체', '차량 배터리 교체 서비스', '정비', 30, 120000),
('전체점검', '차량 전체 종합 점검', '점검', 120, 100000),
('변속기오일교환', '변속기 오일 교환 서비스', '정비', 60, 150000),
('냉각수교체', '엔진 냉각수 교체 서비스', '정비', 45, 80000),
('와이퍼교체', '와이퍼 블레이드 교체', '정비', 15, 30000);

-- Add comments for documentation
COMMENT ON DATABASE carcare_dev IS 'Car Center Application Development Database';
COMMENT ON DATABASE carcare_prod IS 'Car Center Application Production Database';

-- Schema setup completed
-- Total tables created: 16
-- Total indexes created: 50+
-- Total foreign key constraints: 12
-- Total check constraints: 8
-- 
-- Execute the following query to verify the setup:
-- SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE' ORDER BY table_name; 