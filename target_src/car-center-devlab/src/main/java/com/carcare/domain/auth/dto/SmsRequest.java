package com.carcare.domain.auth.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import lombok.Data;

/**
 * SMS 인증 요청 DTO
 */
public class SmsRequest {

    /**
     * SMS 인증번호 발송 요청
     */
    @Data
    public static class SendCode {
        @NotBlank(message = "휴대폰 번호는 필수입니다")
        @Pattern(regexp = "^01[0-9]-?[0-9]{3,4}-?[0-9]{4}$", 
                message = "올바른 휴대폰 번호 형식이 아닙니다")
        private String phoneNumber;
        
        private String purpose; // "register", "login", "password-reset" 등
    }

    /**
     * SMS 인증번호 검증 요청
     */
    @Data
    public static class VerifyCode {
        @NotBlank(message = "휴대폰 번호는 필수입니다")
        @Pattern(regexp = "^01[0-9]-?[0-9]{3,4}-?[0-9]{4}$", 
                message = "올바른 휴대폰 번호 형식이 아닙니다")
        private String phoneNumber;
        
        @NotBlank(message = "인증번호는 필수입니다")
        @Pattern(regexp = "^[0-9]{6}$", message = "인증번호는 6자리 숫자입니다")
        private String verificationCode;
    }
} 