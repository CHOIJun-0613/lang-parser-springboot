package com.carcare.domain.vehicle.validator;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import com.carcare.domain.vehicle.dto.VehicleDto;
import com.carcare.domain.vehicle.entity.Vehicle;
import com.carcare.domain.vehicle.exception.DuplicateLicensePlateException;
import com.carcare.domain.vehicle.exception.InvalidVehicleDataException;
import com.carcare.domain.vehicle.exception.VehicleAccessDeniedException;
import com.carcare.domain.vehicle.exception.VehicleNotFoundException;
import com.carcare.domain.vehicle.repository.VehicleRepository;
import com.carcare.domain.vehicle.service.VehicleBusinessRuleService;

import lombok.extern.slf4j.Slf4j;

import java.time.LocalDateTime;
import java.util.regex.Pattern;

/**
 * 차량 데이터 검증 클래스
 */
@Slf4j
@Component
public class VehicleValidator {
    
    private final VehicleRepository vehicleRepository;
    private final VehicleBusinessRuleService businessRuleService;
    
    // 차량번호 정규식 패턴
    private static final Pattern LICENSE_PLATE_PATTERN = Pattern.compile(
        "^\\d{2,3}[가-힣]\\d{4}$|^[가-힣]\\d{2}[가-힣]\\d{4}$|^\\d{3}[가-힣]\\d{4}$"
    );
    
    // VIN 번호 정규식 패턴 (17자리 영숫자)
    private static final Pattern VIN_PATTERN = Pattern.compile("^[A-HJ-NPR-Z0-9]{17}$");
    
    // 연식 범위
    private static final int MIN_YEAR = 1900;
    private static final int MAX_FUTURE_YEARS = 1; // 현재 연도 + 1년까지 허용
    
    @Autowired
    public VehicleValidator(VehicleRepository vehicleRepository, VehicleBusinessRuleService businessRuleService) {
        this.vehicleRepository = vehicleRepository;
        this.businessRuleService = businessRuleService;
    }
    
    /**
     * 차량 등록 데이터 검증
     */
    public void validateForRegistration(VehicleDto.Request request) {
        log.debug("Validating vehicle registration data: {}", request.getLicensePlate());
        
        // 기본 데이터 검증
        validateBasicData(request);
        
        // 차량번호 중복 검증
        validateLicensePlateUniqueness(request.getLicensePlate(), null);
        
        // 차량 연식 비즈니스 규칙 검증
        businessRuleService.validateVehicleAgeConstraints(request.getYear());
        
        log.debug("Vehicle registration validation completed successfully");
    }
    
    /**
     * 차량 수정 데이터 검증
     */
    public void validateForUpdate(Long vehicleId, VehicleDto.Request request) {
        log.debug("Validating vehicle update data: vehicleId={}, licensePlate={}", vehicleId, request.getLicensePlate());
        
        // 기본 데이터 검증
        validateBasicData(request);
        
        // 기존 차량 정보 조회
        Vehicle existingVehicle = vehicleRepository.findById(vehicleId)
                .orElseThrow(() -> new VehicleNotFoundException(vehicleId));
        
        // 차량번호 변경 여부 확인 및 제약 조건 검증
        boolean isLicensePlateChange = !existingVehicle.getLicensePlate().equals(request.getLicensePlate());
        businessRuleService.validateVehicleUpdateConstraints(vehicleId, isLicensePlateChange);
        
        // 차량번호 중복 검증 (본인 차량 제외)
        if (isLicensePlateChange) {
            validateLicensePlateUniqueness(request.getLicensePlate(), vehicleId);
        }
        
        log.debug("Vehicle update validation completed successfully");
    }
    
    /**
     * 차량 소유권 검증
     */
    public void validateOwnership(Long vehicleId, Long userId) {
        log.debug("Validating vehicle ownership: vehicleId={}, userId={}", vehicleId, userId);
        
        if (!vehicleRepository.isVehicleOwnedByUser(vehicleId, userId)) {
            throw new VehicleAccessDeniedException(userId, vehicleId);
        }
        
        log.debug("Vehicle ownership validation passed");
    }
    
    /**
     * 차량 존재 여부 검증
     */
    public Vehicle validateAndGetVehicle(Long vehicleId) {
        log.debug("Validating vehicle existence: vehicleId={}", vehicleId);
        
        return vehicleRepository.findById(vehicleId)
                .orElseThrow(() -> new VehicleNotFoundException(vehicleId));
    }
    
    /**
     * 기본 데이터 검증
     */
    private void validateBasicData(VehicleDto.Request request) {
        // 필수 필드 검증
        validateRequired(request);
        
        // 차량번호 형식 검증
        validateLicensePlateFormat(request.getLicensePlate());
        
        // 연식 검증
        validateYear(request.getYear());
        
        // 주행거리 검증
        validateMileage(request.getMileage());
        
        // VIN 번호 검증 (선택적)
        if (request.getVin() != null && !request.getVin().trim().isEmpty()) {
            validateVin(request.getVin());
        }
        
        // 제조사/모델 검증
        validateMakeAndModel(request.getMake(), request.getModel());
    }
    
