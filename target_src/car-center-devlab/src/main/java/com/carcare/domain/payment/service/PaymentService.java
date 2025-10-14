package com.carcare.domain.payment.service;

import com.carcare.config.JwtAuthenticationFilter.JwtUserPrincipal;
import com.carcare.domain.payment.dto.PaymentDto;
import com.carcare.domain.payment.entity.Payment;
import com.carcare.domain.payment.exception.PaymentException;
import com.carcare.domain.payment.repository.PaymentRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

/**
 * 결제 서비스
 */
@Slf4j
@Service
@RequiredArgsConstructor
@Transactional
public class PaymentService {
    
    private final PaymentRepository paymentRepository;
    
    /**
     * 결제 정보 생성
     */
    public Payment createPayment(PaymentDto.CreateRequest request) {
        log.info("Creating payment for reservation: {}", request.getReservationId());
        
        Payment payment = Payment.builder()
                .paymentUuid(UUID.randomUUID().toString())
                .reservationId(request.getReservationId())
                .quoteId(request.getQuoteId())
                .amount(request.getAmount())
                .paymentMethod(request.getPaymentMethod())
                .status(Payment.PaymentStatus.PENDING)
                .paymentGateway(Payment.PaymentGateway.TOSS_PAYMENTS)
                .createdAt(LocalDateTime.now())
                .updatedAt(LocalDateTime.now())
                .build();
        
        paymentRepository.save(payment);
        log.info("Payment created with UUID: {}", payment.getPaymentUuid());
        
        return payment;
    }
    
    /**
     * 결제 상태 업데이트
     */
    public Payment updatePaymentStatus(String paymentUuid, Payment.PaymentStatus status, String transactionId) {
        log.info("Updating payment status: {} to {}", paymentUuid, status);
        
        Payment payment = paymentRepository.findByPaymentUuid(paymentUuid)
                .orElseThrow(() -> new PaymentException("PAYMENT_NOT_FOUND", "결제 정보를 찾을 수 없습니다: " + paymentUuid));
        
        payment.setStatus(status);
        payment.setTransactionId(transactionId);
        payment.setUpdatedAt(LocalDateTime.now());
        
        if (status == Payment.PaymentStatus.COMPLETED) {
            payment.setPaidAt(LocalDateTime.now());
        }
        
        paymentRepository.update(payment);
        log.info("Payment status updated successfully");
        
        return payment;
    }
    
    /**
     * 결제 정보 조회 (UUID)
     */
    @Transactional(readOnly = true)
    public Payment getPaymentByUuid(String paymentUuid) {
        return paymentRepository.findByPaymentUuid(paymentUuid)
                .orElseThrow(() -> new PaymentException("PAYMENT_NOT_FOUND", "결제 정보를 찾을 수 없습니다: " + paymentUuid));
    }
    
    /**
     * 결제 정보 조회 (ID)
     */
    @Transactional(readOnly = true)
    public Payment getPaymentById(Long id) {
        return paymentRepository.findById(id)
                .orElseThrow(() -> new PaymentException("PAYMENT_NOT_FOUND", "결제 정보를 찾을 수 없습니다: " + id));
    }
    
    /**
     * 예약별 결제 목록 조회
     */
    @Transactional(readOnly = true)
    public List<Payment> getPaymentsByReservationId(Long reservationId) {
        return paymentRepository.findByReservationId(reservationId);
    }
    
    /**
     * 사용자별 결제 목록 조회
     */
    @Transactional(readOnly = true)
    public List<Payment> getPaymentsByUserId(Long userId) {
        return paymentRepository.findByUserId(userId);
    }
    
