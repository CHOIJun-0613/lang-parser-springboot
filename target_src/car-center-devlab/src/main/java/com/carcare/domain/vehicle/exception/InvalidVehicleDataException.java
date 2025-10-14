package com.carcare.domain.vehicle.exception;

import com.carcare.common.exception.BusinessException;

/**
 * 잘못된 차량 데이터 예외
 */
public class InvalidVehicleDataException extends BusinessException {
    
    private static final String DEFAULT_MESSAGE = "차량 데이터가 올바르지 않습니다";
    
    public InvalidVehicleDataException() {
        super(DEFAULT_MESSAGE);
    }
    
    public InvalidVehicleDataException(String message) {
        super(message);
    }
    
    public InvalidVehicleDataException(String message, Throwable cause) {
        super(message, cause);
    }
    
    public InvalidVehicleDataException(String field, Object value) {
        super(String.format("잘못된 차량 데이터입니다. 필드: %s, 값: %s", field, value));
    }
} 