package com.carcare.domain.payment.controller;

import com.carcare.common.dto.ApiResponse;
import com.carcare.common.util.ResponseUtils;
import com.carcare.domain.payment.client.TossPaymentsClient;
import com.carcare.domain.payment.service.PaymentWebhookService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;

import jakarta.servlet.http.HttpServletRequest;
import java.io.BufferedReader;
import java.io.IOException;

/**
 * 결제 웹훅 컨트롤러
 */
@Slf4j
@RestController
@RequestMapping("/api/v1/payments/webhook")
@Tag(name = "Payment Webhook", description = "결제 웹훅 처리 API")
@RequiredArgsConstructor
public class PaymentWebhookController {
    
    private final PaymentWebhookService paymentWebhookService;
    private final TossPaymentsClient tossPaymentsClient;
    
    /**
     * 토스페이먼츠 웹훅 처리
     */
    @PostMapping("/toss")
    @Operation(summary = "토스페이먼츠 웹훅", description = "토스페이먼츠로부터 결제 상태 변경 웹훅을 처리합니다.")
    public ApiResponse<String> handleTossPaymentsWebhook(
            HttpServletRequest request,
            @RequestHeader(value = "X-Toss-Signature", required = false) String signature) {
        
        try {
            // 요청 본문 읽기
            String requestBody = getRequestBody(request);
            
            log.info("Received TossPayments webhook: signature={}", 
                    signature != null ? signature.substring(0, Math.min(signature.length(), 10)) + "..." : "null");
            
            // 서명 검증
            if (!tossPaymentsClient.verifyWebhookSignature(signature, requestBody)) {
                log.warn("Invalid webhook signature");
                return ResponseUtils.error("INVALID_SIGNATURE", "잘못된 웹훅 서명입니다.");
            }
            
            // 웹훅 처리
            paymentWebhookService.processTossPaymentsWebhook(requestBody);
            
            return ResponseUtils.success("웹훅이 성공적으로 처리되었습니다.");
            
        } catch (Exception e) {
            log.error("Error processing TossPayments webhook", e);
            return ResponseUtils.error("WEBHOOK_PROCESSING_ERROR", 
                    "웹훅 처리 중 오류가 발생했습니다: " + e.getMessage());
        }
    }
    
    /**
     * 기타 결제 게이트웨이 웹훅 처리
     */
    @PostMapping("/{gateway}")
    @Operation(summary = "일반 결제 웹훅", description = "다양한 결제 게이트웨이의 웹훅을 처리합니다.")
    public ApiResponse<String> handleGeneralWebhook(
            @PathVariable String gateway,
            HttpServletRequest request,
            @RequestHeader(value = "X-Signature", required = false) String signature) {
        
        try {
            String requestBody = getRequestBody(request);
            
            log.info("Received {} webhook: signature={}", gateway, 
                    signature != null ? signature.substring(0, Math.min(signature.length(), 10)) + "..." : "null");
            
            // 게이트웨이별 웹훅 처리
            paymentWebhookService.processGeneralWebhook(gateway, requestBody, signature);
            
            return ResponseUtils.success("웹훅이 성공적으로 처리되었습니다.");
            
        } catch (Exception e) {
            log.error("Error processing {} webhook", gateway, e);
            return ResponseUtils.error("WEBHOOK_PROCESSING_ERROR", 
                    "웹훅 처리 중 오류가 발생했습니다: " + e.getMessage());
        }
    }
    
    /**
     * HTTP 요청 본문 읽기
     */
    private String getRequestBody(HttpServletRequest request) throws IOException {
        StringBuilder sb = new StringBuilder();
        String line;
        
        try (BufferedReader reader = request.getReader()) {
            while ((line = reader.readLine()) != null) {
                sb.append(line);
            }
        }
        
        return sb.toString();
    }
} 