package com.carcare.domain.payment.service;

import com.carcare.domain.payment.client.TossPaymentsClient;
import com.carcare.domain.payment.dto.PaymentDto;
import com.carcare.domain.payment.dto.TossPaymentsDto;
import com.carcare.domain.payment.entity.Payment;
import com.carcare.domain.payment.exception.PaymentException;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.retry.annotation.Backoff;
import org.springframework.retry.annotation.Retryable;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.concurrent.CompletableFuture;

/**
 * 결제 실패 재시도 서비스
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class PaymentRetryService {
    
    private final TossPaymentsClient tossPaymentsClient;
    private final PaymentService paymentService;
    
    /**
     * 결제 승인 재시도 (지수 백오프)
     */
    @Retryable(
        value = {PaymentException.class},
        maxAttempts = 3,
        backoff = @Backoff(delay = 1000, multiplier = 2.0)
    )
    public TossPaymentsDto.PaymentConfirmResponse retryPaymentConfirmation(PaymentDto.ConfirmRequest request) {
        log.info("Retrying payment confirmation for orderId: {}", request.getOrderId());
        
        try {
            TossPaymentsDto.PaymentConfirmRequest tossRequest = TossPaymentsDto.PaymentConfirmRequest.builder()
                    .paymentKey(request.getPaymentKey())
                    .orderId(request.getOrderId())
                    .amount(request.getAmount())
                    .build();
            
            return tossPaymentsClient.confirmPayment(tossRequest);
            
        } catch (Exception e) {
            log.warn("Payment confirmation retry failed for orderId: {}, attempt will be retried", 
                    request.getOrderId());
            
            // 재시도 가능한 오류인지 확인
            if (isRetryableError(e)) {
                throw new PaymentException("재시도 가능한 결제 오류: " + e.getMessage(), e);
            } else {
                // 재시도 불가능한 오류는 즉시 실패 처리
                handleNonRetryableError(request.getOrderId(), e);
                throw new PaymentException("재시도 불가능한 결제 오류: " + e.getMessage(), e);
            }
        }
    }
    
    /**
     * 비동기 결제 재시도
     */
    @Async
    public CompletableFuture<Void> retryPaymentAsync(String paymentUuid) {
        log.info("Starting async payment retry for payment: {}", paymentUuid);
        
        try {
            Payment payment = paymentService.getPaymentByUuid(paymentUuid);
            
            // 재시도 가능 상태 확인
            if (!isRetryablePaymentStatus(payment.getStatus())) {
                log.warn("Payment {} is not in retryable status: {}", paymentUuid, payment.getStatus());
                return CompletableFuture.completedFuture(null);
            }
            
            // 재시도 횟수 확인 (간단한 구현)
            int retryCount = getRetryCount(payment);
            if (retryCount >= 3) {
                log.warn("Maximum retry count reached for payment: {}", paymentUuid);
                handleMaxRetryReached(payment);
                return CompletableFuture.completedFuture(null);
            }
            
            // 결제 재시도 실행
            performPaymentRetry(payment);
            
            log.info("Async payment retry completed for payment: {}", paymentUuid);
            
        } catch (Exception e) {
            log.error("Error during async payment retry for payment: {}", paymentUuid, e);
        }
        
        return CompletableFuture.completedFuture(null);
    }
    
    /**
     * 결제 재시도 실행
     */
    private void performPaymentRetry(Payment payment) {
        try {
            // 토스페이먼츠 결제 상태 조회
            TossPaymentsDto.PaymentConfirmResponse response = 
                    tossPaymentsClient.getPayment(payment.getTransactionId());
            
            // 응답에 따른 상태 업데이트
            updatePaymentStatusFromResponse(payment, response);
            
        } catch (Exception e) {
            log.error("Failed to retry payment for: {}", payment.getPaymentUuid(), e);
            
            // 재시도 실패 기록
            recordRetryFailure(payment, e);
        }
    }
    
    /**
     * 재시도 가능한 오류인지 확인
     */
    private boolean isRetryableError(Exception e) {
        String message = e.getMessage();
        if (message == null) {
            return false;
        }
        
        // 네트워크 오류, 일시적 서버 오류 등은 재시도 가능
        return message.contains("timeout") ||
               message.contains("connection") ||
               message.contains("server error") ||
               message.contains("503") ||
               message.contains("502");
    }
    
    /**
     * 재시도 가능한 결제 상태인지 확인
     */
    private boolean isRetryablePaymentStatus(Payment.PaymentStatus status) {
        return status == Payment.PaymentStatus.PENDING || 
               status == Payment.PaymentStatus.FAILED;
    }
    
    /**
     * 재시도 횟수 조회 (간단한 구현)
     */
    private int getRetryCount(Payment payment) {
        // TODO: 실제 재시도 이력 테이블에서 조회
        // 현재는 간단하게 업데이트 시간을 기준으로 추정
        if (payment.getCreatedAt().equals(payment.getUpdatedAt())) {
            return 0;
        }
        return 1; // 임시 구현
    }
    
    /**
     * 재시도 불가능한 오류 처리
     */
    private void handleNonRetryableError(String orderId, Exception e) {
        log.error("Non-retryable error for orderId: {}", orderId, e);
        
        try {
            Payment payment = paymentService.getPaymentByUuid(orderId);
            paymentService.updatePaymentStatus(
                    payment.getPaymentUuid(), 
                    Payment.PaymentStatus.FAILED, 
                    null
            );
        } catch (Exception ex) {
            log.error("Failed to update payment status after non-retryable error", ex);
        }
    }
    
    /**
     * 최대 재시도 횟수 도달 처리
     */
    private void handleMaxRetryReached(Payment payment) {
        log.warn("Max retry count reached for payment: {}", payment.getPaymentUuid());
        
        paymentService.updatePaymentStatus(
                payment.getPaymentUuid(), 
                Payment.PaymentStatus.FAILED, 
                payment.getTransactionId()
        );
        
        // TODO: 관리자 알림, 고객 알림 등 추가 처리
    }
    
    /**
     * 토스페이먼츠 응답에 따른 결제 상태 업데이트
     */
    private void updatePaymentStatusFromResponse(Payment payment, TossPaymentsDto.PaymentConfirmResponse response) {
        Payment.PaymentStatus newStatus;
        
        switch (response.getStatus()) {
            case "DONE":
                newStatus = Payment.PaymentStatus.COMPLETED;
                break;
            case "CANCELED":
                newStatus = Payment.PaymentStatus.REFUNDED;
                break;
            case "PARTIAL_CANCELED":
                newStatus = Payment.PaymentStatus.PARTIALLY_REFUNDED;
                break;
            case "FAILED":
                newStatus = Payment.PaymentStatus.FAILED;
                break;
            default:
                newStatus = Payment.PaymentStatus.PENDING;
                break;
        }
        
        paymentService.updatePaymentStatus(
                payment.getPaymentUuid(), 
                newStatus, 
                response.getPaymentKey()
        );
    }
    
    /**
     * 재시도 실패 기록
     */
    private void recordRetryFailure(Payment payment, Exception e) {
        // TODO: 재시도 실패 이력 테이블에 기록
        log.warn("Recording retry failure for payment: {}, error: {}", 
                payment.getPaymentUuid(), e.getMessage());
    }
} 