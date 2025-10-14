package com.carcare.domain.payment.controller;

import com.carcare.common.dto.ApiResponse;
import com.carcare.common.util.ResponseUtils;
import com.carcare.domain.payment.dto.PaymentDto;
import com.carcare.domain.payment.service.PaymentService;
import com.carcare.domain.payment.service.TossPaymentsService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import com.carcare.config.JwtAuthenticationFilter.JwtUserPrincipal;
import org.springframework.web.bind.annotation.*;

import jakarta.validation.Valid;
import java.util.List;

/**
 * 결제 관리 컨트롤러
 */
@Slf4j
@RestController
@RequestMapping("/api/v1/payments")
@Tag(name = "Payment", description = "결제 관리 API")
@RequiredArgsConstructor
public class PaymentController {
    
    private final PaymentService paymentService;
    private final TossPaymentsService tossPaymentsService;
    
    /**
     * 결제 요청
     */
    @PostMapping
    @Operation(summary = "결제 요청", description = "새로운 결제를 요청합니다.")
    public ApiResponse<PaymentDto.CreateResponse> createPayment(
            @Valid @RequestBody PaymentDto.CreateRequest request,
            @Parameter(hidden = true) @AuthenticationPrincipal JwtUserPrincipal userPrincipal) {
        
        log.info("Payment request received: reservationId={}, amount={}", 
                request.getReservationId(), request.getAmount());
        
        PaymentDto.CreateResponse response = tossPaymentsService.createPayment(request, userPrincipal);
        
        return ResponseUtils.success("결제 요청이 성공적으로 생성되었습니다.", response);
    }
    
    /**
     * 전체 결제 목록 조회 (관리자)
     */
    @GetMapping
    @Operation(summary = "전체 결제 목록 조회", description = "모든 결제의 목록을 조회합니다. (관리자 권한)")
    public ApiResponse<List<PaymentDto.ListResponse>> getAllPayments(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String status,
            @Parameter(hidden = true) @AuthenticationPrincipal JwtUserPrincipal userPrincipal) {
        
        log.info("All payments request: page={}, size={}, status={}", page, size, status);
        
        // 임시로 빈 목록 반환 (추후 PaymentService에 getAllPayments 메서드 구현 필요)
        List<PaymentDto.ListResponse> response = java.util.Collections.emptyList();
        
        return ResponseUtils.success("전체 결제 목록을 성공적으로 조회했습니다.", response);
    }
    
    /**
     * 결제 승인
     */
    @PostMapping("/confirm")
    @Operation(summary = "결제 승인", description = "토스페이먼츠 결제를 승인합니다.")
    public ApiResponse<PaymentDto.ConfirmResponse> confirmPayment(
            @Valid @RequestBody PaymentDto.ConfirmRequest request,
            @Parameter(hidden = true) @AuthenticationPrincipal JwtUserPrincipal userPrincipal) {
        
        log.info("Payment confirmation request: orderId={}, paymentKey={}", 
                request.getOrderId(), request.getPaymentKey());
        
        PaymentDto.ConfirmResponse response = tossPaymentsService.confirmPayment(request, userPrincipal);
        
        return ResponseUtils.success("결제가 성공적으로 승인되었습니다.", response);
    }
    
    /**
     * 결제 정보 조회 (ID)
     */
    @GetMapping("/{id}")
    @Operation(summary = "결제 정보 조회 (ID)", description = "결제 ID로 결제 정보를 조회합니다.")
    public ApiResponse<PaymentDto.DetailResponse> getPaymentById(
            @Parameter(description = "결제 ID", example = "1")
            @PathVariable Long id,
            @Parameter(hidden = true) @AuthenticationPrincipal JwtUserPrincipal userPrincipal) {
        
        log.info("Payment details request by ID: id={}", id);
        
        PaymentDto.DetailResponse response = paymentService.getPaymentDetailsById(id, userPrincipal);
        
        return ResponseUtils.success("결제 정보를 성공적으로 조회했습니다.", response);
    }
    
    /**
     * 결제 정보 조회 (UUID)
     */
    @GetMapping("/uuid/{uuid}")
    @Operation(summary = "결제 정보 조회 (UUID)", description = "결제 UUID로 결제 정보를 조회합니다.")
    public ApiResponse<PaymentDto.DetailResponse> getPaymentByUuid(
            @Parameter(description = "결제 UUID", example = "550e8400-e29b-41d4-a716-446655440000")
            @PathVariable String uuid,
            @Parameter(hidden = true) @AuthenticationPrincipal JwtUserPrincipal userPrincipal) {
        
        log.info("Payment details request by UUID: uuid={}", uuid);
        
        PaymentDto.DetailResponse response = paymentService.getPaymentDetails(uuid, userPrincipal);
        
        return ResponseUtils.success("결제 정보를 성공적으로 조회했습니다.", response);
    }
    
    /**
     * 사용자 결제 목록 조회
     */
    @GetMapping("/my")
    @Operation(summary = "내 결제 목록 조회", description = "현재 사용자의 결제 목록을 조회합니다.")
    public ApiResponse<List<PaymentDto.ListResponse>> getMyPayments(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size,
            @Parameter(hidden = true) @AuthenticationPrincipal JwtUserPrincipal userPrincipal) {
        
        log.info("My payments request: user={}, page={}, size={}", 
                userPrincipal.getEmail(), page, size);
        
        List<PaymentDto.ListResponse> response = paymentService.getUserPayments(userPrincipal, page, size);
        
        return ResponseUtils.success("결제 목록을 성공적으로 조회했습니다.", response);
    }
    
