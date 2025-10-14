package com.carcare.domain.vehicle.exception;

import com.carcare.common.exception.BusinessException;

/**
 * 차량을 찾을 수 없음 예외
 */
public class VehicleNotFoundException extends BusinessException {
    
    private static final String DEFAULT_MESSAGE = "차량을 찾을 수 없습니다";
    
    public VehicleNotFoundException() {
        super(DEFAULT_MESSAGE);
    }
    
    public VehicleNotFoundException(String message) {
        super(message);
    }
    
    public VehicleNotFoundException(Long vehicleId) {
        super(String.format("차량을 찾을 수 없습니다. ID: %d", vehicleId));
    }
    
    public VehicleNotFoundException(String identifier, Object value) {
        super(String.format("차량을 찾을 수 없습니다. %s: %s", identifier, value));
    }
    
    public VehicleNotFoundException(String message, Throwable cause) {
        super(message, cause);
    }
} 