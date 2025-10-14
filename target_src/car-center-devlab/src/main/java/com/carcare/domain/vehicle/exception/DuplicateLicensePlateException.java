package com.carcare.domain.vehicle.exception;

import com.carcare.common.exception.BusinessException;

/**
 * 차량번호 중복 예외
 */
public class DuplicateLicensePlateException extends BusinessException {
    
    private static final String DEFAULT_MESSAGE = "이미 등록된 차량번호입니다";
    
    public DuplicateLicensePlateException() {
        super(DEFAULT_MESSAGE);
    }
    
    public DuplicateLicensePlateException(String licensePlate) {
        super(String.format("이미 등록된 차량번호입니다: %s", licensePlate));
    }
    
    public DuplicateLicensePlateException(String message, Throwable cause) {
        super(message, cause);
    }
} 