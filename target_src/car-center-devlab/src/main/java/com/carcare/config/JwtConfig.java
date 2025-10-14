package com.carcare.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

/**
 * JWT 설정 프로퍼티
 */
@Configuration
@ConfigurationProperties(prefix = "app.jwt")
@Data
public class JwtConfig {
    
    /**
     * JWT 서명용 비밀키 (Base64 인코딩)
     * 운영 환경에서는 환경변수로 관리해야 함
     */
    private String secret = "Y2FyY2FyZS1qd3Qtc2VjcmV0LWtleS1mb3ItaGFzaC1zaWduaW5nLWFuZC12ZXJpZmljYXRpb24tMjAyNAr";
    
    /**
     * 액세스 토큰 만료 시간 (밀리초)
     * 기본값: 1시간 (3600000ms)
     */
    private long accessTokenExpiration = 3600000L;
    
    /**
     * 리프레시 토큰 만료 시간 (밀리초)
     * 기본값: 7일 (604800000ms)
     */
    private long refreshTokenExpiration = 604800000L;
    
    /**
     * JWT 토큰 발급자
     */
    private String issuer = "carcare-api";
    
    /**
     * JWT 토큰 대상
     */
    private String audience = "carcare-client";
} 