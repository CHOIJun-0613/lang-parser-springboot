package com.carcare.domain.payment.config;

import lombok.Getter;
import lombok.Setter;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

/**
 * 토스페이먼츠 설정
 */
@Getter
@Setter
@Configuration
@ConfigurationProperties(prefix = "toss.payments")
public class TossPaymentsConfig {
    
    /**
     * 토스페이먼츠 API 기본 URL
     */
    private String baseUrl = "https://api.tosspayments.com";
    
    /**
     * 시크릿 키
     */
    private String secretKey;
    
    /**
     * 클라이언트 키
     */
    private String clientKey;
    
    /**
     * 성공 URL
     */
    private String successUrl;
    
    /**
     * 실패 URL
     */
    private String failUrl;
    
    /**
     * 웹훅 시크릿
     */
    private String webhookSecret;
    
    /**
     * 타임아웃 (초)
     */
    private int timeout = 30;
    
    /**
     * 재시도 횟수
     */
    private int retryCount = 3;
    
    /**
     * 테스트 모드 여부
     */
    private boolean testMode = false;
} 