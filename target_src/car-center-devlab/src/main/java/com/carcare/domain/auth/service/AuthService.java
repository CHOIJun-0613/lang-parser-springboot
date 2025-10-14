package com.carcare.domain.auth.service;

import com.carcare.common.exception.BusinessException;
import com.carcare.common.util.JwtUtil;
import com.carcare.config.JwtAuthenticationFilter;
import com.carcare.domain.auth.dto.AuthRequest;
import com.carcare.domain.auth.dto.AuthResponse;
import com.carcare.domain.user.entity.User;
import com.carcare.domain.user.mapper.UserMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.Optional;
import java.util.UUID;

/**
 * 인증 서비스
 * 
 * 주요 기능:
 * - 사용자 회원가입
 * - 로그인/로그아웃
 * - 토큰 갱신
 * - 비밀번호 변경/재설정
 * - 이메일 인증
 */
@Slf4j
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class AuthService {

    private final UserMapper userMapper;
    private final PasswordEncoder passwordEncoder;
    private final JwtUtil jwtUtil;

    /**
     * 사용자 회원가입
     */
    @Transactional
    public AuthResponse.Register register(AuthRequest.Register request) {
        log.info("회원가입 시도: {}", request.getEmail());

        // 1. 유효성 검증
        validateRegisterRequest(request);

        // 2. 이메일 중복 확인
        if (userMapper.existsByEmail(request.getEmail())) {
            throw new BusinessException("이미 등록된 이메일입니다: " + request.getEmail());
        }

        // 3. 비밀번호 확인
        if (!request.getPassword().equals(request.getConfirmPassword())) {
            throw new BusinessException("비밀번호와 비밀번호 확인이 일치하지 않습니다");
        }

        // 4. 사용자 생성
        User user = createUser(request);
        userMapper.insertUser(user);

        log.info("회원가입 완료: {} (ID: {})", user.getEmail(), user.getId());

        // 5. 응답 생성
        return AuthResponse.Register.builder()
                .message("회원가입이 성공적으로 완료되었습니다")
                .user(convertToUserInfo(user))
                .emailVerificationRequired(true)
                .registeredAt(LocalDateTime.now())
                .build();
    }

    /**
     * 사용자 로그인
     */
    @Transactional
    public AuthResponse.Login login(AuthRequest.Login request) {
        log.info("로그인 시도: {}", request.getEmail());

        // 1. 사용자 조회
        User user = userMapper.findByEmail(request.getEmail())
                .orElseThrow(() -> new BusinessException("존재하지 않는 사용자입니다"));

        // 2. 계정 활성 상태 확인
        if (!user.getIsActive()) {
            throw new BusinessException("비활성화된 계정입니다");
        }

        // 3. 비밀번호 검증
        if (!passwordEncoder.matches(request.getPassword(), user.getPassword())) {
            throw new BusinessException("비밀번호가 올바르지 않습니다");
        }

        // 4. 로그인 시간 업데이트
        user.setLastLoginAt(LocalDateTime.now());
        userMapper.updateUser(user);

        // 5. JWT 토큰 생성
        String accessToken = jwtUtil.generateAccessToken(
            user.getId(), user.getUserUuid(), user.getEmail(), user.getRole()
        );
        
        // 리프레시 토큰도 사용자 정보로 생성 (임시)
        String refreshToken = jwtUtil.generateAccessToken(
            user.getId(), user.getUserUuid(), user.getEmail(), user.getRole()
        );

        log.info("로그인 성공: {} (ID: {})", user.getEmail(), user.getId());

        // 6. 응답 생성
        return AuthResponse.Login.builder()
                .accessToken(accessToken)
                .refreshToken(refreshToken)
                .tokenType("Bearer")
                .expiresIn(3600L) // 1시간
                .user(convertToUserInfo(user))
                .loginTime(LocalDateTime.now())
                .build();
    }

    /**
     * 토큰 갱신
     */
    public AuthResponse.RefreshToken refreshToken(AuthRequest.RefreshToken request) {
        log.info("토큰 갱신 요청");

        String refreshToken = request.getRefreshToken();

        // 1. 리프레시 토큰 유효성 검증
        if (!jwtUtil.validateToken(refreshToken)) {
            throw new BusinessException("유효하지 않은 리프레시 토큰입니다");
        }

        // 2. 토큰에서 사용자 정보 추출
        Long userId = jwtUtil.getUserIdFromToken(refreshToken);
        String userUuid = jwtUtil.getUserUuidFromToken(refreshToken);
        String email = jwtUtil.getUserEmailFromToken(refreshToken);
        String role = jwtUtil.getUserRoleFromToken(refreshToken);

        // 3. 사용자 존재 및 활성 상태 확인
        User user = userMapper.findById(userId)
                .orElseThrow(() -> new BusinessException("존재하지 않는 사용자입니다"));

        if (!user.getIsActive()) {
            throw new BusinessException("비활성화된 계정입니다");
        }

        // 4. 새로운 토큰 생성
        String newAccessToken = jwtUtil.generateAccessToken(userId, userUuid, email, role);
        String newRefreshToken = jwtUtil.generateAccessToken(userId, userUuid, email, role);

        log.info("토큰 갱신 성공: {}", email);

        // 5. 응답 생성
        return AuthResponse.RefreshToken.builder()
                .accessToken(newAccessToken)
                .refreshToken(newRefreshToken)
                .tokenType("Bearer")
                .expiresIn(3600L)
                .refreshedAt(LocalDateTime.now())
                .build();
    }

    /**
     * 비밀번호 변경
     */
    @Transactional
    public AuthResponse.Success changePassword(AuthRequest.ChangePassword request) {
        // 현재 인증된 사용자 정보 조회
        JwtAuthenticationFilter.JwtUserPrincipal principal = getCurrentUser();
        User user = userMapper.findById(principal.getUserId())
                .orElseThrow(() -> new BusinessException("존재하지 않는 사용자입니다"));

        // 1. 현재 비밀번호 확인
        if (!passwordEncoder.matches(request.getCurrentPassword(), user.getPassword())) {
            throw new BusinessException("현재 비밀번호가 올바르지 않습니다");
        }

        // 2. 새 비밀번호 확인
        if (!request.getNewPassword().equals(request.getConfirmNewPassword())) {
            throw new BusinessException("새 비밀번호와 새 비밀번호 확인이 일치하지 않습니다");
        }

        // 3. 비밀번호 업데이트
        user.setPassword(passwordEncoder.encode(request.getNewPassword()));
        user.setUpdatedAt(LocalDateTime.now());
        userMapper.updateUser(user);

        log.info("비밀번호 변경 완료: {}", user.getEmail());

        return AuthResponse.Success.builder()
                .message("비밀번호가 성공적으로 변경되었습니다")
                .timestamp(LocalDateTime.now())
                .build();
    }

    /**
     * 로그아웃
     */
    public AuthResponse.Logout logout() {
        // 현재 인증 정보 제거
        SecurityContextHolder.clearContext();
        
        log.info("로그아웃 완료");

        return AuthResponse.Logout.builder()
                .message("로그아웃이 완료되었습니다")
                .logoutTime(LocalDateTime.now())
                .build();
    }

    /**
     * 회원가입 요청 유효성 검증
     */
    private void validateRegisterRequest(AuthRequest.Register request) {
        if (request.getEmail() == null || request.getEmail().trim().isEmpty()) {
            throw new BusinessException("이메일은 필수입니다");
        }
        if (request.getPassword() == null || request.getPassword().length() < 8) {
            throw new BusinessException("비밀번호는 8자 이상이어야 합니다");
        }
        if (request.getName() == null || request.getName().trim().isEmpty()) {
            throw new BusinessException("이름은 필수입니다");
        }
    }

    /**
     * 회원가입 요청으로부터 User 엔티티 생성
     */
    private User createUser(AuthRequest.Register request) {
        User user = new User();
        user.setUserUuid(UUID.randomUUID().toString());
        user.setEmail(request.getEmail());
        user.setPassword(passwordEncoder.encode(request.getPassword()));
        user.setName(request.getName());
        user.setPhone(request.getPhone());
        user.setRole(request.getRole());
        user.setIsActive(true);
        user.setEmailVerified(false); // 이메일 인증은 별도 처리
        user.setCreatedAt(LocalDateTime.now());
        user.setUpdatedAt(LocalDateTime.now());
        return user;
    }

    /**
     * User 엔티티를 UserInfo DTO로 변환
     */
    private AuthResponse.UserInfo convertToUserInfo(User user) {
        return AuthResponse.UserInfo.builder()
                .id(user.getId())
                .userUuid(user.getUserUuid())
                .email(user.getEmail())
                .name(user.getName())
                .phone(user.getPhone())
                .role(user.getRole())
                .isActive(user.getIsActive())
                .emailVerified(user.getEmailVerified())
                .lastLoginAt(user.getLastLoginAt())
                .createdAt(user.getCreatedAt())
                .build();
    }

    /**
     * 현재 인증된 사용자 정보 조회
     */
    private JwtAuthenticationFilter.JwtUserPrincipal getCurrentUser() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication == null || !(authentication.getPrincipal() instanceof JwtAuthenticationFilter.JwtUserPrincipal)) {
            throw new BusinessException("인증되지 않은 사용자입니다");
        }
        return (JwtAuthenticationFilter.JwtUserPrincipal) authentication.getPrincipal();
    }
} 