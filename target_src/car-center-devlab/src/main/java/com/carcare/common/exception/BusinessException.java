package com.carcare.common.exception;

/**
 * 비즈니스 로직 예외
 * 
 * 애플리케이션에서 발생하는 비즈니스 관련 예외를 처리
 */
public class BusinessException extends RuntimeException {

    public BusinessException(String message) {
        super(message);
    }

    public BusinessException(String message, Throwable cause) {
        super(message, cause);
    }
} 