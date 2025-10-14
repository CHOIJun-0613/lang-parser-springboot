package com.carcare.domain.payment.dto;

import com.carcare.domain.payment.entity.Payment;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 결제 DTO 클래스들
 */
public class PaymentDto {
    
    /**
     * 결제 요청 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class CreateRequest {
        private Long reservationId;
        private Long quoteId;
        private BigDecimal amount;
        private Payment.PaymentMethod paymentMethod;
        private String successUrl;
        private String failUrl;
    }
    
    /**
     * 결제 응답 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class CreateResponse {
        private String paymentUuid;
        private String orderId;
        private BigDecimal amount;
        private String orderName;
        private String customerName;
        private String successUrl;
        private String failUrl;
        private String paymentUrl;
    }
    
    /**
     * 결제 승인 요청 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ConfirmRequest {
        private String paymentKey;
        private String orderId;
        private BigDecimal amount;
    }
    
    /**
     * 결제 승인 응답 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ConfirmResponse {
        private String paymentKey;
        private String orderId;
        private String orderName;
        private String method;
        private BigDecimal totalAmount;
        private String status;
        private LocalDateTime requestedAt;
        private LocalDateTime approvedAt;
        private String receiptUrl;
    }
    
    /**
     * 환불 요청 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class RefundRequest {
        private String cancelReason;
        private BigDecimal cancelAmount;
        private BigDecimal refundableAmount;
    }
    
    /**
     * 환불 응답 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class RefundResponse {
        private String paymentKey;
        private String orderId;
        private String status;
        private BigDecimal cancelAmount;
        private String cancelReason;
        private LocalDateTime canceledAt;
    }
    
    /**
     * 결제 상세 조회 응답 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class DetailResponse {
        private Long id;
        private String paymentUuid;
        private Long reservationId;
        private Long quoteId;
        private BigDecimal amount;
        private Payment.PaymentMethod paymentMethod;
        private Payment.PaymentStatus status;
        private String transactionId;
        private Payment.PaymentGateway paymentGateway;
        private LocalDateTime paidAt;
        private LocalDateTime createdAt;
        private String receiptUrl;
    }
    
    /**
     * 결제 목록 조회 응답 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ListResponse {
        private Long id;
        private String paymentUuid;
        private BigDecimal amount;
        private Payment.PaymentStatus status;
        private Payment.PaymentMethod paymentMethod;
        private LocalDateTime paidAt;
        private LocalDateTime createdAt;
    }
} 