package com.carcare.domain.auth.dto;

import lombok.Data;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

/**
 * 인증 요청 관련 DTO 모음
 */
public class AuthRequest {

    /**
     * 로그인 요청 DTO
     */
    @Data
    public static class Login {
        @NotBlank(message = "이메일은 필수입니다")
        @Email(message = "올바른 이메일 형식이 아닙니다")
        private String email;

        @NotBlank(message = "비밀번호는 필수입니다")
        @Size(min = 8, max = 50, message = "비밀번호는 8자 이상 50자 이하여야 합니다")
        private String password;

        private boolean rememberMe = false;
    }

    /**
     * 회원가입 요청 DTO
     */
    @Data
    public static class Register {
        @NotBlank(message = "이메일은 필수입니다")
        @Email(message = "올바른 이메일 형식이 아닙니다")
        private String email;

        @NotBlank(message = "비밀번호는 필수입니다")
        @Size(min = 8, max = 50, message = "비밀번호는 8자 이상 50자 이하여야 합니다")
        @Pattern(
            regexp = "^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)(?=.*[@$!%*?&])[A-Za-z\\d@$!%*?&]+$",
            message = "비밀번호는 대소문자, 숫자, 특수문자를 모두 포함해야 합니다"
        )
        private String password;

        @NotBlank(message = "비밀번호 확인은 필수입니다")
        private String confirmPassword;

        @NotBlank(message = "이름은 필수입니다")
        @Size(min = 2, max = 20, message = "이름은 2자 이상 20자 이하여야 합니다")
        private String name;

        @Pattern(
            regexp = "^01[0-9]-?[0-9]{3,4}-?[0-9]{4}$",
            message = "올바른 휴대폰 번호 형식이 아닙니다"
        )
        private String phone;

        private String role = "CUSTOMER"; // 기본값: 고객
    }

    /**
     * 비밀번호 변경 요청 DTO
     */
    @Data
    public static class ChangePassword {
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

    /**
     * 비밀번호 재설정 요청 DTO
     */
    @Data
    public static class ResetPassword {
        @NotBlank(message = "이메일은 필수입니다")
        @Email(message = "올바른 이메일 형식이 아닙니다")
        private String email;
    }

    /**
     * 이메일 인증 요청 DTO
     */
    @Data
    public static class VerifyEmail {
        @NotBlank(message = "이메일은 필수입니다")
        @Email(message = "올바른 이메일 형식이 아닙니다")
        private String email;

        @NotBlank(message = "인증 코드는 필수입니다")
        @Size(min = 6, max = 6, message = "인증 코드는 6자리입니다")
        private String verificationCode;
    }

    /**
     * 토큰 갱신 요청 DTO
     */
    @Data
    public static class RefreshToken {
        @NotBlank(message = "리프레시 토큰은 필수입니다")
        private String refreshToken;
    }
} 