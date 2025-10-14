package com.carcare.domain.auth.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 인증 응답 관련 DTO 모음
 */
public class AuthResponse {

    /**
     * 로그인 성공 응답 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Login {
        private String accessToken;
        private String refreshToken;
        private String tokenType = "Bearer";
        private Long expiresIn; // 초 단위
        private UserInfo user;
        private LocalDateTime loginTime;
    }

    /**
     * 회원가입 성공 응답 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Register {
        private String message;
        private UserInfo user;
        private boolean emailVerificationRequired;
        private LocalDateTime registeredAt;
    }

    /**
     * 토큰 갱신 응답 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class RefreshToken {
        private String accessToken;
        private String refreshToken;
        private String tokenType = "Bearer";
        private Long expiresIn; // 초 단위
        private LocalDateTime refreshedAt;
    }

    /**
     * 사용자 정보 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class UserInfo {
        private Long id;
        private String userUuid;
        private String email;
        private String name;
        private String phone;
        private String role;
        private boolean isActive;
        private boolean emailVerified;
        private LocalDateTime lastLoginAt;
        private LocalDateTime createdAt;
    }

    /**
     * 이메일 인증 응답 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class EmailVerification {
        private String message;
        private boolean verified;
        private String email;
        private LocalDateTime verifiedAt;
    }

    /**
     * 비밀번호 재설정 응답 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class PasswordReset {
        private String message;
        private String email;
        private LocalDateTime requestedAt;
    }

    /**
     * 로그아웃 응답 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Logout {
        private String message;
        private LocalDateTime logoutTime;
    }

    /**
     * 일반적인 성공 응답 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Success {
        private String message;
        private LocalDateTime timestamp;
    }
} 