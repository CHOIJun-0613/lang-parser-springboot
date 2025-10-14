package com.carcare.domain.auth.controller;

import com.carcare.domain.auth.dto.AuthRequest;
import com.carcare.domain.auth.dto.AuthResponse;
import com.carcare.domain.auth.dto.SmsRequest;
import com.carcare.domain.auth.dto.SmsResponse;
import com.carcare.domain.auth.service.AuthService;
import com.carcare.domain.auth.service.SmsService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/**
 * 인증 관련 API 컨트롤러
 * 
 * 주요 기능:
 * - 회원가입
 * - 로그인/로그아웃
 * - 토큰 갱신
 * - 비밀번호 변경
 */
@Slf4j
@RestController
@RequestMapping("/api/v1/auth")
@RequiredArgsConstructor
@Tag(name = "인증 API", description = "사용자 인증 관련 API")
public class AuthController {

    private final AuthService authService;
    private final SmsService smsService;

    /**
     * 회원가입
     */
    @PostMapping("/register")
    @Operation(summary = "회원가입", description = "새로운 사용자 계정을 생성합니다")
    public ResponseEntity<AuthResponse.Register> register(
            @Valid @RequestBody AuthRequest.Register request) {
        
        log.info("회원가입 요청: {}", request.getEmail());
        
        AuthResponse.Register response = authService.register(request);
        return ResponseEntity.ok(response);
    }

    /**
     * 로그인
     */
    @PostMapping("/login")
    @Operation(summary = "로그인", description = "이메일과 비밀번호로 로그인합니다")
    public ResponseEntity<AuthResponse.Login> login(
            @Valid @RequestBody AuthRequest.Login request) {
        
        log.info("로그인 요청: {}", request.getEmail());
        
        AuthResponse.Login response = authService.login(request);
        return ResponseEntity.ok(response);
    }

    /**
     * 로그아웃
     */
    @PostMapping("/logout")
    @Operation(summary = "로그아웃", description = "현재 세션을 종료합니다")
    public ResponseEntity<AuthResponse.Logout> logout() {
        
        log.info("로그아웃 요청");
        
        AuthResponse.Logout response = authService.logout();
        return ResponseEntity.ok(response);
    }

    /**
     * 토큰 갱신
     */
    @PostMapping("/refresh")
    @Operation(summary = "토큰 갱신", description = "리프레시 토큰으로 새로운 액세스 토큰을 발급받습니다")
    public ResponseEntity<AuthResponse.RefreshToken> refreshToken(
            @Valid @RequestBody AuthRequest.RefreshToken request) {
        
        log.info("토큰 갱신 요청");
        
        AuthResponse.RefreshToken response = authService.refreshToken(request);
        return ResponseEntity.ok(response);
    }

    /**
     * 비밀번호 변경
     */
    @PutMapping("/change-password")
    @Operation(summary = "비밀번호 변경", description = "현재 비밀번호를 새로운 비밀번호로 변경합니다")
    public ResponseEntity<AuthResponse.Success> changePassword(
            @Valid @RequestBody AuthRequest.ChangePassword request) {
        
        log.info("비밀번호 변경 요청");
        
        AuthResponse.Success response = authService.changePassword(request);
        return ResponseEntity.ok(response);
    }

    /**
     * 비밀번호 재설정 요청
     */
    @PostMapping("/reset-password")
    @Operation(summary = "비밀번호 재설정 요청", description = "이메일로 비밀번호 재설정 링크를 발송합니다")
    public ResponseEntity<AuthResponse.PasswordReset> resetPassword(
            @Valid @RequestBody AuthRequest.ResetPassword request) {
        
        log.info("비밀번호 재설정 요청: {}", request.getEmail());
        
        // TODO: 비밀번호 재설정 구현
        AuthResponse.PasswordReset response = AuthResponse.PasswordReset.builder()
                .message("비밀번호 재설정 이메일이 발송되었습니다")
                .email(request.getEmail())
                .requestedAt(java.time.LocalDateTime.now())
                .build();
                
        return ResponseEntity.ok(response);
    }

    /**
     * 이메일 인증
     */
    @PostMapping("/verify-email")
    @Operation(summary = "이메일 인증", description = "이메일로 받은 인증 코드로 이메일을 인증합니다")
    public ResponseEntity<AuthResponse.EmailVerification> verifyEmail(
            @Valid @RequestBody AuthRequest.VerifyEmail request) {
        
        log.info("이메일 인증 요청: {}", request.getEmail());
        
        // TODO: 이메일 인증 구현
        AuthResponse.EmailVerification response = AuthResponse.EmailVerification.builder()
                .message("이메일 인증이 완료되었습니다")
                .verified(true)
                .email(request.getEmail())
                .verifiedAt(java.time.LocalDateTime.now())
                .build();
                
        return ResponseEntity.ok(response);
    }

    /**
     * SMS 인증번호 발송
     */
    @PostMapping("/sms/send")
    @Operation(summary = "SMS 인증번호 발송", description = "휴대폰 번호로 인증번호를 발송합니다")
    public ResponseEntity<SmsResponse.SendCode> sendSmsCode(
            @Valid @RequestBody SmsRequest.SendCode request) {
        
        log.info("SMS 인증번호 발송 요청: {}", request.getPhoneNumber());
        
        SmsResponse.SendCode response = smsService.sendVerificationCode(request);
        return ResponseEntity.ok(response);
    }

    /**
     * SMS 인증번호 검증
     */
    @PostMapping("/sms/verify")
    @Operation(summary = "SMS 인증번호 검증", description = "발송된 인증번호를 검증합니다")
    public ResponseEntity<SmsResponse.VerifyCode> verifySmsCode(
            @Valid @RequestBody SmsRequest.VerifyCode request) {
        
        log.info("SMS 인증번호 검증 요청: {}", request.getPhoneNumber());
        
        SmsResponse.VerifyCode response = smsService.verifyCode(request);
        return ResponseEntity.ok(response);
    }
} 