    /**
     * 필수 필드 검증
     */
    private void validateRequired(VehicleDto.Request request) {
        if (request.getMake() == null || request.getMake().trim().isEmpty()) {
            throw new InvalidVehicleDataException("제조사는 필수입니다");
        }
        
        if (request.getModel() == null || request.getModel().trim().isEmpty()) {
            throw new InvalidVehicleDataException("모델명은 필수입니다");
        }
        
        if (request.getYear() == null) {
            throw new InvalidVehicleDataException("연식은 필수입니다");
        }
        
        if (request.getLicensePlate() == null || request.getLicensePlate().trim().isEmpty()) {
            throw new InvalidVehicleDataException("차량번호는 필수입니다");
        }
    }
    
    /**
     * 차량번호 형식 검증
     */
    private void validateLicensePlateFormat(String licensePlate) {
        if (!LICENSE_PLATE_PATTERN.matcher(licensePlate).matches()) {
            throw new InvalidVehicleDataException("올바른 차량번호 형식이 아닙니다: " + licensePlate);
        }
    }
    
    /**
     * 차량번호 중복 검증
     */
    private void validateLicensePlateUniqueness(String licensePlate, Long excludeVehicleId) {
        boolean exists;
        
        if (excludeVehicleId != null) {
            exists = vehicleRepository.existsByLicensePlateAndNotId(licensePlate, excludeVehicleId);
        } else {
            exists = vehicleRepository.existsByLicensePlate(licensePlate);
        }
        
        if (exists) {
            throw new DuplicateLicensePlateException(licensePlate);
        }
    }
    
    /**
     * 연식 검증
     */
    private void validateYear(Integer year) {
        int currentYear = LocalDateTime.now().getYear();
        int maxYear = currentYear + MAX_FUTURE_YEARS;
        
        if (year < MIN_YEAR) {
            throw new InvalidVehicleDataException("연식은 " + MIN_YEAR + "년 이후여야 합니다");
        }
        
        if (year > maxYear) {
            throw new InvalidVehicleDataException("연식은 " + maxYear + "년을 초과할 수 없습니다");
        }
    }
    
    /**
     * 주행거리 검증
     */
    private void validateMileage(Integer mileage) {
        if (mileage != null && mileage < 0) {
            throw new InvalidVehicleDataException("주행거리는 0 이상이어야 합니다");
        }
        
        // 최대 주행거리 검증 (일반적으로 500만km 이상은 비현실적)
        if (mileage != null && mileage > 5_000_000) {
            throw new InvalidVehicleDataException("주행거리가 너무 큽니다: " + mileage + "km");
        }
    }
    
    /**
     * VIN 번호 검증
     */
    private void validateVin(String vin) {
        if (vin.length() != 17) {
            throw new InvalidVehicleDataException("차대번호(VIN)는 17자리여야 합니다");
        }
        
        if (!VIN_PATTERN.matcher(vin.toUpperCase()).matches()) {
            throw new InvalidVehicleDataException("올바른 차대번호(VIN) 형식이 아닙니다");
        }
        
        // VIN에서 금지된 문자 체크 (I, O, Q는 사용하지 않음)
        if (vin.toUpperCase().matches(".*[IOQ].*")) {
            throw new InvalidVehicleDataException("차대번호(VIN)에는 I, O, Q 문자를 사용할 수 없습니다");
        }
    }
    
    /**
     * 제조사/모델 검증
     */
    private void validateMakeAndModel(String make, String model) {
        // 제조사명 길이 검증
        if (make.length() > 100) {
            throw new InvalidVehicleDataException("제조사명은 100자 이하여야 합니다");
        }
        
        // 모델명 길이 검증
        if (model.length() > 100) {
            throw new InvalidVehicleDataException("모델명은 100자 이하여야 합니다");
        }
        
        // 특수문자 검증 (영문, 한글, 숫자, 공백, 하이픈만 허용)
        Pattern namePattern = Pattern.compile("^[가-힣a-zA-Z0-9\\s\\-]+$");
        
        if (!namePattern.matcher(make).matches()) {
            throw new InvalidVehicleDataException("제조사명에 허용되지 않는 문자가 포함되어 있습니다");
        }
        
        if (!namePattern.matcher(model).matches()) {
            throw new InvalidVehicleDataException("모델명에 허용되지 않는 문자가 포함되어 있습니다");
        }
    }
    
    /**
     * 차량 삭제 가능 여부 검증
     */
    public void validateForDeletion(Long vehicleId, Long userId) {
        log.debug("Validating vehicle for deletion: vehicleId={}, userId={}", vehicleId, userId);
        
        // 차량 존재 및 소유권 검증
        Vehicle vehicle = validateAndGetVehicle(vehicleId);
        validateOwnership(vehicleId, userId);
        
        // 삭제 제약 조건 검증 (예약, 정비 등)
        businessRuleService.validateVehicleDeletionConstraints(vehicleId);
        
        log.debug("Vehicle deletion validation completed successfully");
    }
    
    /**
     * 차량 상태 검증
     */
    public void validateVehicleStatus(Vehicle vehicle) {
        if (vehicle.getIsActive() == null || !vehicle.getIsActive()) {
            throw new InvalidVehicleDataException("비활성화된 차량입니다");
        }
    }
    
    /**
     * 연료타입 검증
     */
    public void validateFuelType(Vehicle.FuelType fuelType) {
        if (fuelType == null) {
            return; // 연료타입은 선택사항
        }
        
        // 연료타입 유효성 검증은 enum 자체에서 처리됨
        log.debug("Fuel type validation passed: {}", fuelType);
    }
} 