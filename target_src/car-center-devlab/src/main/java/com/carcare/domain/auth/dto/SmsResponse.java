package com.carcare.domain.auth.dto;

import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * SMS 인증 응답 DTO
 */
public class SmsResponse {

    /**
     * SMS 인증번호 발송 응답
     */
    @Data
    @Builder
    public static class SendCode {
        private String message;
        private String phoneNumber;
        private int expirationMinutes;
        private LocalDateTime sentAt;
        private String requestId; // 추적용 ID
    }

    /**
     * SMS 인증번호 검증 응답
     */
    @Data
    @Builder
    public static class VerifyCode {
        private String message;
        private String phoneNumber;
        private boolean verified;
        private LocalDateTime verifiedAt;
    }
} 