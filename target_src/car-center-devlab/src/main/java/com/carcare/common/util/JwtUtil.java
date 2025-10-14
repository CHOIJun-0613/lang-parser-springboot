package com.carcare.common.util;

import com.carcare.config.JwtConfig;
import io.jsonwebtoken.*;
import io.jsonwebtoken.security.Keys;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.util.Base64;
import java.util.Date;
import java.util.HashMap;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * JWT 토큰 생성, 검증, 파싱 유틸리티
 * 
 * 주요 기능:
 * - 액세스 토큰 및 리프레시 토큰 생성
 * - 토큰 검증 및 파싱
 * - 사용자 정보 추출
 * - 토큰 만료 확인
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class JwtUtil {

    private final JwtConfig jwtConfig;

    /**
     * 서명용 비밀키 생성
     */
    private SecretKey getSigningKey() {
        byte[] keyBytes = Base64.getDecoder().decode(jwtConfig.getSecret());
        return Keys.hmacShaKeyFor(keyBytes);
    }

    /**
     * 액세스 토큰 생성
     * 
     * @param authentication 인증 정보
     * @return JWT 액세스 토큰
     */
    public String generateAccessToken(Authentication authentication) {
        return generateToken(
            authentication, 
            jwtConfig.getAccessTokenExpiration(),
            "access"
        );
    }

    /**
     * 리프레시 토큰 생성
     * 
     * @param authentication 인증 정보
     * @return JWT 리프레시 토큰
     */
    public String generateRefreshToken(Authentication authentication) {
        return generateToken(
            authentication, 
            jwtConfig.getRefreshTokenExpiration(),
            "refresh"
        );
    }

    /**
     * 사용자 ID로 액세스 토큰 생성
     * 
     * @param userId 사용자 ID
     * @param userUuid 사용자 UUID
     * @param email 사용자 이메일
     * @param role 사용자 역할
     * @return JWT 액세스 토큰
     */
    public String generateAccessToken(Long userId, String userUuid, String email, String role) {
        Date now = new Date();
        Date expiration = new Date(now.getTime() + jwtConfig.getAccessTokenExpiration());

        Map<String, Object> claims = new HashMap<>();
        claims.put("userId", userId);
        claims.put("userUuid", userUuid);
        claims.put("email", email);
        claims.put("role", role);
        claims.put("type", "access");

        return Jwts.builder()
                .setClaims(claims)
                .setSubject(email)
                .setIssuer(jwtConfig.getIssuer())
                .setAudience(jwtConfig.getAudience())
                .setIssuedAt(now)
                .setExpiration(expiration)
                .signWith(getSigningKey())
                .compact();
    }

    /**
     * JWT 토큰 생성 (공통 로직)
     */
    private String generateToken(Authentication authentication, long expiration, String tokenType) {
        Date now = new Date();
        Date expirationDate = new Date(now.getTime() + expiration);

        // 권한 정보 추출
        String authorities = authentication.getAuthorities().stream()
                .map(GrantedAuthority::getAuthority)
                .collect(Collectors.joining(","));

        Map<String, Object> claims = new HashMap<>();
        claims.put("authorities", authorities);
        claims.put("type", tokenType);

        return Jwts.builder()
                .setClaims(claims)
                .setSubject(authentication.getName())
                .setIssuer(jwtConfig.getIssuer())
                .setAudience(jwtConfig.getAudience())
                .setIssuedAt(now)
                .setExpiration(expirationDate)
                .signWith(getSigningKey())
                .compact();
    }

    /**
     * JWT 토큰에서 사용자 이메일 추출
     * 
     * @param token JWT 토큰
     * @return 사용자 이메일
     */
    public String getUserEmailFromToken(String token) {
        return getClaims(token).getSubject();
    }

    /**
     * JWT 토큰에서 사용자 ID 추출
     * 
     * @param token JWT 토큰
     * @return 사용자 ID
     */
    public Long getUserIdFromToken(String token) {
        Claims claims = getClaims(token);
        return claims.get("userId", Long.class);
    }

    /**
     * JWT 토큰에서 사용자 UUID 추출
     * 
     * @param token JWT 토큰
     * @return 사용자 UUID
     */
    public String getUserUuidFromToken(String token) {
        Claims claims = getClaims(token);
        return claims.get("userUuid", String.class);
    }

    /**
     * JWT 토큰에서 사용자 역할 추출
     * 
     * @param token JWT 토큰
     * @return 사용자 역할
     */
    public String getUserRoleFromToken(String token) {
        Claims claims = getClaims(token);
        return claims.get("role", String.class);
    }

    /**
     * JWT 토큰에서 권한 정보 추출
     * 
     * @param token JWT 토큰
     * @return 권한 문자열
     */
    public String getAuthoritiesFromToken(String token) {
        Claims claims = getClaims(token);
        return claims.get("authorities", String.class);
    }

    /**
     * JWT 토큰에서 토큰 타입 추출
     * 
     * @param token JWT 토큰
     * @return 토큰 타입 (access/refresh)
     */
    public String getTokenTypeFromToken(String token) {
        Claims claims = getClaims(token);
        return claims.get("type", String.class);
    }

    /**
     * JWT 토큰 만료 시간 조회
     * 
     * @param token JWT 토큰
     * @return 만료 시간
     */
    public Date getExpirationFromToken(String token) {
        return getClaims(token).getExpiration();
    }

    /**
     * JWT 토큰 발급 시간 조회
     * 
     * @param token JWT 토큰
     * @return 발급 시간
     */
    public Date getIssuedAtFromToken(String token) {
        return getClaims(token).getIssuedAt();
    }

    /**
     * JWT 토큰 만료 여부 확인
     * 
     * @param token JWT 토큰
     * @return 만료 여부
     */
    public boolean isTokenExpired(String token) {
        try {
            Date expiration = getExpirationFromToken(token);
            return expiration.before(new Date());
        } catch (Exception e) {
            log.warn("토큰 만료 확인 중 오류 발생: {}", e.getMessage());
            return true;
        }
    }

    /**
     * JWT 토큰 유효성 검증
     * 
     * @param token JWT 토큰
     * @return 유효성 여부
     */
    public boolean validateToken(String token) {
        try {
            getClaims(token);
            return !isTokenExpired(token);
        } catch (SecurityException e) {
            log.warn("잘못된 JWT 서명: {}", e.getMessage());
        } catch (MalformedJwtException e) {
            log.warn("잘못된 JWT 토큰: {}", e.getMessage());
        } catch (ExpiredJwtException e) {
            log.warn("만료된 JWT 토큰: {}", e.getMessage());
        } catch (UnsupportedJwtException e) {
            log.warn("지원되지 않는 JWT 토큰: {}", e.getMessage());
        } catch (IllegalArgumentException e) {
            log.warn("JWT 토큰이 비어있습니다: {}", e.getMessage());
        } catch (Exception e) {
            log.warn("JWT 토큰 검증 실패: {}", e.getMessage());
        }
        return false;
    }

    /**
     * 특정 토큰 타입 검증
     * 
     * @param token JWT 토큰
     * @param expectedType 기대하는 토큰 타입
     * @return 타입 일치 여부
     */
    public boolean validateTokenType(String token, String expectedType) {
        try {
            String tokenType = getTokenTypeFromToken(token);
            return expectedType.equals(tokenType);
        } catch (Exception e) {
            log.warn("토큰 타입 확인 실패: {}", e.getMessage());
            return false;
        }
    }

    /**
     * JWT 토큰에서 Claims 추출 (내부 메서드)
     */
    private Claims getClaims(String token) {
        return Jwts.parser()
                .verifyWith(getSigningKey())
                .build()
                .parseSignedClaims(token)
                .getPayload();
    }

    /**
     * 토큰에서 Bearer 접두사 제거
     * 
     * @param bearerToken Bearer 토큰
     * @return 순수 JWT 토큰
     */
    public String extractTokenFromBearer(String bearerToken) {
        if (bearerToken != null && bearerToken.startsWith("Bearer ")) {
            return bearerToken.substring(7);
        }
        return bearerToken;
    }

    /**
     * 토큰 남은 만료 시간 계산 (초 단위)
     * 
     * @param token JWT 토큰
     * @return 남은 시간 (초)
     */
    public long getTimeToExpiration(String token) {
        try {
            Date expiration = getExpirationFromToken(token);
            long timeToExpiration = (expiration.getTime() - System.currentTimeMillis()) / 1000;
            return Math.max(0, timeToExpiration);
        } catch (Exception e) {
            return 0;
        }
    }
} 