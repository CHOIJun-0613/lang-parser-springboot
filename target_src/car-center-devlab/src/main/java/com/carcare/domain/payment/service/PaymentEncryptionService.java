package com.carcare.domain.payment.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import javax.crypto.Cipher;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.util.Base64;

/**
 * 결제 데이터 암호화 서비스
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class PaymentEncryptionService {
    
    private final SecretKey paymentEncryptionKey;
    private final SecureRandom secureRandom;
    private final Base64.Encoder base64Encoder;
    private final Base64.Decoder base64Decoder;
    
    private static final String ALGORITHM = "AES";
    private static final String TRANSFORMATION = "AES/GCM/NoPadding";
    private static final int GCM_IV_LENGTH = 12; // 96 bits
    private static final int GCM_TAG_LENGTH = 16; // 128 bits
    
    /**
     * 민감한 결제 데이터 암호화
     */
    public String encrypt(String plainText) {
        try {
            if (plainText == null || plainText.trim().isEmpty()) {
                return plainText;
            }
            
            // IV 생성
            byte[] iv = new byte[GCM_IV_LENGTH];
            secureRandom.nextBytes(iv);
            
            // 암호화
            Cipher cipher = Cipher.getInstance(TRANSFORMATION);
            GCMParameterSpec parameterSpec = new GCMParameterSpec(GCM_TAG_LENGTH * 8, iv);
            cipher.init(Cipher.ENCRYPT_MODE, paymentEncryptionKey, parameterSpec);
            
            byte[] encryptedData = cipher.doFinal(plainText.getBytes(StandardCharsets.UTF_8));
            
            // IV + 암호화된 데이터를 결합하여 Base64 인코딩
            byte[] encryptedWithIv = new byte[GCM_IV_LENGTH + encryptedData.length];
            System.arraycopy(iv, 0, encryptedWithIv, 0, GCM_IV_LENGTH);
            System.arraycopy(encryptedData, 0, encryptedWithIv, GCM_IV_LENGTH, encryptedData.length);
            
            return base64Encoder.encodeToString(encryptedWithIv);
            
        } catch (Exception e) {
            log.error("Error encrypting payment data", e);
            throw new RuntimeException("데이터 암호화에 실패했습니다.", e);
        }
    }
    
    /**
     * 암호화된 결제 데이터 복호화
     */
    public String decrypt(String encryptedText) {
        try {
            if (encryptedText == null || encryptedText.trim().isEmpty()) {
                return encryptedText;
            }
            
            // Base64 디코딩
            byte[] encryptedWithIv = base64Decoder.decode(encryptedText);
            
            // IV와 암호화된 데이터 분리
            byte[] iv = new byte[GCM_IV_LENGTH];
            byte[] encryptedData = new byte[encryptedWithIv.length - GCM_IV_LENGTH];
            
            System.arraycopy(encryptedWithIv, 0, iv, 0, GCM_IV_LENGTH);
            System.arraycopy(encryptedWithIv, GCM_IV_LENGTH, encryptedData, 0, encryptedData.length);
            
            // 복호화
            Cipher cipher = Cipher.getInstance(TRANSFORMATION);
            GCMParameterSpec parameterSpec = new GCMParameterSpec(GCM_TAG_LENGTH * 8, iv);
            cipher.init(Cipher.DECRYPT_MODE, paymentEncryptionKey, parameterSpec);
            
            byte[] decryptedData = cipher.doFinal(encryptedData);
            
            return new String(decryptedData, StandardCharsets.UTF_8);
            
        } catch (Exception e) {
            log.error("Error decrypting payment data", e);
            throw new RuntimeException("데이터 복호화에 실패했습니다.", e);
        }
    }
    
    /**
     * 카드 번호 마스킹 처리
     */
    public String maskCardNumber(String cardNumber) {
        if (cardNumber == null || cardNumber.length() < 8) {
            return cardNumber;
        }
        
        // 앞 4자리와 뒤 4자리만 보이도록 마스킹
        String prefix = cardNumber.substring(0, 4);
        String suffix = cardNumber.substring(cardNumber.length() - 4);
        String masked = "*".repeat(cardNumber.length() - 8);
        
        return prefix + masked + suffix;
    }
    
    /**
     * 개인정보 마스킹 처리
     */
    public String maskPersonalInfo(String personalInfo) {
        if (personalInfo == null || personalInfo.length() < 3) {
            return personalInfo;
        }
        
        if (personalInfo.length() <= 4) {
            return personalInfo.charAt(0) + "*".repeat(personalInfo.length() - 1);
        }
        
        // 앞 2자리와 뒤 2자리만 보이도록 마스킹
        String prefix = personalInfo.substring(0, 2);
        String suffix = personalInfo.substring(personalInfo.length() - 2);
        String masked = "*".repeat(personalInfo.length() - 4);
        
        return prefix + masked + suffix;
    }
    
    /**
     * 결제 로그용 데이터 마스킹
     */
    public String maskForLogging(String sensitiveData) {
        if (sensitiveData == null || sensitiveData.length() < 6) {
            return "***";
        }
        
        // 처음 3글자만 보이고 나머지는 마스킹
        return sensitiveData.substring(0, 3) + "***";
    }
} 