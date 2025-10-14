package com.carcare.domain.payment.entity;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 결제 엔티티
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Payment {
    
    private Long id;
    
    private String paymentUuid;
    
    private Long reservationId;
    
    private Long quoteId;
    
    private BigDecimal amount;
    
    private PaymentMethod paymentMethod;
    
    private PaymentStatus status;
    
    private String transactionId;
    
    private PaymentGateway paymentGateway;
    
    private LocalDateTime paidAt;
    
    private LocalDateTime createdAt;
    
    private LocalDateTime updatedAt;
    
    private String receiptUrl;
    
    /**
     * 결제 상태 열거형
     */
    public enum PaymentStatus {
        PENDING,
        COMPLETED,
        FAILED,
        REFUNDED,
        PARTIALLY_REFUNDED,
        CANCELLED
    }
    
    /**
     * 결제 수단 열거형
     */
    public enum PaymentMethod {
        CARD,
        BANK_TRANSFER,
        CASH,
        VIRTUAL_ACCOUNT,
        MOBILE_PAYMENT
    }
    
    /**
     * 결제 게이트웨이 열거형
     */
    public enum PaymentGateway {
        TOSS_PAYMENTS,
        STRIPE,
        KAKAO_PAY,
        NAVER_PAY,
        PAYCO
    }
} 