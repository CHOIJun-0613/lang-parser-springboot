package com.carcare.domain.payment.service;

import com.carcare.domain.payment.dto.TossPaymentsDto;
import com.carcare.domain.payment.entity.Payment;
import com.carcare.domain.payment.exception.PaymentException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 결제 웹훅 처리 서비스
 */
@Slf4j
@Service
@RequiredArgsConstructor
@Transactional
public class PaymentWebhookService {
    
    private final PaymentService paymentService;
    private final ObjectMapper objectMapper;
    
    /**
     * 토스페이먼츠 웹훅 처리
     */
    public void processTossPaymentsWebhook(String requestBody) {
        try {
            log.info("Processing TossPayments webhook: {}", requestBody);
            
            // JSON 파싱
            TossPaymentsDto.PaymentConfirmResponse webhookData = 
                objectMapper.readValue(requestBody, TossPaymentsDto.PaymentConfirmResponse.class);
            
            // 결제 정보 조회
            Payment payment = paymentService.getPaymentByUuid(webhookData.getOrderId());
            
            // 웹훅 이벤트 타입에 따른 처리
            String status = webhookData.getStatus();
            
            switch (status) {
                case "DONE":
                    handlePaymentCompleted(payment, webhookData);
                    break;
                case "CANCELED":
                    handlePaymentCanceled(payment, webhookData);
                    break;
                case "PARTIAL_CANCELED":
                    handlePaymentPartiallyCanceled(payment, webhookData);
                    break;
                case "FAILED":
                    handlePaymentFailed(payment, webhookData);
                    break;
                default:
                    log.warn("Unhandled payment status: {}", status);
                    break;
            }
            
        } catch (Exception e) {
            log.error("Error processing TossPayments webhook", e);
            throw new PaymentException("웹훅 처리 중 오류가 발생했습니다: " + e.getMessage());
        }
    }
    
    /**
     * 일반 결제 게이트웨이 웹훅 처리
     */
    public void processGeneralWebhook(String gateway, String requestBody, String signature) {
        log.info("Processing {} webhook", gateway);
        
        switch (gateway.toLowerCase()) {
            case "kakao":
                processKakaoPayWebhook(requestBody, signature);
                break;
            case "naver":
                processNaverPayWebhook(requestBody, signature);
                break;
            default:
                log.warn("Unsupported payment gateway: {}", gateway);
                throw new PaymentException("지원하지 않는 결제 게이트웨이입니다: " + gateway);
        }
    }
    
    /**
     * 결제 완료 처리
     */
    private void handlePaymentCompleted(Payment payment, TossPaymentsDto.PaymentConfirmResponse webhookData) {
        log.info("Handling payment completion for payment: {}", payment.getPaymentUuid());
        
        // 결제 상태 업데이트
        paymentService.updatePaymentStatus(
            payment.getPaymentUuid(),
            Payment.PaymentStatus.COMPLETED,
            webhookData.getPaymentKey()
        );
        
        // 영수증 URL 업데이트
        if (webhookData.getReceipt() != null) {
            payment.setReceiptUrl(webhookData.getReceipt().getUrl());
        }
        
        // 추가 비즈니스 로직 처리
        processAfterPaymentCompletion(payment);
    }
    
    /**
     * 결제 취소 처리
     */
    private void handlePaymentCanceled(Payment payment, TossPaymentsDto.PaymentConfirmResponse webhookData) {
        log.info("Handling payment cancellation for payment: {}", payment.getPaymentUuid());
        
        // 결제 상태 업데이트
        paymentService.updatePaymentStatus(
            payment.getPaymentUuid(),
            Payment.PaymentStatus.REFUNDED,
            webhookData.getPaymentKey()
        );
        
        // 추가 비즈니스 로직 처리
        processAfterPaymentCancellation(payment);
    }
    
    /**
     * 부분 취소 처리
     */
    private void handlePaymentPartiallyCanceled(Payment payment, TossPaymentsDto.PaymentConfirmResponse webhookData) {
        log.info("Handling partial payment cancellation for payment: {}", payment.getPaymentUuid());
        
        // 결제 상태 업데이트
        paymentService.updatePaymentStatus(
            payment.getPaymentUuid(),
            Payment.PaymentStatus.PARTIALLY_REFUNDED,
            webhookData.getPaymentKey()
        );
        
        // 추가 비즈니스 로직 처리
        processAfterPartialCancellation(payment);
    }
    
    /**
     * 결제 실패 처리
     */
    private void handlePaymentFailed(Payment payment, TossPaymentsDto.PaymentConfirmResponse webhookData) {
        log.info("Handling payment failure for payment: {}", payment.getPaymentUuid());
        
        // 결제 상태 업데이트
        paymentService.updatePaymentStatus(
            payment.getPaymentUuid(),
            Payment.PaymentStatus.FAILED,
            webhookData.getPaymentKey()
        );
        
        // 추가 비즈니스 로직 처리
        processAfterPaymentFailure(payment);
    }
    
    /**
     * 카카오페이 웹훅 처리
     */
    private void processKakaoPayWebhook(String requestBody, String signature) {
        // TODO: 카카오페이 웹훅 처리 로직 구현
        log.info("Processing KakaoPay webhook");
    }
    
    /**
     * 네이버페이 웹훅 처리
     */
    private void processNaverPayWebhook(String requestBody, String signature) {
        // TODO: 네이버페이 웹훅 처리 로직 구현
        log.info("Processing NaverPay webhook");
    }
    
    /**
     * 결제 완료 후 처리
     */
    private void processAfterPaymentCompletion(Payment payment) {
        // TODO: 예약 상태 업데이트, 알림 발송 등
        log.info("Processing after payment completion for payment: {}", payment.getPaymentUuid());
    }
    
    /**
     * 결제 취소 후 처리
     */
    private void processAfterPaymentCancellation(Payment payment) {
        // TODO: 예약 취소 처리, 환불 알림 발송 등
        log.info("Processing after payment cancellation for payment: {}", payment.getPaymentUuid());
    }
    
    /**
     * 부분 취소 후 처리
     */
    private void processAfterPartialCancellation(Payment payment) {
        // TODO: 부분 환불 처리, 예약 상태 조정 등
        log.info("Processing after partial cancellation for payment: {}", payment.getPaymentUuid());
    }
    
    /**
     * 결제 실패 후 처리
     */
    private void processAfterPaymentFailure(Payment payment) {
        // TODO: 예약 상태 복원, 실패 알림 발송 등
        log.info("Processing after payment failure for payment: {}", payment.getPaymentUuid());
    }
} 