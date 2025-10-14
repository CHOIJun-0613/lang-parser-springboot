package com.carcare.domain.notification.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.hc.client5.http.classic.methods.HttpPost;
import org.apache.hc.client5.http.impl.classic.CloseableHttpClient;
import org.apache.hc.client5.http.impl.classic.CloseableHttpResponse;
import org.apache.hc.client5.http.impl.classic.HttpClients;
import org.apache.hc.core5.http.io.entity.StringEntity;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.retry.annotation.Backoff;
import org.springframework.retry.annotation.Retryable;
import org.springframework.stereotype.Service;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.InvalidKeyException;
import java.security.NoSuchAlgorithmException;
import java.time.LocalDateTime;
import java.util.Base64;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * SMS 발송 서비스 (네이버 클라우드 플랫폼 API 연동)
 */
@Slf4j
@Service("notificationSmsService")
@RequiredArgsConstructor
public class SmsService {
    
    @Value("${ncp.sms.access-key:}")
    private String accessKey;
    
    @Value("${ncp.sms.secret-key:}")
    private String secretKey;
    
    @Value("${ncp.sms.service-id:}")
    private String serviceId;
    
    @Value("${ncp.sms.from-number:}")
    private String fromNumber;
    
    @Value("${ncp.sms.api-url:https://sens.apigw.ntruss.com}")
    private String apiUrl;
    
    @Value("${ncp.sms.enabled:false}")
    private boolean smsEnabled;
    
    private final ObjectMapper objectMapper;
    private final NotificationService notificationService;
    
    /**
     * SMS 발송 (단일)
     */
    @Retryable(value = {Exception.class}, maxAttempts = 3, backoff = @Backoff(delay = 1000))
    public SmsResult sendSms(String toNumber, String message) {
        return sendSms(List.of(toNumber), message);
    }
    
    /**
     * SMS 발송 (다중)
     */
    @Retryable(value = {Exception.class}, maxAttempts = 3, backoff = @Backoff(delay = 1000))
    public SmsResult sendSms(List<String> toNumbers, String message) {
        
        if (!smsEnabled) {
            log.warn("SMS 발송이 비활성화되어 있습니다.");
            return SmsResult.builder()
                    .success(false)
                    .errorMessage("SMS 발송이 비활성화되어 있습니다.")
                    .build();
        }
        
        if (accessKey.isEmpty() || secretKey.isEmpty() || serviceId.isEmpty() || fromNumber.isEmpty()) {
            log.error("SMS 설정이 누락되었습니다. 환경 변수를 확인해주세요.");
            return SmsResult.builder()
                    .success(false)
                    .errorMessage("SMS 설정이 누락되었습니다.")
                    .build();
        }
        
        try {
            String requestUrl = String.format("%s/sms/v2/services/%s/messages", apiUrl, serviceId);
            String timestamp = String.valueOf(System.currentTimeMillis());
            
            // 요청 본문 생성
            Map<String, Object> requestBody = createRequestBody(toNumbers, message);
            String jsonBody = objectMapper.writeValueAsString(requestBody);
            
            // 서명 생성
            String signature = createSignature("POST", "/sms/v2/services/" + serviceId + "/messages", timestamp);
            
            // HTTP 요청 발송
            try (CloseableHttpClient httpClient = HttpClients.createDefault()) {
                HttpPost httpPost = new HttpPost(requestUrl);
                
                // 헤더 설정
                httpPost.setHeader("Content-Type", "application/json; charset=utf-8");
                httpPost.setHeader("x-ncp-apigw-timestamp", timestamp);
                httpPost.setHeader("x-ncp-iam-access-key", accessKey);
                httpPost.setHeader("x-ncp-apigw-signature-v2", signature);
                
                // 요청 본문 설정
                httpPost.setEntity(new StringEntity(jsonBody, StandardCharsets.UTF_8));
                
                // 요청 실행
                try (CloseableHttpResponse response = httpClient.execute(httpPost)) {
                    int statusCode = response.getCode();
                    String responseBody = new String(response.getEntity().getContent().readAllBytes(), StandardCharsets.UTF_8);
                    
                    log.info("SMS 발송 응답 - StatusCode: {}, Body: {}", statusCode, responseBody);
                    
                    if (statusCode == 202) {
                        // 성공
                        Map<String, Object> responseMap = objectMapper.readValue(responseBody, Map.class);
                        String requestId = (String) responseMap.get("requestId");
                        
                        return SmsResult.builder()
                                .success(true)
                                .requestId(requestId)
                                .sentAt(LocalDateTime.now())
                                .toNumbers(toNumbers)
                                .message(message)
                                .build();
                    } else {
                        // 실패
                        return SmsResult.builder()
                                .success(false)
                                .errorMessage("SMS 발송 실패: " + responseBody)
                                .build();
                    }
                }
            }
            
        } catch (Exception e) {
            log.error("SMS 발송 중 오류 발생", e);
            return SmsResult.builder()
                    .success(false)
                    .errorMessage("SMS 발송 중 오류 발생: " + e.getMessage())
                    .build();
        }
    }
    
