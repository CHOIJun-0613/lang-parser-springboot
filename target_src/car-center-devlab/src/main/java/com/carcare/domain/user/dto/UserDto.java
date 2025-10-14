package com.carcare.domain.user.dto;

import lombok.Data;
import lombok.Builder;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import java.time.LocalDateTime;

import jakarta.validation.constraints.*;

/**
 * 사용자 데이터 전송 객체
 */
public class UserDto {
    
    /**
     * 사용자 프로필 조회 응답 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ProfileResponse {
        private Long id;
        private String userUuid;
        private String email;
        private String name;
        private String phone;
        private String role;
        private Boolean isActive;
        private Boolean emailVerified;
        private LocalDateTime lastLoginAt;
        private LocalDateTime createdAt;
        private LocalDateTime updatedAt;
    }
    
    /**
     * 사용자 프로필 수정 요청 DTO
     */
    @Data
    public static class UpdateProfileRequest {
        @NotBlank(message = "이름은 필수입니다")
        @Size(min = 2, max = 20, message = "이름은 2자 이상 20자 이하여야 합니다")
        private String name;
        
        @Pattern(
            regexp = "^01[0-9]-?[0-9]{3,4}-?[0-9]{4}$",
            message = "올바른 휴대폰 번호 형식이 아닙니다"
        )
        private String phone;
    }
    
    /**
     * 사용자 목록 조회 응답 DTO (관리자용)
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ListResponse {
        private Long id;
        private String userUuid;
        private String email;
        private String name;
        private String phone;
        private String role;
        private Boolean isActive;
        private Boolean emailVerified;
        private LocalDateTime createdAt;
        private LocalDateTime lastLoginAt;
    }
    
    /**
     * 사용자 비밀번호 변경 요청 DTO
     */
    @Data
    public static class ChangePasswordRequest {
        @NotBlank(message = "현재 비밀번호는 필수입니다")
        private String currentPassword;
        
        @NotBlank(message = "새 비밀번호는 필수입니다")
        @Size(min = 8, max = 50, message = "비밀번호는 8자 이상 50자 이하여야 합니다")
        @Pattern(
            regexp = "^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)(?=.*[@$!%*?&])[A-Za-z\\d@$!%*?&]+$",
            message = "비밀번호는 대소문자, 숫자, 특수문자를 모두 포함해야 합니다"
        )
        private String newPassword;
        
        @NotBlank(message = "새 비밀번호 확인은 필수입니다")
        private String confirmNewPassword;
    }
} 