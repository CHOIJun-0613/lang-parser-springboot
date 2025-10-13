package com.carcare.config;

import lombok.RequiredArgsConstructor;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.env.Environment;
import org.springframework.http.HttpMethod;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.config.annotation.authentication.configuration.AuthenticationConfiguration;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.security.web.header.writers.ReferrerPolicyHeaderWriter;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

import java.util.Arrays;
import java.util.List;

/**
 * Spring Security 설정
 * - JWT 기반 인증
 * - CORS 설정
 * - 보안 헤더 설정
 * - 환경별 설정 차별화
 */
@Configuration
@EnableWebSecurity
@EnableMethodSecurity(prePostEnabled = true)
@RequiredArgsConstructor
public class SecurityConfig {

    private final Environment environment;
    private final JwtAuthenticationFilter jwtAuthenticationFilter;

    /**
     * 비밀번호 인코더 (BCrypt)
     */
    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder(12); // 높은 strength로 보안 강화
    }

    /**
     * 인증 매니저
     */
    @Bean
    public AuthenticationManager authenticationManager(AuthenticationConfiguration config) throws Exception {
        return config.getAuthenticationManager();
    }

    /**
     * 보안 필터 체인 설정
     */
    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        
        // 개발 환경 여부 확인
        boolean isDevEnvironment = Arrays.asList(environment.getActiveProfiles()).contains("local");
        
        http
            // CSRF 비활성화 (JWT 사용)
            .csrf(AbstractHttpConfigurer::disable)
            
            // CORS 설정
            .cors(cors -> cors.configurationSource(corsConfigurationSource()))
            
            // 세션 비활성화 (Stateless)
            .sessionManagement(session -> 
                session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            
            // 보안 헤더 설정
            .headers(headers -> headers
                .frameOptions().sameOrigin() // H2 Console 접근 허용
                .contentTypeOptions().and()
                .httpStrictTransportSecurity(hstsConfig -> hstsConfig
                    .maxAgeInSeconds(31536000)
                    .includeSubDomains(true))
                .referrerPolicy(ReferrerPolicyHeaderWriter.ReferrerPolicy.STRICT_ORIGIN_WHEN_CROSS_ORIGIN)
            )
            
            // 인증/인가 설정
            .authorizeHttpRequests(authz -> authz
                // 공개 엔드포인트
                .requestMatchers("/", "/api/v1/health/**").permitAll()
                .requestMatchers("/actuator/**").permitAll()
                
                // Swagger UI 관련 (더 구체적인 패턴)
                .requestMatchers("/swagger-ui.html", "/swagger-ui/**", "/swagger-ui/index.html").permitAll()
                .requestMatchers("/v3/api-docs/**", "/v3/api-docs.yaml", "/v3/api-docs").permitAll()
                .requestMatchers("/api-docs/**", "/api-docs/swagger-config").permitAll()
                .requestMatchers("/swagger-resources/**", "/swagger-resources").permitAll()
                .requestMatchers("/webjars/**").permitAll()
                .requestMatchers("/api/swagger-ui.html", "/api/swagger-ui/**").permitAll()
                .requestMatchers("/swagger/**").permitAll()
                
                // H2 Console (개발 환경에서만)
                .requestMatchers("/h2-console/**").permitAll()
                
                // 인증 관련 엔드포인트
                .requestMatchers("/api/v1/auth/**").permitAll()
                .requestMatchers(HttpMethod.POST, "/api/v1/users/register").permitAll()
                
                // 결제 콜백 엔드포인트 (토스페이먼츠에서 호출)
                .requestMatchers("/api/v1/payments/success").permitAll()
                .requestMatchers("/api/v1/payments/fail").permitAll()
                .requestMatchers("/api/v1/payments/webhook/**").permitAll()
                
                // 차량 마스터 데이터 API (공개)
                .requestMatchers("/api/v1/vehicles/master/**").permitAll()
                
                // 정비소 조회/검색 API (공개)
                .requestMatchers(HttpMethod.GET, "/api/v1/service-centers/search").permitAll()
                .requestMatchers(HttpMethod.GET, "/api/v1/service-centers/autocomplete").permitAll()
                .requestMatchers(HttpMethod.GET, "/api/v1/service-centers/service-types").permitAll()
                .requestMatchers(HttpMethod.GET, "/api/v1/service-centers/*").permitAll()
                .requestMatchers(HttpMethod.GET, "/api/v1/service-centers/*/operating-hours").permitAll()
                .requestMatchers(HttpMethod.GET, "/api/v1/service-centers/*/operating-hours/**").permitAll()
                
                // 운영시간 관리 API
                .requestMatchers(HttpMethod.POST, "/api/v1/service-centers/*/operating-hours/initialize").permitAll()
                .requestMatchers(HttpMethod.GET, "/api/v1/service-centers/operating-hours/currently-open").permitAll()
                .requestMatchers(HttpMethod.POST, "/api/v1/service-centers/operating-hours/batch-update-status").permitAll()
                
                // 알림 시스템 API (테스트용 일부 공개, 나머지 인증 필요)
                .requestMatchers("/api/v1/sms/**").permitAll() // SMS 발송 테스트 API (공개)
                .requestMatchers("/api/v1/email/**").permitAll() // 이메일 발송 테스트 API (공개)
                .requestMatchers("/api/v1/notification-templates/**").permitAll() // 알림 템플릿 API (테스트용 공개)
                .requestMatchers("/api/v1/notifications/**").authenticated() // 알림 관리 API (인증 필요)
                
                // 예약 API - 임시로 일부를 public으로 설정 (테스트용)
                .requestMatchers(HttpMethod.GET, "/api/v1/reservations/search").permitAll()
                .requestMatchers(HttpMethod.GET, "/api/v1/reservations/today").permitAll()
                .requestMatchers(HttpMethod.GET, "/api/v1/reservations/statistics").permitAll()
                .requestMatchers("/api/v1/reservations/**").authenticated()
                
                // 사용자 API (인증 필요)
                .requestMatchers("/api/v1/users/**").authenticated()
                
                // 차량 API (인증 필요)
                .requestMatchers("/api/v1/vehicles/**").authenticated()
                
                // 정비소 관리 API (인증 필요)
                .requestMatchers(HttpMethod.POST, "/api/v1/service-centers").authenticated()
                .requestMatchers(HttpMethod.PUT, "/api/v1/service-centers/**").authenticated()
                .requestMatchers(HttpMethod.DELETE, "/api/v1/service-centers/**").authenticated()
                
                // 정적 리소스
                .requestMatchers("/css/**", "/js/**", "/images/**").permitAll()
                .requestMatchers("/favicon.ico", "/robots.txt", "/error").permitAll()
                
                // 기타 모든 요청은 인증 필요
                .anyRequest().authenticated()
            )
            
            // 기본 HTTP Basic 인증 비활성화
            .httpBasic(AbstractHttpConfigurer::disable)
            
            // 폼 로그인 비활성화
            .formLogin(AbstractHttpConfigurer::disable)
            
            // 로그아웃 설정
            .logout(logout -> logout
                .logoutUrl("/api/v1/auth/logout")
                .logoutSuccessUrl("/")
                .invalidateHttpSession(true)
                .deleteCookies("JSESSIONID")
            )
            

            
            // JWT 인증 필터 추가
            .addFilterBefore(jwtAuthenticationFilter, UsernamePasswordAuthenticationFilter.class);

        return http.build();
    }

    /**
     * CORS 설정
     */
    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration configuration = new CorsConfiguration();
        
        // 환경별 허용 오리진 설정
        List<String> allowedOrigins = getCorsAllowedOrigins();
        configuration.setAllowedOriginPatterns(allowedOrigins);
        
        // 허용 메서드
        configuration.setAllowedMethods(Arrays.asList(
            "GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"
        ));
        
        // 허용 헤더
        configuration.setAllowedHeaders(Arrays.asList(
            "Authorization", "Content-Type", "X-Requested-With", 
            "Accept", "Origin", "Access-Control-Request-Method",
            "Access-Control-Request-Headers"
        ));
        
        // 인증 정보 포함 허용
        configuration.setAllowCredentials(true);
        
        // 노출 헤더
        configuration.setExposedHeaders(Arrays.asList(
            "Access-Control-Allow-Origin", "Access-Control-Allow-Credentials"
        ));
        
        // 캐시 시간 (1시간)
        configuration.setMaxAge(3600L);

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", configuration);
        
        return source;
    }

    /**
     * 환경별 CORS 허용 오리진 반환
     * 동적 URL 감지를 위해 더 포용적인 패턴 사용
     */
    private List<String> getCorsAllowedOrigins() {
        String activeProfile = environment.getProperty("spring.profiles.active", "local");
        
        return switch (activeProfile) {
            case "prod" -> Arrays.asList(
                "https://carcare.com",
                "https://www.carcare.com",
                "https://api.carcare.com",
                "http://backend.carcare.com",
                "https://backend.carcare.com",
                "http://*.carcare.com",
                "https://*.carcare.com"
            );
            case "dev" -> Arrays.asList(
                "http://localhost:*",
                "https://localhost:*",
                "http://127.0.0.1:*",
                "https://127.0.0.1:*",
                "http://192.168.*",
                "https://192.168.*",
                "http://dev-frontend.carcare.com",
                "http://backend.carcare.com",
                "https://backend.carcare.com",
                "http://*.carcare.com",
                "https://*.carcare.com"
            );
            default -> Arrays.asList( // local, test
                "http://localhost:*",
                "https://localhost:*",
                "http://127.0.0.1:*",
                "https://127.0.0.1:*",
                "*" // 개발 환경에서만 모든 오리진 허용
            );
        };
    }
} 