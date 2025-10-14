package com.carcare.domain.vehicle.service;

import org.springframework.stereotype.Service;

import com.carcare.domain.vehicle.exception.InvalidVehicleDataException;

import lombok.extern.slf4j.Slf4j;

/**
 * 차량 비즈니스 규칙 서비스
 * 예약, 정비 이력 등과 연관된 비즈니스 규칙을 검증
 */
@Slf4j
@Service
public class VehicleBusinessRuleService {
    
    /**
     * 차량 삭제 가능 여부 검증 (예약 존재 여부 확인)
     * 
     * @param vehicleId 차량 ID
     * @throws InvalidVehicleDataException 활성 예약이 있는 경우
     */
    public void validateVehicleDeletionConstraints(Long vehicleId) {
        log.debug("Validating vehicle deletion constraints: vehicleId={}", vehicleId);
        
        // TODO: 향후 예약 시스템 구현 시 활성 예약 확인
        // if (hasActiveReservations(vehicleId)) {
        //     throw new InvalidVehicleDataException("예약이 있는 차량은 삭제할 수 없습니다");
        // }
        
        // TODO: 향후 정비 이력 시스템 구현 시 진행 중인 정비 확인
        // if (hasOngoingMaintenance(vehicleId)) {
        //     throw new InvalidVehicleDataException("정비 중인 차량은 삭제할 수 없습니다");
        // }
        
        log.debug("Vehicle deletion constraints validation passed");
    }
    
    /**
     * 차량 정보 수정 가능 여부 검증
     * 
     * @param vehicleId 차량 ID
     * @param isLicensePlateChange 차량번호 변경 여부
     * @throws InvalidVehicleDataException 수정이 제한된 경우
     */
    public void validateVehicleUpdateConstraints(Long vehicleId, boolean isLicensePlateChange) {
        log.debug("Validating vehicle update constraints: vehicleId={}, licensePlateChange={}", 
                vehicleId, isLicensePlateChange);
        
        if (isLicensePlateChange) {
            // TODO: 향후 예약 시스템 구현 시 활성 예약이 있는 경우 차량번호 변경 제한
            // if (hasActiveReservations(vehicleId)) {
            //     throw new InvalidVehicleDataException("예약이 있는 차량의 번호는 변경할 수 없습니다");
            // }
        }
        
        log.debug("Vehicle update constraints validation passed");
    }
    
    /**
     * 차량 비활성화 가능 여부 검증
     * 
     * @param vehicleId 차량 ID
     * @throws InvalidVehicleDataException 비활성화가 제한된 경우
     */
    public void validateVehicleDeactivationConstraints(Long vehicleId) {
        log.debug("Validating vehicle deactivation constraints: vehicleId={}", vehicleId);
        
        // TODO: 향후 예약 시스템 구현 시 활성 예약 확인
        // if (hasActiveReservations(vehicleId)) {
        //     throw new InvalidVehicleDataException("예약이 있는 차량은 비활성화할 수 없습니다");
        // }
        
        log.debug("Vehicle deactivation constraints validation passed");
    }
    
    /**
     * 사용자의 차량 등록 한도 검증
     * 
     * @param userId 사용자 ID
     * @param currentVehicleCount 현재 등록된 차량 수
     * @throws InvalidVehicleDataException 등록 한도 초과 시
     */
    public void validateVehicleRegistrationLimit(Long userId, int currentVehicleCount) {
        log.debug("Validating vehicle registration limit: userId={}, currentCount={}", userId, currentVehicleCount);
        
        // 일반 사용자는 최대 5대까지 등록 가능 (비즈니스 룰)
        final int MAX_VEHICLES_PER_USER = 5;
        
        if (currentVehicleCount >= MAX_VEHICLES_PER_USER) {
            throw new InvalidVehicleDataException(
                String.format("사용자당 최대 %d대까지만 등록할 수 있습니다", MAX_VEHICLES_PER_USER));
        }
        
        log.debug("Vehicle registration limit validation passed");
    }
    
    /**
     * 차량 연식과 현재 시점 간의 비즈니스 규칙 검증
     * 
     * @param year 차량 연식
     * @throws InvalidVehicleDataException 비즈니스 규칙 위반 시
     */
    public void validateVehicleAgeConstraints(Integer year) {
        log.debug("Validating vehicle age constraints: year={}", year);
        
        int currentYear = java.time.LocalDateTime.now().getYear();
        int vehicleAge = currentYear - year;
        
        // 30년 이상 된 차량에 대한 경고 (삭제는 아니지만 로그 기록)
        if (vehicleAge >= 30) {
            log.warn("등록하려는 차량이 30년 이상 된 차량입니다: 연식={}, 경과년수={}", year, vehicleAge);
        }
        
        log.debug("Vehicle age constraints validation passed");
    }
    
    // === Private Helper Methods (향후 예약/정비 시스템 연동용) ===
    
    /**
     * 활성 예약 존재 여부 확인 (향후 구현)
     */
    @SuppressWarnings("unused")
    private boolean hasActiveReservations(Long vehicleId) {
        // TODO: 예약 시스템과 연동하여 활성 예약 확인
        return false;
    }
    
    /**
     * 진행 중인 정비 존재 여부 확인 (향후 구현)
     */
    @SuppressWarnings("unused")
    private boolean hasOngoingMaintenance(Long vehicleId) {
        // TODO: 정비 시스템과 연동하여 진행 중인 정비 확인
        return false;
    }
} 