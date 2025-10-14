package com.carcare.domain.service.service;

import com.carcare.domain.service.entity.ServiceCenterVerification;
import com.carcare.common.exception.BusinessException;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Value;

import java.time.LocalDateTime;
import java.util.regex.Pattern;
import java.util.Set;
import java.util.HashSet;
import java.util.Map;
import java.util.HashMap;

/**
 * 사업자등록번호 유효성 검증 서비스
 * 형식 검증, 체크섬 검증, 국세청 API 연동 등을 담당
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class BusinessNumberValidationService {

    @Value("${app.nts.api.enabled:false}")
    private boolean ntsApiEnabled;

    @Value("${app.nts.api.timeout:5000}")
    private int ntsApiTimeout;

    // 사업자등록번호 형식 패턴
    private static final Pattern BUSINESS_NUMBER_PATTERN = Pattern.compile("^\\d{3}-\\d{2}-\\d{5}$");
    private static final Pattern BUSINESS_NUMBER_DIGITS_PATTERN = Pattern.compile("^\\d{10}$");

    // 테스트용 블랙리스트 (실제 환경에서는 데이터베이스 또는 외부 API 사용)
    private static final Set<String> BLACKLISTED_BUSINESS_NUMBERS = new HashSet<String>() {{
        add("000-00-00000");
        add("111-11-11111");
        add("999-99-99999");
    }};

    /**
     * 사업자등록번호 종합 검증
     */
    public BusinessNumberValidationResult validateBusinessNumber(String businessNumber) {
        log.info("사업자등록번호 종합 검증 시작: {}", maskBusinessNumber(businessNumber));

        try {
            // 1. 형식 검증
            FormatValidationResult formatResult = validateFormat(businessNumber);
            if (!formatResult.isValid()) {
                return BusinessNumberValidationResult.builder()
                    .businessNumber(businessNumber)
                    .isValid(false)
                    .formatValid(false)
                    .checksumValid(false)
                    .ntsStatus(ServiceCenterVerification.NtsVerificationStatus.NOT_VERIFIED)
                    .errorMessage(formatResult.getErrorMessage())
                    .validatedAt(LocalDateTime.now())
                    .build();
            }

            String cleanedNumber = cleanBusinessNumber(businessNumber);

            // 2. 체크섬 검증
            boolean checksumValid = validateChecksum(cleanedNumber);
            if (!checksumValid) {
                return BusinessNumberValidationResult.builder()
                    .businessNumber(businessNumber)
                    .isValid(false)
                    .formatValid(true)
                    .checksumValid(false)
                    .ntsStatus(ServiceCenterVerification.NtsVerificationStatus.NOT_VERIFIED)
                    .errorMessage("사업자등록번호 체크섬이 올바르지 않습니다")
                    .validatedAt(LocalDateTime.now())
                    .build();
            }

            // 3. 블랙리스트 확인
            if (isBlacklisted(businessNumber)) {
                return BusinessNumberValidationResult.builder()
                    .businessNumber(businessNumber)
                    .isValid(false)
                    .formatValid(true)
                    .checksumValid(true)
                    .ntsStatus(ServiceCenterVerification.NtsVerificationStatus.INVALID)
                    .errorMessage("사용할 수 없는 사업자등록번호입니다")
                    .validatedAt(LocalDateTime.now())
                    .build();
            }

            // 4. 국세청 API 검증 (실제 환경에서는 외부 API 호출)
            NtsApiResponse ntsResponse = queryNtsApi(cleanedNumber);

            return BusinessNumberValidationResult.builder()
                .businessNumber(businessNumber)
                .isValid(ntsResponse.getStatus().isValid())
                .formatValid(true)
                .checksumValid(true)
                .ntsStatus(ntsResponse.getStatus())
                .ntsResponseCode(ntsResponse.getResponseCode())
                .ntsResponseMessage(ntsResponse.getResponseMessage())
                .businessInfo(ntsResponse.getBusinessInfo())
                .errorMessage(ntsResponse.getStatus().isValid() ? null : ntsResponse.getResponseMessage())
                .validatedAt(LocalDateTime.now())
                .build();

        } catch (Exception e) {
            log.error("사업자등록번호 검증 중 오류 발생: {}, 오류={}", maskBusinessNumber(businessNumber), e.getMessage(), e);
            return BusinessNumberValidationResult.builder()
                .businessNumber(businessNumber)
                .isValid(false)
                .formatValid(false)
                .checksumValid(false)
                .ntsStatus(ServiceCenterVerification.NtsVerificationStatus.ERROR)
                .errorMessage("검증 중 오류가 발생했습니다: " + e.getMessage())
                .validatedAt(LocalDateTime.now())
                .build();
        }
    }

    /**
     * 사업자등록번호 형식 검증
     */
    public FormatValidationResult validateFormat(String businessNumber) {
        if (businessNumber == null || businessNumber.trim().isEmpty()) {
            return FormatValidationResult.builder()
                .isValid(false)
                .errorMessage("사업자등록번호를 입력해주세요")
                .build();
        }

        String trimmed = businessNumber.trim();

        // 하이픈 포함 형식 확인
        if (BUSINESS_NUMBER_PATTERN.matcher(trimmed).matches()) {
            return FormatValidationResult.builder()
                .isValid(true)
                .cleanedNumber(cleanBusinessNumber(trimmed))
                .build();
        }

        // 숫자만 형식 확인
        String digitsOnly = trimmed.replaceAll("-", "");
        if (BUSINESS_NUMBER_DIGITS_PATTERN.matcher(digitsOnly).matches()) {
            return FormatValidationResult.builder()
                .isValid(true)
                .cleanedNumber(digitsOnly)
                .build();
        }

        return FormatValidationResult.builder()
            .isValid(false)
            .errorMessage("사업자등록번호 형식이 올바르지 않습니다. (예: 123-45-67890 또는 1234567890)")
            .build();
    }

    /**
     * 사업자등록번호 체크섬 검증
     * 한국 사업자등록번호 검증 알고리즘 사용
     */
    public boolean validateChecksum(String businessNumber) {
        if (businessNumber == null || businessNumber.length() != 10) {
            return false;
        }

        try {
            int[] digits = businessNumber.chars()
                .map(c -> Character.getNumericValue(c))
                .toArray();

            // 체크섬 계산
            int[] multipliers = {1, 3, 7, 1, 3, 7, 1, 3, 5};
            int sum = 0;

            for (int i = 0; i < 9; i++) {
                sum += digits[i] * multipliers[i];
            }

            // 9번째 자리수에 5를 곱한 결과의 1의 자리만 더함
            sum += (digits[8] * 5) / 10;

            // 체크 디지트 계산
            int checkDigit = (10 - (sum % 10)) % 10;

            return checkDigit == digits[9];

        } catch (Exception e) {
            log.warn("사업자등록번호 체크섬 검증 중 오류: {}", e.getMessage());
            return false;
        }
    }

    /**
     * 국세청 API 조회 (시뮬레이션)
     * 실제 환경에서는 국세청 API를 호출
     */
    private NtsApiResponse queryNtsApi(String businessNumber) {
        log.info("국세청 API 조회 시작: {}", maskBusinessNumber(businessNumber));

        if (!ntsApiEnabled) {
            log.info("국세청 API가 비활성화되어 시뮬레이션 모드로 동작");
            return simulateNtsApiResponse(businessNumber);
        }

        try {
            // TODO: 실제 국세청 API 호출 구현
            // 현재는 시뮬레이션으로 대체
            Thread.sleep(100); // API 호출 시뮬레이션
            return simulateNtsApiResponse(businessNumber);

        } catch (Exception e) {
            log.error("국세청 API 호출 중 오류 발생: {}", e.getMessage(), e);
            return NtsApiResponse.builder()
                .status(ServiceCenterVerification.NtsVerificationStatus.ERROR)
                .responseCode("API_ERROR")
                .responseMessage("국세청 API 호출 중 오류가 발생했습니다")
                .build();
        }
    }

    /**
     * 국세청 API 응답 시뮬레이션
     */
    private NtsApiResponse simulateNtsApiResponse(String businessNumber) {
        // 특정 패턴에 따른 시뮬레이션 응답
        String lastTwoDigits = businessNumber.substring(8);

        switch (lastTwoDigits) {
            case "00":
                return NtsApiResponse.builder()
                    .status(ServiceCenterVerification.NtsVerificationStatus.CLOSED)
                    .responseCode("02")
                    .responseMessage("폐업자")
                    .build();

            case "99":
                return NtsApiResponse.builder()
                    .status(ServiceCenterVerification.NtsVerificationStatus.INVALID)
                    .responseCode("01")
                    .responseMessage("등록되지 않은 사업자등록번호")
                    .build();

            case "88":
                return NtsApiResponse.builder()
                    .status(ServiceCenterVerification.NtsVerificationStatus.SUSPENDED)
                    .responseCode("03")
                    .responseMessage("사업자 정지")
                    .build();

            default:
                return NtsApiResponse.builder()
                    .status(ServiceCenterVerification.NtsVerificationStatus.VERIFIED)
                    .responseCode("00")
                    .responseMessage("정상")
                    .businessInfo(createSimulatedBusinessInfo(businessNumber))
                    .build();
        }
    }

    /**
     * 시뮬레이션용 사업자 정보 생성
     */
    private BusinessInfo createSimulatedBusinessInfo(String businessNumber) {
        return BusinessInfo.builder()
            .businessNumber(businessNumber)
            .businessName("시뮬레이션 정비소 " + businessNumber.substring(6))
            .representativeName("홍길동")
            .businessAddress("서울특별시 강남구 테헤란로 123")
            .businessType("자동차 정비업")
            .establishmentDate("20200101")
            .businessStatus("정상")
            .build();
    }

    /**
     * 블랙리스트 확인
     */
    private boolean isBlacklisted(String businessNumber) {
        return BLACKLISTED_BUSINESS_NUMBERS.contains(businessNumber);
    }

    /**
     * 사업자등록번호 정제 (하이픈 제거)
     */
    private String cleanBusinessNumber(String businessNumber) {
        return businessNumber.replaceAll("-", "");
    }

    /**
     * 사업자등록번호 마스킹 (로그용)
     */
    private String maskBusinessNumber(String businessNumber) {
        if (businessNumber == null || businessNumber.length() < 4) {
            return "***";
        }
        return businessNumber.substring(0, 3) + "-**-****" + businessNumber.substring(businessNumber.length() - 1);
    }

    // === 결과 클래스들 ===

    @lombok.Data
    @lombok.Builder
    public static class BusinessNumberValidationResult {
        private String businessNumber;
        private boolean isValid;
        private boolean formatValid;
        private boolean checksumValid;
        private ServiceCenterVerification.NtsVerificationStatus ntsStatus;
        private String ntsResponseCode;
        private String ntsResponseMessage;
        private BusinessInfo businessInfo;
        private String errorMessage;
        private LocalDateTime validatedAt;

        /**
         * 검증 완료 여부 확인
         */
        public boolean isFullyValidated() {
            return formatValid && checksumValid && ntsStatus != ServiceCenterVerification.NtsVerificationStatus.NOT_VERIFIED;
        }

        /**
         * 국세청 검증 성공 여부
         */
        public boolean isNtsValid() {
            return ntsStatus == ServiceCenterVerification.NtsVerificationStatus.VERIFIED;
        }
    }

    @lombok.Data
    @lombok.Builder
    public static class FormatValidationResult {
        private boolean isValid;
        private String cleanedNumber;
        private String errorMessage;
    }

    @lombok.Data
    @lombok.Builder
    public static class NtsApiResponse {
        private ServiceCenterVerification.NtsVerificationStatus status;
        private String responseCode;
        private String responseMessage;
        private BusinessInfo businessInfo;
    }

    @lombok.Data
    @lombok.Builder
    public static class BusinessInfo {
        private String businessNumber;
        private String businessName;
        private String representativeName;
        private String businessAddress;
        private String businessType;
        private String establishmentDate;
        private String businessStatus;
    }
} 