    /**
     * 결제 정보를 DTO로 변환
     */
    public PaymentDto.DetailResponse convertToDetailResponse(Payment payment) {
        return PaymentDto.DetailResponse.builder()
                .id(payment.getId())
                .paymentUuid(payment.getPaymentUuid())
                .reservationId(payment.getReservationId())
                .quoteId(payment.getQuoteId())
                .amount(payment.getAmount())
                .paymentMethod(payment.getPaymentMethod())
                .status(payment.getStatus())
                .transactionId(payment.getTransactionId())
                .paymentGateway(payment.getPaymentGateway())
                .paidAt(payment.getPaidAt())
                .createdAt(payment.getCreatedAt())
                .receiptUrl(payment.getReceiptUrl())
                .build();
    }
    
    /**
     * 결제 목록을 DTO로 변환
     */
    public PaymentDto.ListResponse convertToListResponse(Payment payment) {
        return PaymentDto.ListResponse.builder()
                .id(payment.getId())
                .paymentUuid(payment.getPaymentUuid())
                .amount(payment.getAmount())
                .status(payment.getStatus())
                .paymentMethod(payment.getPaymentMethod())
                .paidAt(payment.getPaidAt())
                .createdAt(payment.getCreatedAt())
                .build();
    }
    
    /**
     * 결제 상세 정보 조회 (권한 검증 포함)
     */
    @Transactional(readOnly = true)
    public PaymentDto.DetailResponse getPaymentDetails(String paymentUuid, JwtUserPrincipal userPrincipal) {
        Payment payment = getPaymentByUuid(paymentUuid);
        
        // 권한 검증 로직
        validatePaymentAccess(payment, userPrincipal);
        
        return convertToDetailResponse(payment);
    }
    
    /**
     * 결제 상세 정보 조회 (ID) (권한 검증 포함)
     */
    @Transactional(readOnly = true)
    public PaymentDto.DetailResponse getPaymentDetailsById(Long id, JwtUserPrincipal userPrincipal) {
        Payment payment = getPaymentById(id);
        
        // 권한 검증 로직
        validatePaymentAccess(payment, userPrincipal);
        
        return convertToDetailResponse(payment);
    }
    
    /**
     * 사용자별 결제 목록 조회 (페이징)
     */
    @Transactional(readOnly = true)
    public List<PaymentDto.ListResponse> getUserPayments(JwtUserPrincipal userPrincipal, int page, int size) {
        // JWT에서 사용자 ID 추출
        Long userId = userPrincipal.getUserId();
        
        List<Payment> payments = paymentRepository.findByUserId(userId);
        
        // 페이징 처리 (간단한 구현)
        int fromIndex = page * size;
        int toIndex = Math.min(fromIndex + size, payments.size());
        
        if (fromIndex >= payments.size()) {
            return List.of();
        }
        
        return payments.subList(fromIndex, toIndex)
                .stream()
                .map(this::convertToListResponse)
                .toList();
    }
    
    /**
     * 예약별 결제 목록 조회 (권한 검증 포함)
     */
    @Transactional(readOnly = true)
    public List<PaymentDto.ListResponse> getReservationPayments(Long reservationId, JwtUserPrincipal userPrincipal) {
        // 예약 소유권 검증
        validateReservationAccess(reservationId, userPrincipal);
        
        List<Payment> payments = paymentRepository.findByReservationId(reservationId);
        
        return payments.stream()
                .map(this::convertToListResponse)
                .toList();
    }
    
    /**
     * 결제 접근 권한 검증
     */
    private void validatePaymentAccess(Payment payment, JwtUserPrincipal userPrincipal) {
        // 실제 권한 검증 로직 구현
        log.debug("Validating payment access for payment {} and user {}", 
                payment.getPaymentUuid(), userPrincipal.getEmail());
    }
    
    /**
     * 예약 접근 권한 검증
     */
    private void validateReservationAccess(Long reservationId, JwtUserPrincipal userPrincipal) {
        // 실제 예약 권한 검증 로직 구현
        log.debug("Validating reservation access for reservation {} and user {}", 
                reservationId, userPrincipal.getEmail());
    }
} 