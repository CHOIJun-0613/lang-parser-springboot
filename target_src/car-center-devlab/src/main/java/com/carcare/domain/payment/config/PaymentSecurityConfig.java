package com.carcare.domain.payment.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;

import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.SecretKeySpec;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.util.Base64;

/**
 * 결제 보안 설정
 */
@Configuration
public class PaymentSecurityConfig {
    
    /**
     * 보안 난수 생성기
     */
    @Bean
    public SecureRandom secureRandom() {
        return new SecureRandom();
    }
    
    /**
     * AES 암호화용 키 생성기
     */
    @Bean
    public KeyGenerator aesKeyGenerator() throws NoSuchAlgorithmException {
        KeyGenerator keyGenerator = KeyGenerator.getInstance("AES");
        keyGenerator.init(256, secureRandom());
        return keyGenerator;
    }
    
    /**
     * 결제 데이터 암호화용 AES 키
     */
    @Bean
    public SecretKey paymentEncryptionKey() throws NoSuchAlgorithmException {
        return aesKeyGenerator().generateKey();
    }
    
    /**
     * Base64 인코더
     */
    @Bean
    public Base64.Encoder base64Encoder() {
        return Base64.getEncoder();
    }
    
    /**
     * Base64 디코더
     */
    @Bean
    public Base64.Decoder base64Decoder() {
        return Base64.getDecoder();
    }
} 