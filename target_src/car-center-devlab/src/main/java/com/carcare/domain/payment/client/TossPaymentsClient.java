package com.carcare.domain.payment.client;

import com.carcare.domain.payment.config.TossPaymentsConfig;
import com.carcare.domain.payment.dto.TossPaymentsDto;
import com.carcare.domain.payment.exception.PaymentException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.*;
import org.springframework.stereotype.Component;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.HttpServerErrorException;
import org.springframework.web.client.RestClientResponseException;
import org.springframework.web.client.RestTemplate;

import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Base64;

/**
 * 토스페이먼츠 API 클라이언트
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class TossPaymentsClient {
    
    private final TossPaymentsConfig config;
    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper;
    
    /**
     * 결제 승인
     */
    public TossPaymentsDto.PaymentConfirmResponse confirmPayment(TossPaymentsDto.PaymentConfirmRequest request) {
        log.info("Confirming payment: orderId={}, paymentKey={}", request.getOrderId(), request.getPaymentKey());
        
        String url = config.getBaseUrl() + "/v1/payments/confirm";
        HttpHeaders headers = createHeaders();
        
        HttpEntity<TossPaymentsDto.PaymentConfirmRequest> httpEntity = new HttpEntity<>(request, headers);
        
        try {
            ResponseEntity<TossPaymentsDto.PaymentConfirmResponse> response = 
                restTemplate.postForEntity(url, httpEntity, TossPaymentsDto.PaymentConfirmResponse.class);
            
            log.info("Payment confirmation successful: {}", response.getBody());
            return response.getBody();
            
        } catch (HttpClientErrorException | HttpServerErrorException e) {
            log.error("Payment confirmation failed: {}", e.getResponseBodyAsString());
            handleHttpError(e);
            throw new PaymentException("결제 승인에 실패했습니다.");
        } catch (Exception e) {
            log.error("Unexpected error during payment confirmation", e);
            throw new PaymentException("결제 승인 중 예상치 못한 오류가 발생했습니다.");
        }
    }
    
    /**
     * 결제 조회
     */
    public TossPaymentsDto.PaymentConfirmResponse getPayment(String paymentKey) {
        log.info("Getting payment: paymentKey={}", paymentKey);
        
        String url = config.getBaseUrl() + "/v1/payments/" + paymentKey;
        HttpHeaders headers = createHeaders();
        
        HttpEntity<Void> httpEntity = new HttpEntity<>(headers);
        
        try {
            ResponseEntity<TossPaymentsDto.PaymentConfirmResponse> response = 
                restTemplate.exchange(url, HttpMethod.GET, httpEntity, TossPaymentsDto.PaymentConfirmResponse.class);
            
            log.info("Payment retrieval successful: {}", response.getBody());
            return response.getBody();
            
        } catch (HttpClientErrorException | HttpServerErrorException e) {
            log.error("Payment retrieval failed: {}", e.getResponseBodyAsString());
            handleHttpError(e);
            throw new PaymentException("결제 정보 조회에 실패했습니다.");
        } catch (Exception e) {
            log.error("Unexpected error during payment retrieval", e);
            throw new PaymentException("결제 정보 조회 중 예상치 못한 오류가 발생했습니다.");
        }
    }
    
    /**
     * 결제 취소
     */
    public TossPaymentsDto.PaymentConfirmResponse cancelPayment(String paymentKey, TossPaymentsDto.CancelRequest request) {
        log.info("Canceling payment: paymentKey={}, reason={}", paymentKey, request.getCancelReason());
        
        String url = config.getBaseUrl() + "/v1/payments/" + paymentKey + "/cancel";
        HttpHeaders headers = createHeaders();
        
        HttpEntity<TossPaymentsDto.CancelRequest> httpEntity = new HttpEntity<>(request, headers);
        
        try {
            ResponseEntity<TossPaymentsDto.PaymentConfirmResponse> response = 
                restTemplate.postForEntity(url, httpEntity, TossPaymentsDto.PaymentConfirmResponse.class);
            
            log.info("Payment cancellation successful: {}", response.getBody());
            return response.getBody();
            
        } catch (HttpClientErrorException | HttpServerErrorException e) {
            log.error("Payment cancellation failed: {}", e.getResponseBodyAsString());
            handleHttpError(e);
            throw new PaymentException("결제 취소에 실패했습니다.");
        } catch (Exception e) {
            log.error("Unexpected error during payment cancellation", e);
            throw new PaymentException("결제 취소 중 예상치 못한 오류가 발생했습니다.");
        }
    }
    
    /**
     * HTTP 헤더 생성
     */
    private HttpHeaders createHeaders() {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.set("Authorization", "Basic " + createBasicAuthToken());
        return headers;
    }
    
    /**
     * Basic Auth 토큰 생성
     */
    private String createBasicAuthToken() {
        String credentials = config.getSecretKey() + ":";
        byte[] encodedCredentials = Base64.getEncoder().encode(credentials.getBytes(StandardCharsets.UTF_8));
        return new String(encodedCredentials, StandardCharsets.UTF_8);
    }
    
    /**
     * HTTP 에러 처리
     */
    private void handleHttpError(RestClientResponseException e) {
        try {
            TossPaymentsDto.ErrorResponse errorResponse = 
                objectMapper.readValue(e.getResponseBodyAsString(), TossPaymentsDto.ErrorResponse.class);
            
            log.error("TossPayments API Error - Code: {}, Message: {}", 
                errorResponse.getCode(), errorResponse.getMessage());
            
            // 특정 에러 코드에 따른 처리
            switch (errorResponse.getCode()) {
                case "ALREADY_PROCESSED_PAYMENT":
                    throw new PaymentException("이미 처리된 결제입니다.");
                case "PROVIDER_ERROR":
                    throw new PaymentException("결제 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.");
                case "EXCEED_MAX_CARD_INSTALLMENT_PLAN":
                    throw new PaymentException("할부 개월 수가 초과되었습니다.");
                case "INVALID_REQUEST":
                    throw new PaymentException("잘못된 요청입니다.");
                case "NOT_ALLOWED_POINT_USE":
                    throw new PaymentException("포인트 사용이 허용되지 않습니다.");
                case "INVALID_API_KEY":
                    throw new PaymentException("API 키가 유효하지 않습니다.");
                case "INVALID_SECRET_KEY":
                    throw new PaymentException("시크릿 키가 유효하지 않습니다.");
                case "UNAUTHORIZED_KEY":
                    throw new PaymentException("인증되지 않은 키입니다.");
                case "REJECTED_CARD_COMPANY":
                    throw new PaymentException("카드사에서 거절된 결제입니다.");
                default:
                    throw new PaymentException("결제 처리 중 오류가 발생했습니다: " + errorResponse.getMessage());
            }
        } catch (Exception ex) {
            log.error("Error parsing TossPayments error response", ex);
            throw new PaymentException("결제 처리 중 오류가 발생했습니다.");
        }
    }
    
    /**
     * 웹훅 서명 검증
     */
    public boolean verifyWebhookSignature(String signature, String body) {
        try {
            if (signature == null || body == null) {
                log.warn("Webhook signature or body is null");
                return false;
            }
            
            // HMAC-SHA256으로 서명 검증
            javax.crypto.Mac mac = javax.crypto.Mac.getInstance("HmacSHA256");
            javax.crypto.spec.SecretKeySpec secretKeySpec = 
                new javax.crypto.spec.SecretKeySpec(config.getWebhookSecret().getBytes(StandardCharsets.UTF_8), "HmacSHA256");
            mac.init(secretKeySpec);
            
            byte[] computedHash = mac.doFinal(body.getBytes(StandardCharsets.UTF_8));
            String computedSignature = Base64.getEncoder().encodeToString(computedHash);
            
            // 시간 상수 비교를 통한 타이밍 공격 방지
            return constantTimeEquals(signature, computedSignature);
            
        } catch (Exception e) {
            log.error("Error verifying webhook signature", e);
            return false;
        }
    }
    
    /**
     * 시간 상수 문자열 비교 (타이밍 공격 방지)
     */
    private boolean constantTimeEquals(String a, String b) {
        if (a == null || b == null) {
            return false;
        }
        
        if (a.length() != b.length()) {
            return false;
        }
        
        int result = 0;
        for (int i = 0; i < a.length(); i++) {
            result |= a.charAt(i) ^ b.charAt(i);
        }
        
        return result == 0;
    }
} 