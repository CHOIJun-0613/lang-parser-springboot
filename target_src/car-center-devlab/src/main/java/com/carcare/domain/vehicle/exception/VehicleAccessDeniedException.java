package com.carcare.domain.vehicle.exception;

import com.carcare.common.exception.BusinessException;

/**
 * 차량 접근 권한 없음 예외
 */
public class VehicleAccessDeniedException extends BusinessException {
    
    private static final String DEFAULT_MESSAGE = "해당 차량에 대한 권한이 없습니다";
    
    public VehicleAccessDeniedException() {
        super(DEFAULT_MESSAGE);
    }
    
    public VehicleAccessDeniedException(String message) {
        super(message);
    }
    
    public VehicleAccessDeniedException(Long userId, Long vehicleId) {
        super(String.format("해당 차량에 대한 권한이 없습니다. 사용자ID: %d, 차량ID: %d", userId, vehicleId));
    }
    
    public VehicleAccessDeniedException(String message, Throwable cause) {
        super(message, cause);
    }
} 