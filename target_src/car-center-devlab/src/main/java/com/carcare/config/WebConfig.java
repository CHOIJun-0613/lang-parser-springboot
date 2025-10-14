package com.carcare.config;

import org.apache.hc.client5.http.impl.classic.CloseableHttpClient;
import org.apache.hc.client5.http.impl.classic.HttpClients;
import org.apache.hc.client5.http.impl.io.PoolingHttpClientConnectionManagerBuilder;
import org.apache.hc.client5.http.ssl.SSLConnectionSocketFactory;
import org.apache.hc.client5.http.ssl.TrustAllStrategy;
import org.apache.hc.core5.ssl.SSLContextBuilder;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.HttpComponentsClientHttpRequestFactory;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.filter.ForwardedHeaderFilter;

import javax.net.ssl.SSLContext;
import java.security.KeyManagementException;
import java.security.KeyStoreException;
import java.security.NoSuchAlgorithmException;
import java.time.Duration;

/**
 * 웹 설정
 */
@Configuration
public class WebConfig {
    
    @Value("${spring.profiles.active:local}")
    private String activeProfile;
    
    /**
     * ForwardedHeaderFilter 등록
     * 프록시 환경에서 X-Forwarded-* 헤더를 통해 원본 요청 정보를 복원
     * 지원하는 헤더:
     * - X-Forwarded-Host: 원본 호스트
     * - X-Forwarded-Port: 원본 포트
     * - X-Forwarded-Proto: 원본 프로토콜 (http/https)
     * - X-Forwarded-For: 클라이언트 IP
     * - X-Real-IP: 실제 클라이언트 IP (nginx)
     */
    @Bean
    public FilterRegistrationBean<ForwardedHeaderFilter> forwardedHeaderFilter() {
        FilterRegistrationBean<ForwardedHeaderFilter> bean = new FilterRegistrationBean<>();
        bean.setFilter(new ForwardedHeaderFilter());
        bean.setOrder(0); // 가장 먼저 실행
        bean.addUrlPatterns("/*"); // 모든 URL에 적용
        return bean;
    }
    
    /**
     * RestTemplate 빈 설정
     */
    @Bean
    public RestTemplate restTemplate() throws Exception {
        HttpComponentsClientHttpRequestFactory factory = new HttpComponentsClientHttpRequestFactory();
        factory.setConnectTimeout(30000); // 30초
        factory.setReadTimeout(30000); // 30초
        
        // 개발 환경에서만 SSL 검증 우회
        if ("dev".equals(activeProfile) || "local".equals(activeProfile)) {
            CloseableHttpClient httpClient = createInsecureHttpClient();
            factory.setHttpClient(httpClient);
        }
        
        return new RestTemplate(factory);
    }
    
    /**
     * SSL 검증을 우회하는 HttpClient 생성 (개발 환경 전용)
     */
    private CloseableHttpClient createInsecureHttpClient() throws Exception {
        try {
            SSLContext sslContext = SSLContextBuilder.create()
                    .loadTrustMaterial(null, TrustAllStrategy.INSTANCE)
                    .build();
            
            SSLConnectionSocketFactory sslSocketFactory = new SSLConnectionSocketFactory(
                    sslContext, 
                    (hostname, session) -> true  // 모든 호스트명 허용
            );
            
            return HttpClients.custom()
                    .setConnectionManager(
                            PoolingHttpClientConnectionManagerBuilder.create()
                                    .setSSLSocketFactory(sslSocketFactory)
                                    .build()
                    )
                    .build();
                    
        } catch (NoSuchAlgorithmException | KeyStoreException | KeyManagementException e) {
            throw new RuntimeException("SSL 설정 중 오류가 발생했습니다", e);
        }
    }
} 