    /**
     * 사용자별 SMS 발송 (알림 설정 확인)
     */
    public SmsResult sendSmsToUser(Long userId, String message, String relatedEntityType, Long relatedEntityId) {
        
        // 사용자 알림 설정 확인
        if (!notificationService.shouldReceiveNotification(userId, 
                com.carcare.domain.notification.entity.Notification.NotificationType.SYSTEM_MAINTENANCE, "SMS")) {
            log.info("사용자 {}의 SMS 수신 설정이 비활성화되어 있습니다.", userId);
            return SmsResult.builder()
                    .success(false)
                    .errorMessage("사용자 SMS 수신 설정이 비활성화되어 있습니다.")
                    .build();
        }
        
        // 사용자 전화번호 조회 (실제로는 UserService에서 조회해야 함)
        String phoneNumber = getUserPhoneNumber(userId);
        if (phoneNumber == null || phoneNumber.isEmpty()) {
            log.warn("사용자 {}의 전화번호가 없습니다.", userId);
            return SmsResult.builder()
                    .success(false)
                    .errorMessage("사용자 전화번호가 없습니다.")
                    .build();
        }
        
        return sendSms(phoneNumber, message);
    }
    
    /**
     * 요청 본문 생성
     */
    private Map<String, Object> createRequestBody(List<String> toNumbers, String message) {
        Map<String, Object> body = new HashMap<>();
        body.put("type", "SMS");
        body.put("contentType", "COMM");
        body.put("countryCode", "82");
        body.put("from", fromNumber);
        body.put("content", message);
        
        // 수신자 목록 생성
        List<Map<String, String>> messages = toNumbers.stream()
                .map(toNumber -> {
                    Map<String, String> msg = new HashMap<>();
                    msg.put("to", toNumber.replaceAll("-", "")); // 하이픈 제거
                    return msg;
                })
                .toList();
        
        body.put("messages", messages);
        return body;
    }
    
    /**
     * API 서명 생성
     */
    private String createSignature(String method, String uri, String timestamp) 
            throws NoSuchAlgorithmException, InvalidKeyException {
        
        String space = " ";
        String newLine = "\n";
        
        String message = method +
                space +
                uri +
                newLine +
                timestamp +
                newLine +
                accessKey;
        
        SecretKeySpec signingKey = new SecretKeySpec(secretKey.getBytes(StandardCharsets.UTF_8), "HmacSHA256");
        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(signingKey);
        byte[] rawHmac = mac.doFinal(message.getBytes(StandardCharsets.UTF_8));
        
        return Base64.getEncoder().encodeToString(rawHmac);
    }
    
    /**
     * 사용자 전화번호 조회 (임시 구현)
     * TODO: UserService에서 실제 사용자 정보 조회하도록 수정
     */
    private String getUserPhoneNumber(Long userId) {
        // 임시로 하드코딩된 값 반환
        // 실제로는 UserService를 통해 사용자 정보를 조회해야 함
        log.warn("임시 구현: 사용자 {}의 전화번호를 하드코딩된 값으로 반환합니다.", userId);
        return "010-1234-5678"; // 임시 값
    }
    
    /**
     * SMS 발송 결과
     */
    public static class SmsResult {
        private boolean success;
        private String requestId;
        private LocalDateTime sentAt;
        private List<String> toNumbers;
        private String message;
        private String errorMessage;
        
        public static SmsResultBuilder builder() {
            return new SmsResultBuilder();
        }
        
        // Getters
        public boolean isSuccess() { return success; }
        public String getRequestId() { return requestId; }
        public LocalDateTime getSentAt() { return sentAt; }
        public List<String> getToNumbers() { return toNumbers; }
        public String getMessage() { return message; }
        public String getErrorMessage() { return errorMessage; }
        
        public static class SmsResultBuilder {
            private boolean success;
            private String requestId;
            private LocalDateTime sentAt;
            private List<String> toNumbers;
            private String message;
            private String errorMessage;
            
            public SmsResultBuilder success(boolean success) {
                this.success = success;
                return this;
            }
            
            public SmsResultBuilder requestId(String requestId) {
                this.requestId = requestId;
                return this;
            }
            
            public SmsResultBuilder sentAt(LocalDateTime sentAt) {
                this.sentAt = sentAt;
                return this;
            }
            
            public SmsResultBuilder toNumbers(List<String> toNumbers) {
                this.toNumbers = toNumbers;
                return this;
            }
            
            public SmsResultBuilder message(String message) {
                this.message = message;
                return this;
            }
            
            public SmsResultBuilder errorMessage(String errorMessage) {
                this.errorMessage = errorMessage;
                return this;
            }
            
            public SmsResult build() {
                SmsResult result = new SmsResult();
                result.success = this.success;
                result.requestId = this.requestId;
                result.sentAt = this.sentAt;
                result.toNumbers = this.toNumbers;
                result.message = this.message;
                result.errorMessage = this.errorMessage;
                return result;
            }
        }
    }
} 