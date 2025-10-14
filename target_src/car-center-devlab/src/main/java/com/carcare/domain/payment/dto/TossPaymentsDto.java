package com.carcare.domain.payment.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

/**
 * 토스페이먼츠 API DTO 클래스들
 */
public class TossPaymentsDto {
    
    /**
     * 결제 승인 요청 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class PaymentConfirmRequest {
        @JsonProperty("paymentKey")
        private String paymentKey;
        
        @JsonProperty("orderId")
        private String orderId;
        
        @JsonProperty("amount")
        private BigDecimal amount;
    }
    
    /**
     * 결제 승인 응답 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class PaymentConfirmResponse {
        @JsonProperty("version")
        private String version;
        
        @JsonProperty("paymentKey")
        private String paymentKey;
        
        @JsonProperty("type")
        private String type;
        
        @JsonProperty("orderId")
        private String orderId;
        
        @JsonProperty("orderName")
        private String orderName;
        
        @JsonProperty("mId")
        private String mId;
        
        @JsonProperty("currency")
        private String currency;
        
        @JsonProperty("method")
        private String method;
        
        @JsonProperty("totalAmount")
        private BigDecimal totalAmount;
        
        @JsonProperty("balanceAmount")
        private BigDecimal balanceAmount;
        
        @JsonProperty("status")
        private String status;
        
        @JsonProperty("requestedAt")
        private LocalDateTime requestedAt;
        
        @JsonProperty("approvedAt")
        private LocalDateTime approvedAt;
        
        @JsonProperty("useEscrow")
        private Boolean useEscrow;
        
        @JsonProperty("lastTransactionKey")
        private String lastTransactionKey;
        
        @JsonProperty("suppliedAmount")
        private BigDecimal suppliedAmount;
        
        @JsonProperty("vat")
        private BigDecimal vat;
        
        @JsonProperty("cultureExpense")
        private Boolean cultureExpense;
        
        @JsonProperty("taxFreeAmount")
        private BigDecimal taxFreeAmount;
        
        @JsonProperty("taxExemptionAmount")
        private BigDecimal taxExemptionAmount;
        
        @JsonProperty("cancels")
        private List<Cancel> cancels;
        
        @JsonProperty("isPartialCancelable")
        private Boolean isPartialCancelable;
        
        @JsonProperty("card")
        private Card card;
        
        @JsonProperty("virtualAccount")
        private VirtualAccount virtualAccount;
        
        @JsonProperty("transfer")
        private Transfer transfer;
        
        @JsonProperty("mobilePhone")
        private MobilePhone mobilePhone;
        
        @JsonProperty("giftCertificate")
        private GiftCertificate giftCertificate;
        
        @JsonProperty("cashReceipt")
        private CashReceipt cashReceipt;
        
        @JsonProperty("cashReceipts")
        private List<CashReceipt> cashReceipts;
        
        @JsonProperty("discount")
        private Discount discount;
        
        @JsonProperty("secret")
        private String secret;
        
        @JsonProperty("receipt")
        private Receipt receipt;
        
        @JsonProperty("checkout")
        private Checkout checkout;
        
        @JsonProperty("easyPay")
        private EasyPay easyPay;
        
        @JsonProperty("country")
        private String country;
        
        @JsonProperty("failure")
        private Failure failure;
    }
    
    /**
     * 취소 정보
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Cancel {
        @JsonProperty("cancelAmount")
        private BigDecimal cancelAmount;
        
        @JsonProperty("cancelReason")
        private String cancelReason;
        
        @JsonProperty("taxFreeAmount")
        private BigDecimal taxFreeAmount;
        
        @JsonProperty("taxExemptionAmount")
        private BigDecimal taxExemptionAmount;
        
        @JsonProperty("refundableAmount")
        private BigDecimal refundableAmount;
        
        @JsonProperty("easyPayDiscountAmount")
        private BigDecimal easyPayDiscountAmount;
        
        @JsonProperty("canceledAt")
        private LocalDateTime canceledAt;
        
        @JsonProperty("transactionKey")
        private String transactionKey;
        
        @JsonProperty("receiptKey")
        private String receiptKey;
    }
    
    /**
     * 카드 정보
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Card {
        @JsonProperty("amount")
        private BigDecimal amount;
        
        @JsonProperty("issuerCode")
        private String issuerCode;
        
        @JsonProperty("acquirerCode")
        private String acquirerCode;
        
        @JsonProperty("number")
        private String number;
        
        @JsonProperty("installmentPlanMonths")
        private Integer installmentPlanMonths;
        
        @JsonProperty("approveNo")
        private String approveNo;
        
        @JsonProperty("useCardPoint")
        private Boolean useCardPoint;
        
        @JsonProperty("cardType")
        private String cardType;
        
        @JsonProperty("ownerType")
        private String ownerType;
        
        @JsonProperty("acquireStatus")
        private String acquireStatus;
        
        @JsonProperty("isInterestFree")
        private Boolean isInterestFree;
        
        @JsonProperty("interestPayer")
        private String interestPayer;
    }
    
    /**
     * 가상계좌 정보
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class VirtualAccount {
        @JsonProperty("accountType")
        private String accountType;
        
        @JsonProperty("accountNumber")
        private String accountNumber;
        
        @JsonProperty("bankCode")
        private String bankCode;
        
        @JsonProperty("customerName")
        private String customerName;
        
        @JsonProperty("dueDate")
        private LocalDateTime dueDate;
        
        @JsonProperty("refundStatus")
        private String refundStatus;
        
        @JsonProperty("expired")
        private Boolean expired;
        
        @JsonProperty("settlementStatus")
        private String settlementStatus;
        
        @JsonProperty("refundReceiveAccount")
        private RefundReceiveAccount refundReceiveAccount;
    }
    
    /**
     * 환불 받을 계좌 정보
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class RefundReceiveAccount {
        @JsonProperty("bankCode")
        private String bankCode;
        
        @JsonProperty("accountNumber")
        private String accountNumber;
        
        @JsonProperty("holderName")
        private String holderName;
    }
    
    /**
     * 계좌이체 정보
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Transfer {
        @JsonProperty("bankCode")
        private String bankCode;
        
        @JsonProperty("settlementStatus")
        private String settlementStatus;
    }
    
    /**
     * 휴대폰 결제 정보
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class MobilePhone {
        @JsonProperty("customerMobilePhone")
        private String customerMobilePhone;
        
        @JsonProperty("settlementStatus")
        private String settlementStatus;
        
        @JsonProperty("receiptUrl")
        private String receiptUrl;
    }
    
    /**
     * 상품권 정보
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class GiftCertificate {
        @JsonProperty("approveNo")
        private String approveNo;
        
        @JsonProperty("settlementStatus")
        private String settlementStatus;
    }
    
    /**
     * 현금영수증 정보
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class CashReceipt {
        @JsonProperty("type")
        private String type;
        
        @JsonProperty("receiptKey")
        private String receiptKey;
        
        @JsonProperty("issueNumber")
        private String issueNumber;
        
        @JsonProperty("receiptUrl")
        private String receiptUrl;
        
        @JsonProperty("amount")
        private BigDecimal amount;
        
        @JsonProperty("taxFreeAmount")
        private BigDecimal taxFreeAmount;
    }
    
    /**
     * 할인 정보
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Discount {
        @JsonProperty("amount")
        private BigDecimal amount;
    }
    
    /**
     * 영수증 정보
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Receipt {
        @JsonProperty("url")
        private String url;
    }
    
    /**
     * 체크아웃 정보
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Checkout {
        @JsonProperty("url")
        private String url;
    }
    
    /**
     * 간편결제 정보
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class EasyPay {
        @JsonProperty("provider")
        private String provider;
        
        @JsonProperty("amount")
        private BigDecimal amount;
        
        @JsonProperty("discountAmount")
        private BigDecimal discountAmount;
    }
    
    /**
     * 실패 정보
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Failure {
        @JsonProperty("code")
        private String code;
        
        @JsonProperty("message")
        private String message;
    }
    
    /**
     * 취소 요청 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class CancelRequest {
        @JsonProperty("cancelReason")
        private String cancelReason;
        
        @JsonProperty("cancelAmount")
        private BigDecimal cancelAmount;
        
        @JsonProperty("refundReceiveAccount")
        private RefundReceiveAccount refundReceiveAccount;
    }
    
    /**
     * API 에러 응답 DTO
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ErrorResponse {
        @JsonProperty("code")
        private String code;
        
        @JsonProperty("message")
        private String message;
    }
} 