    /**
     * 예약별 결제 목록 조회
     */
    @GetMapping("/reservation/{reservationId}")
    @Operation(summary = "예약별 결제 목록 조회", description = "특정 예약의 결제 목록을 조회합니다.")
    public ApiResponse<List<PaymentDto.ListResponse>> getPaymentsByReservation(
            @PathVariable Long reservationId,
            @Parameter(hidden = true) @AuthenticationPrincipal JwtUserPrincipal userPrincipal) {
        
        log.info("Reservation payments request: reservationId={}", reservationId);
        
        List<PaymentDto.ListResponse> response = paymentService.getReservationPayments(reservationId, userPrincipal);
        
        return ResponseUtils.success("예약별 결제 목록을 성공적으로 조회했습니다.", response);
    }
    
    /**
     * 결제 취소 (ID)
     */
    @PostMapping("/{id}/cancel")
    @Operation(summary = "결제 취소 (ID)", description = "결제 ID로 진행 중인 결제를 취소합니다.")
    public ApiResponse<PaymentDto.RefundResponse> cancelPaymentById(
            @Parameter(description = "결제 ID", example = "1")
            @PathVariable Long id,
            @Valid @RequestBody PaymentDto.RefundRequest request,
            @Parameter(hidden = true) @AuthenticationPrincipal JwtUserPrincipal userPrincipal) {
        
        log.info("Payment cancel request by ID: id={}, reason={}", 
                id, request.getCancelReason());
        
        PaymentDto.RefundResponse response = tossPaymentsService.refundPaymentById(id, request, userPrincipal);
        
        return ResponseUtils.success("결제가 성공적으로 취소되었습니다.", response);
    }
    
    /**
     * 결제 취소 (UUID)
     */
    @PostMapping("/uuid/{uuid}/cancel")
    @Operation(summary = "결제 취소 (UUID)", description = "결제 UUID로 진행 중인 결제를 취소합니다.")
    public ApiResponse<PaymentDto.RefundResponse> cancelPaymentByUuid(
            @Parameter(description = "결제 UUID", example = "550e8400-e29b-41d4-a716-446655440000")
            @PathVariable String uuid,
            @Valid @RequestBody PaymentDto.RefundRequest request,
            @Parameter(hidden = true) @AuthenticationPrincipal JwtUserPrincipal userPrincipal) {
        
        log.info("Payment cancel request by UUID: uuid={}, reason={}", 
                uuid, request.getCancelReason());
        
        // 임시로 refund 메서드 사용 (추후 별도 cancel 메서드 구현 필요)
        PaymentDto.RefundResponse response = tossPaymentsService.refundPayment(uuid, request, userPrincipal);
        
        return ResponseUtils.success("결제가 성공적으로 취소되었습니다.", response);
    }
    
    /**
     * 결제 환불 (ID)
     */
    @PostMapping("/{id}/refund")
    @Operation(summary = "결제 환불 (ID)", description = "결제 ID로 결제를 환불 처리합니다.")
    public ApiResponse<PaymentDto.RefundResponse> refundPaymentById(
            @Parameter(description = "결제 ID", example = "1")
            @PathVariable Long id,
            @Valid @RequestBody PaymentDto.RefundRequest request,
            @Parameter(hidden = true) @AuthenticationPrincipal JwtUserPrincipal userPrincipal) {
        
        log.info("Payment refund request by ID: id={}, reason={}", 
                id, request.getCancelReason());
        
        PaymentDto.RefundResponse response = tossPaymentsService.refundPaymentById(id, request, userPrincipal);
        
        return ResponseUtils.success("환불이 성공적으로 처리되었습니다.", response);
    }
    
    /**
     * 결제 환불 (UUID)
     */
    @PostMapping("/uuid/{uuid}/refund")
    @Operation(summary = "결제 환불 (UUID)", description = "결제 UUID로 결제를 환불 처리합니다.")
    public ApiResponse<PaymentDto.RefundResponse> refundPaymentByUuid(
            @Parameter(description = "결제 UUID", example = "550e8400-e29b-41d4-a716-446655440000")
            @PathVariable String uuid,
            @Valid @RequestBody PaymentDto.RefundRequest request,
            @Parameter(hidden = true) @AuthenticationPrincipal JwtUserPrincipal userPrincipal) {
        
        log.info("Payment refund request by UUID: uuid={}, reason={}", 
                uuid, request.getCancelReason());
        
        PaymentDto.RefundResponse response = tossPaymentsService.refundPayment(uuid, request, userPrincipal);
        
        return ResponseUtils.success("환불이 성공적으로 처리되었습니다.", response);
    }
    
    /**
     * 결제 성공 페이지 (리다이렉트)
     */
    @GetMapping("/success")
    @Operation(summary = "결제 성공 처리", description = "토스페이먼츠 결제 성공 시 리다이렉트 처리")
    public ApiResponse<String> paymentSuccess(
            @RequestParam String paymentKey,
            @RequestParam String orderId,
            @RequestParam String amount) {
        
        log.info("Payment success callback: orderId={}, paymentKey={}, amount={}", 
                orderId, paymentKey, amount);
        
        // 프론트엔드로 리다이렉트 또는 성공 메시지 반환
        return ResponseUtils.success("결제가 성공적으로 완료되었습니다.", 
                "결제 성공 페이지입니다.");
    }
    
    /**
     * 결제 실패 페이지 (리다이렉트)
     */
    @GetMapping("/fail")
    @Operation(summary = "결제 실패 처리", description = "토스페이먼츠 결제 실패 시 리다이렉트 처리")
    public ApiResponse<String> paymentFail(
            @RequestParam String code,
            @RequestParam String message,
            @RequestParam String orderId) {
        
        log.warn("Payment failure callback: orderId={}, code={}, message={}", 
                orderId, code, message);
        
        return ResponseUtils.error("PAYMENT_FAILED", 
                "결제가 실패했습니다: " + message);
    }
} 