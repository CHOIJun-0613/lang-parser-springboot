package com.carcare.config;

import com.carcare.common.util.JwtUtil;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.stream.Collectors;

/**
 * JWT 인증 필터
 * 
 * 모든 HTTP 요청에서 JWT 토큰을 확인하고 인증 처리
 * - Authorization 헤더에서 Bearer 토큰 추출
 * - JWT 토큰 유효성 검증
 * - 인증 정보를 SecurityContext에 설정
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    private final JwtUtil jwtUtil;

    /**
     * 필터링 제외 경로들
     */
    private static final List<String> EXCLUDED_PATHS = Arrays.asList(
        "/api/v1/auth/",
        "/api/v1/health",
        "/actuator/",
        "/swagger-ui",
        "/swagger-ui.html",
        "/swagger-ui/",
        "/v3/api-docs",
        "/api-docs",
        "/swagger-resources",
        "/webjars/",
        "/h2-console/",
        "/favicon.ico",
        "/robots.txt",
        "/error",
        // 결제 콜백 엔드포인트
        "/api/v1/payments/success",
        "/api/v1/payments/fail",
        "/api/v1/payments/webhook/"
    );

    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain) throws ServletException, IOException {

        try {
            // JWT 토큰 추출
            String token = extractTokenFromRequest(request);
            
            if (token != null && jwtUtil.validateToken(token)) {
                // 액세스 토큰만 허용
                if (jwtUtil.validateTokenType(token, "access")) {
                    // 인증 정보 설정
                    setAuthenticationFromToken(token, request);
                } else {
                    log.warn("잘못된 토큰 타입. 액세스 토큰이 필요합니다.");
                }
            }
        } catch (Exception e) {
            log.error("JWT 인증 처리 중 오류 발생: {}", e.getMessage());
            // 오류가 발생해도 필터 체인은 계속 진행
        }

        filterChain.doFilter(request, response);
    }

    /**
     * 요청에서 JWT 토큰 추출
     */
    private String extractTokenFromRequest(HttpServletRequest request) {
        // Authorization 헤더에서 토큰 추출
        String bearerToken = request.getHeader("Authorization");
        
        if (StringUtils.hasText(bearerToken) && bearerToken.startsWith("Bearer ")) {
            return jwtUtil.extractTokenFromBearer(bearerToken);
        }
        
        // 쿼리 파라미터에서 토큰 추출 (WebSocket 등 특별한 경우)
        String queryToken = request.getParameter("token");
        if (StringUtils.hasText(queryToken)) {
            return queryToken;
        }
        
        return null;
    }

    /**
     * JWT 토큰에서 인증 정보 추출하여 SecurityContext에 설정
     */
    private void setAuthenticationFromToken(String token, HttpServletRequest request) {
        try {
            // 토큰에서 사용자 정보 추출
            String userEmail = jwtUtil.getUserEmailFromToken(token);
            Long userId = jwtUtil.getUserIdFromToken(token);
            String userUuid = jwtUtil.getUserUuidFromToken(token);
            String role = jwtUtil.getUserRoleFromToken(token);
            String authorities = jwtUtil.getAuthoritiesFromToken(token);

            // 권한 정보 생성
            List<SimpleGrantedAuthority> authoritiesList = createAuthorities(role, authorities);

            // 사용자 정보 객체 생성 (간단한 Principal 객체)
            JwtUserPrincipal userPrincipal = new JwtUserPrincipal(
                userId, userUuid, userEmail, role, authoritiesList
            );

            // 인증 토큰 생성
            UsernamePasswordAuthenticationToken authentication = 
                new UsernamePasswordAuthenticationToken(
                    userPrincipal, 
                    null, 
                    authoritiesList
                );
            
            authentication.setDetails(new WebAuthenticationDetailsSource().buildDetails(request));

            // SecurityContext에 인증 정보 설정
            SecurityContextHolder.getContext().setAuthentication(authentication);
            
            log.debug("JWT 인증 성공 - 사용자: {}, 역할: {}", userEmail, role);
            
        } catch (Exception e) {
            log.error("JWT 토큰에서 인증 정보 설정 실패: {}", e.getMessage());
        }
    }

    /**
     * 역할과 권한 문자열에서 권한 리스트 생성
     */
    private List<SimpleGrantedAuthority> createAuthorities(String role, String authoritiesStr) {
        List<SimpleGrantedAuthority> authorities = 
            Collections.singletonList(new SimpleGrantedAuthority("ROLE_" + role));

        // 추가 권한이 있는 경우 처리
        if (StringUtils.hasText(authoritiesStr)) {
            List<SimpleGrantedAuthority> additionalAuthorities = Arrays.stream(authoritiesStr.split(","))
                .map(String::trim)
                .filter(StringUtils::hasText)
                .map(SimpleGrantedAuthority::new)
                .collect(Collectors.toList());
            
            authorities.addAll(additionalAuthorities);
        }

        return authorities;
    }

    /**
     * 필터 적용 여부 결정
     * 제외 경로는 필터링하지 않음
     */
    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) throws ServletException {
        String path = request.getRequestURI();
        
        return EXCLUDED_PATHS.stream()
            .anyMatch(excludedPath -> path.startsWith(excludedPath));
    }

    /**
     * JWT 토큰에서 추출한 사용자 정보를 담는 Principal 클래스
     */
    public static class JwtUserPrincipal {
        private final Long userId;
        private final String userUuid;
        private final String email;
        private final String role;
        private final List<SimpleGrantedAuthority> authorities;

        public JwtUserPrincipal(Long userId, String userUuid, String email, String role, 
                              List<SimpleGrantedAuthority> authorities) {
            this.userId = userId;
            this.userUuid = userUuid;
            this.email = email;
            this.role = role;
            this.authorities = authorities;
        }

        // Getters
        public Long getUserId() { return userId; }
        public String getUserUuid() { return userUuid; }
        public String getEmail() { return email; }
        public String getRole() { return role; }
        public List<SimpleGrantedAuthority> getAuthorities() { return authorities; }

        @Override
        public String toString() {
            return email;
        }
    }
} 