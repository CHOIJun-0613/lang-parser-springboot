package com.carcare.domain.payment.exception;

import com.carcare.common.exception.BusinessException;

/**
 * 결제 관련 예외
 */
public class PaymentException extends BusinessException {
    
    public PaymentException(String message) {
        super(message);
    }
    
    public PaymentException(String message, Throwable cause) {
        super(message, cause);
    }
    
    public PaymentException(String code, String message) {
        super(code + ": " + message);
    }
    
    public PaymentException(String code, String message, Throwable cause) {
        super(code + ": " + message, cause);
    }
} 