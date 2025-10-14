package com.carcare.domain.auth.service;

import com.carcare.common.exception.BusinessException;
import com.carcare.domain.auth.dto.SmsRequest;
import com.carcare.domain.auth.dto.SmsResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.security.SecureRandom;
import java.time.LocalDateTime;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;

/**
 * SMS 인증 서비스
 * 
 * 주요 기능:
 * - SMS 인증번호 발송
 * - 인증번호 검증
 * - Redis를 사용한 인증번호 임시 저장
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class SmsService {

    @Autowired(required = false)
    private final RedisTemplate<String, Object> redisTemplate;
    private final SecureRandom secureRandom = new SecureRandom();
    
    // Redis 대체용 메모리 저장소 (개발 환경용)
    private final ConcurrentHashMap<String, String> inMemoryStorage = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, LocalDateTime> expirationTimes = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, Integer> dailyCounts = new ConcurrentHashMap<>();
    
    // 인증번호 만료 시간 (5분)
    private static final long VERIFICATION_CODE_EXPIRATION = 5;
    
    // 일일 발송 제한
    private static final int DAILY_SEND_LIMIT = 10;

    /**
     * SMS 인증번호 발송
     */
    public SmsResponse.SendCode sendVerificationCode(SmsRequest.SendCode request) {
        String phoneNumber = normalizePhoneNumber(request.getPhoneNumber());
        
        // 발송 횟수 제한 확인
        checkDailySendLimit(phoneNumber);
        
        // 6자리 인증번호 생성
        String verificationCode = generateVerificationCode();
        
        // 인증번호 저장 (Redis 또는 메모리)
        String key = createRedisKey(phoneNumber);
        storeVerificationCode(key, verificationCode);
        
        // 발송 횟수 증가
        increaseDailySendCount(phoneNumber);
        
        // 실제 SMS 발송 (현재는 로그로만 처리)
        sendActualSms(phoneNumber, verificationCode);
        
        log.info("SMS 인증번호 발송 완료: {} (코드: {})", phoneNumber, verificationCode);
        
        return SmsResponse.SendCode.builder()
                .message("인증번호가 발송되었습니다")
                .phoneNumber(maskPhoneNumber(phoneNumber))
                .expirationMinutes((int) VERIFICATION_CODE_EXPIRATION)
                .sentAt(LocalDateTime.now())
                .requestId(generateRequestId())
                .build();
    }

    /**
     * SMS 인증번호 검증
     */
    public SmsResponse.VerifyCode verifyCode(SmsRequest.VerifyCode request) {
        String phoneNumber = normalizePhoneNumber(request.getPhoneNumber());
        String inputCode = request.getVerificationCode();
        
        // 저장된 인증번호 조회 (Redis 또는 메모리)
        String key = createRedisKey(phoneNumber);
        String storedCode = getStoredVerificationCode(key);
        
        if (storedCode == null) {
            throw new BusinessException("인증번호가 만료되었거나 존재하지 않습니다");
        }
        
        if (!storedCode.equals(inputCode)) {
            throw new BusinessException("인증번호가 일치하지 않습니다");
        }
        
        // 인증 성공 시 저장소에서 삭제
        deleteVerificationCode(key);
        
        // 인증 완료 표시 (30분 TTL)
        String verifiedKey = createVerifiedKey(phoneNumber);
        storeVerificationCode(verifiedKey, "verified");
        
        log.info("SMS 인증 완료: {}", phoneNumber);
        
        return SmsResponse.VerifyCode.builder()
                .message("인증이 완료되었습니다")
                .phoneNumber(maskPhoneNumber(phoneNumber))
                .verified(true)
                .verifiedAt(LocalDateTime.now())
                .build();
    }

    /**
     * 휴대폰 번호 인증 완료 여부 확인
     */
    public boolean isPhoneVerified(String phoneNumber) {
        String normalizedPhone = normalizePhoneNumber(phoneNumber);
        String verifiedKey = createVerifiedKey(normalizedPhone);
        return getStoredVerificationCode(verifiedKey) != null;
    }

    /**
     * 휴대폰 번호 정규화 (하이픈 제거)
     */
    private String normalizePhoneNumber(String phoneNumber) {
        return phoneNumber.replaceAll("-", "");
    }

    /**
     * 6자리 인증번호 생성
     */
    private String generateVerificationCode() {
        return String.format("%06d", secureRandom.nextInt(1000000));
    }

    /**
     * Redis 키 생성 (인증번호 저장용)
     */
    private String createRedisKey(String phoneNumber) {
        return "sms:verification:" + phoneNumber;
    }

    /**
     * Redis 키 생성 (인증 완료 표시용)
     */
    private String createVerifiedKey(String phoneNumber) {
        return "sms:verified:" + phoneNumber;
    }

    /**
     * 일일 발송 제한 확인
     */
    private void checkDailySendLimit(String phoneNumber) {
        String dailyLimitKey = "sms:daily:" + phoneNumber + ":" + LocalDateTime.now().toLocalDate();
        
        int currentCount = 0;
        if (redisTemplate != null) {
            try {
                String countStr = (String) redisTemplate.opsForValue().get(dailyLimitKey);
                currentCount = countStr != null ? Integer.parseInt(countStr) : 0;
            } catch (Exception e) {
                log.warn("Redis 일일 제한 확인 실패, 메모리 사용: {}", e.getMessage());
                currentCount = dailyCounts.getOrDefault(dailyLimitKey, 0);
            }
        } else {
            currentCount = dailyCounts.getOrDefault(dailyLimitKey, 0);
        }
        
        if (currentCount >= DAILY_SEND_LIMIT) {
            throw new BusinessException("일일 SMS 발송 제한을 초과했습니다. 내일 다시 시도해주세요.");
        }
    }

    /**
     * 일일 발송 횟수 증가
     */
    private void increaseDailySendCount(String phoneNumber) {
        String dailyLimitKey = "sms:daily:" + phoneNumber + ":" + LocalDateTime.now().toLocalDate();
        
        if (redisTemplate != null) {
            try {
                redisTemplate.opsForValue().increment(dailyLimitKey);
                redisTemplate.expire(dailyLimitKey, 24, TimeUnit.HOURS);
            } catch (Exception e) {
                log.warn("Redis 일일 횟수 증가 실패, 메모리 사용: {}", e.getMessage());
                dailyCounts.put(dailyLimitKey, dailyCounts.getOrDefault(dailyLimitKey, 0) + 1);
            }
        } else {
            dailyCounts.put(dailyLimitKey, dailyCounts.getOrDefault(dailyLimitKey, 0) + 1);
        }
    }

    /**
     * 실제 SMS 발송 (현재는 로그만 출력)
     * 실제 구현 시 네이버 클라우드 플랫폼 등 SMS 서비스 API 연동
     */
    private void sendActualSms(String phoneNumber, String verificationCode) {
        // TODO: 실제 SMS 발송 API 연동
        log.info("=== SMS 발송 시뮬레이션 ===");
        log.info("수신번호: {}", phoneNumber);
        log.info("인증번호: {}", verificationCode);
        log.info("내용: [CarCenter] 인증번호는 {}입니다. 5분 내에 입력해주세요.", verificationCode);
        log.info("========================");
    }

    /**
     * 휴대폰 번호 마스킹 (010-1234-5678 -> 010-****-5678)
     */
    private String maskPhoneNumber(String phoneNumber) {
        if (phoneNumber.length() == 11) {
            return phoneNumber.substring(0, 3) + "-****-" + phoneNumber.substring(7);
        }
        return phoneNumber;
    }

    /**
     * 요청 ID 생성 (추적용)
     */
    private String generateRequestId() {
        return "SMS" + System.currentTimeMillis() + secureRandom.nextInt(1000);
    }

    /**
     * 인증번호 저장 (Redis 또는 메모리)
     */
    private void storeVerificationCode(String key, String code) {
        if (redisTemplate != null) {
            try {
                redisTemplate.opsForValue().set(key, code, VERIFICATION_CODE_EXPIRATION, TimeUnit.MINUTES);
            } catch (Exception e) {
                log.warn("Redis 저장 실패, 메모리 저장소 사용: {}", e.getMessage());
                storeInMemory(key, code);
            }
        } else {
            storeInMemory(key, code);
        }
    }

    /**
     * 인증번호 조회 (Redis 또는 메모리)
     */
    private String getStoredVerificationCode(String key) {
        if (redisTemplate != null) {
            try {
                return (String) redisTemplate.opsForValue().get(key);
            } catch (Exception e) {
                log.warn("Redis 조회 실패, 메모리 저장소 사용: {}", e.getMessage());
                return getFromMemory(key);
            }
        } else {
            return getFromMemory(key);
        }
    }

    /**
     * 인증번호 삭제 (Redis 또는 메모리)
     */
    private void deleteVerificationCode(String key) {
        if (redisTemplate != null) {
            try {
                redisTemplate.delete(key);
            } catch (Exception e) {
                log.warn("Redis 삭제 실패, 메모리 저장소 사용: {}", e.getMessage());
                deleteFromMemory(key);
            }
        } else {
            deleteFromMemory(key);
        }
    }

    /**
     * 메모리에 인증번호 저장
     */
    private void storeInMemory(String key, String code) {
        inMemoryStorage.put(key, code);
        expirationTimes.put(key, LocalDateTime.now().plusMinutes(VERIFICATION_CODE_EXPIRATION));
        log.info("메모리 저장소에 인증번호 저장: {}", key);
    }

    /**
     * 메모리에서 인증번호 조회
     */
    private String getFromMemory(String key) {
        // 만료 시간 체크
        LocalDateTime expiration = expirationTimes.get(key);
        if (expiration != null && LocalDateTime.now().isAfter(expiration)) {
            deleteFromMemory(key);
            return null;
        }
        return inMemoryStorage.get(key);
    }

    /**
     * 메모리에서 인증번호 삭제
     */
    private void deleteFromMemory(String key) {
        inMemoryStorage.remove(key);
        expirationTimes.remove(key);
    }
} 