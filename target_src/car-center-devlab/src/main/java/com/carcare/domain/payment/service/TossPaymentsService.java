package com.carcare.domain.payment.service;

import com.carcare.domain.payment.client.TossPaymentsClient;
import com.carcare.domain.payment.dto.PaymentDto;
import com.carcare.domain.payment.dto.TossPaymentsDto;
import com.carcare.domain.payment.entity.Payment;
import com.carcare.domain.payment.exception.PaymentException;
import com.carcare.domain.reservation.service.ReservationService;
import com.carcare.domain.user.service.UserService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import com.carcare.config.JwtAuthenticationFilter.JwtUserPrincipal;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 토스페이먼츠 연동 서비스
 */
@Slf4j
@Service
@RequiredArgsConstructor
@Transactional
public class TossPaymentsService {
    
    private final TossPaymentsClient tossPaymentsClient;
    private final PaymentService paymentService;
    private final ReservationService reservationService;
    private final UserService userService;
    
    /**
     * 결제 요청 생성
     */
    public PaymentDto.CreateResponse createPayment(PaymentDto.CreateRequest request, JwtUserPrincipal userPrincipal) {
        log.info("Creating TossPayments payment request for user: {}", userPrincipal.getEmail());
        
        // 예약 정보 검증
        validateReservationForPayment(request.getReservationId(), userPrincipal);
        
        // 결제 정보 생성
        Payment payment = paymentService.createPayment(request);
        
        // 토스페이먼츠 결제 요청 생성
        return PaymentDto.CreateResponse.builder()
                .paymentUuid(payment.getPaymentUuid())
                .orderId(payment.getPaymentUuid())
                .amount(payment.getAmount())
                .orderName(generateOrderName(request))
                .customerName(userPrincipal.getEmail())
                .successUrl(request.getSuccessUrl())
                .failUrl(request.getFailUrl())
                .paymentUrl(generatePaymentUrl(payment))
                .build();
    }
    
    /**
     * 결제 승인 처리
     */
    public PaymentDto.ConfirmResponse confirmPayment(PaymentDto.ConfirmRequest request, JwtUserPrincipal userPrincipal) {
        log.info("Confirming TossPayments payment: orderId={}", request.getOrderId());
        
        // 결제 정보 조회
        Payment payment = paymentService.getPaymentByUuid(request.getOrderId());
        
        // 권한 검증
        validatePaymentOwnership(payment, userPrincipal);
        
        // 토스페이먼츠 결제 승인 요청
        TossPaymentsDto.PaymentConfirmRequest tossRequest = TossPaymentsDto.PaymentConfirmRequest.builder()
                .paymentKey(request.getPaymentKey())
                .orderId(request.getOrderId())
                .amount(request.getAmount())
                .build();
        
        // 🧪 테스트 환경: 토스페이먼츠 API 호출 시뮬레이션
        log.info("💳 테스트 모드: 결제 승인 시뮬레이션 - paymentKey={}, orderId={}, amount={}", 
                request.getPaymentKey(), request.getOrderId(), request.getAmount());
        
        // 시뮬레이션: 2초 대기 (실제 API 호출 시뮬레이션)
        try {
            Thread.sleep(2000);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
        
        // 결제 상태 업데이트 (성공으로 처리)
        Payment updatedPayment = paymentService.updatePaymentStatus(
                payment.getPaymentUuid(), 
                Payment.PaymentStatus.COMPLETED,
                request.getPaymentKey()
        );
        
        // 예약 상태 업데이트 (결제 완료)
        updateReservationAfterPayment(payment.getReservationId());
        
        LocalDateTime now = LocalDateTime.now();
        
        // 시뮬레이션 응답 생성
        return PaymentDto.ConfirmResponse.builder()
                .paymentKey(request.getPaymentKey())
                .orderId(request.getOrderId())
                .orderName("Car Center 정비 서비스 결제")
                .method("카드")
                .totalAmount(request.getAmount())
                .status("DONE")
                .requestedAt(now.minusMinutes(5))
                .approvedAt(now)
                .receiptUrl("https://mock-receipt.carcare.com/receipt/" + payment.getPaymentUuid())
                .build();
    }
    
    /**
     * 결제 환불 처리
     */
    public PaymentDto.RefundResponse refundPayment(String paymentUuid, PaymentDto.RefundRequest request, JwtUserPrincipal userPrincipal) {
        log.info("Processing refund for payment: {}", paymentUuid);
        
        // 결제 정보 조회
        Payment payment = paymentService.getPaymentByUuid(paymentUuid);
        
        // 권한 검증
        validatePaymentOwnership(payment, userPrincipal);
        
        // 환불 가능 여부 검증
        validateRefundEligibility(payment, request);
        
        // 토스페이먼츠 환불 요청
        TossPaymentsDto.CancelRequest cancelRequest = TossPaymentsDto.CancelRequest.builder()
                .cancelReason(request.getCancelReason())
                .cancelAmount(request.getCancelAmount())
                .build();
        
        // 🧪 테스트 환경: 토스페이먼츠 환불 API 호출 시뮬레이션
        log.info("💳 테스트 모드: 환불 처리 시뮬레이션 - paymentUuid={}, cancelAmount={}", 
                paymentUuid, request.getCancelAmount());
        
        // 시뮬레이션: 1초 대기 (실제 API 호출 시뮬레이션)
        try {
            Thread.sleep(1000);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
        
        // 결제 상태 업데이트 (환불 성공으로 처리)
        Payment.PaymentStatus newStatus = request.getCancelAmount().compareTo(payment.getAmount()) == 0 
                ? Payment.PaymentStatus.REFUNDED 
                : Payment.PaymentStatus.PARTIALLY_REFUNDED;
        
        paymentService.updatePaymentStatus(
                payment.getPaymentUuid(), 
                newStatus,
                payment.getTransactionId()
        );
        
        // 예약 상태 업데이트 (환불 완료)
        updateReservationAfterRefund(payment.getReservationId());
        
        // 시뮬레이션 응답 생성
        return PaymentDto.RefundResponse.builder()
                .paymentKey(payment.getTransactionId())
                .orderId(payment.getPaymentUuid())
                .status("CANCELED")
                .cancelAmount(request.getCancelAmount())
                .cancelReason(request.getCancelReason())
                .canceledAt(LocalDateTime.now())
                .build();
    }
    
    /**
     * 결제 환불 처리 (ID)
     */
    public PaymentDto.RefundResponse refundPaymentById(Long id, PaymentDto.RefundRequest request, JwtUserPrincipal userPrincipal) {
        log.info("Processing refund for payment ID: {}", id);
        
        // 결제 정보 조회
        Payment payment = paymentService.getPaymentById(id);
        
        // 권한 검증
        validatePaymentOwnership(payment, userPrincipal);
        
        // 환불 가능 여부 검증
        validateRefundEligibility(payment, request);
        
        // 토스페이먼츠 환불 요청
        TossPaymentsDto.CancelRequest cancelRequest = TossPaymentsDto.CancelRequest.builder()
                .cancelReason(request.getCancelReason())
                .cancelAmount(request.getCancelAmount())
                .build();
        
        // 🧪 테스트 환경: 토스페이먼츠 환불 API 호출 시뮬레이션
        log.info("💳 테스트 모드: 환불 처리 시뮬레이션 - paymentId={}, cancelAmount={}", 
                id, request.getCancelAmount());
        
        // 시뮬레이션: 1초 대기 (실제 API 호출 시뮬레이션)
        try {
            Thread.sleep(1000);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
        
        // 결제 상태 업데이트 (환불 성공으로 처리)
        Payment.PaymentStatus newStatus = payment.getAmount().equals(request.getCancelAmount())
                ? Payment.PaymentStatus.REFUNDED 
                : Payment.PaymentStatus.PARTIALLY_REFUNDED;
        
        paymentService.updatePaymentStatus(
                payment.getPaymentUuid(), 
                newStatus,
                payment.getTransactionId()
        );
        
        // 예약 상태 업데이트 (환불 완료)
        updateReservationAfterRefund(payment.getReservationId());
        
        // 시뮬레이션 응답 생성
        return PaymentDto.RefundResponse.builder()
                .paymentKey(payment.getTransactionId())
                .orderId(payment.getPaymentUuid())
                .status("CANCELED")
                .cancelAmount(request.getCancelAmount())
                .cancelReason(request.getCancelReason())
                .canceledAt(LocalDateTime.now())
                .build();
    }
    
    /**
     * 예약 결제 권한 검증
     */
    private void validateReservationForPayment(Long reservationId, JwtUserPrincipal userPrincipal) {
        // TODO: ReservationService를 통한 권한 검증 구현
        log.debug("Validating reservation {} for user {}", reservationId, userPrincipal.getEmail());
    }
    
    /**
     * 결제 소유권 검증
     */
    private void validatePaymentOwnership(Payment payment, JwtUserPrincipal userPrincipal) {
        // TODO: 결제 소유권 검증 로직 구현
        log.debug("Validating payment ownership for payment {} and user {}", 
                payment.getPaymentUuid(), userPrincipal.getEmail());
    }
    
    /**
     * 환불 가능 여부 검증
     */
    private void validateRefundEligibility(Payment payment, PaymentDto.RefundRequest request) {
        if (payment.getStatus() != Payment.PaymentStatus.COMPLETED) {
            throw new PaymentException("완료된 결제만 환불할 수 있습니다.");
        }
        
        if (request.getCancelAmount().compareTo(BigDecimal.ZERO) <= 0) {
            throw new PaymentException("환불 금액은 0보다 커야 합니다.");
        }
        
        if (request.getCancelAmount().compareTo(payment.getAmount()) > 0) {
            throw new PaymentException("환불 금액이 결제 금액을 초과할 수 없습니다.");
        }
    }
    
    /**
     * 주문명 생성
     */
    private String generateOrderName(PaymentDto.CreateRequest request) {
        return String.format("차량정비 예약 결제 - 예약번호: %d", request.getReservationId());
    }
    
    /**
     * 결제 URL 생성 (토스페이먼츠 체크아웃 페이지)
     */
    private String generatePaymentUrl(Payment payment) {
        // TODO: 실제 토스페이먼츠 체크아웃 URL 생성 로직 구현
        return String.format("https://api.tosspayments.com/v1/payments/%s", payment.getPaymentUuid());
    }
    
    /**
     * 결제 완료 후 예약 상태 업데이트
     */
    private void updateReservationAfterPayment(Long reservationId) {
        // TODO: 예약 상태를 결제 완료로 업데이트
        log.info("Updating reservation {} status after payment completion", reservationId);
    }
    
    /**
     * 환불 완료 후 예약 상태 업데이트
     */
    private void updateReservationAfterRefund(Long reservationId) {
        // TODO: 예약 상태를 환불 완료로 업데이트
        log.info("Updating reservation {} status after refund completion", reservationId);
    }

} 