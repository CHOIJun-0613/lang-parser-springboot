package com.carcare.domain.service.entity;

import lombok.Data;
import lombok.Builder;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

import jakarta.validation.constraints.*;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.LocalDateTime;
import java.time.LocalDate;

/**
 * 정비소 사업자 인증 엔티티
 * 사업자등록번호 검증, 인증 상태 관리, 문서 업로드 등을 관리
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ServiceCenterVerification {
    
    private Long id;
    
    @NotNull(message = "정비소 ID는 필수입니다")
    private Long serviceCenterId;
    
    // 사업자 정보
    @NotBlank(message = "사업자등록번호는 필수입니다")
    @Pattern(regexp = "^\\d{3}-\\d{2}-\\d{5}$", message = "사업자등록번호 형식이 올바르지 않습니다 (예: 123-45-67890)")
    private String businessNumber;
    
    @NotBlank(message = "대표자명은 필수입니다")
    @Size(max = 50, message = "대표자명은 50자 이하여야 합니다")
    private String representativeName;
    
    @NotBlank(message = "상호명은 필수입니다")
    @Size(max = 100, message = "상호명은 100자 이하여야 합니다")
    private String businessName;
    
    @NotBlank(message = "사업장 주소는 필수입니다")
    @Size(max = 200, message = "사업장 주소는 200자 이하여야 합니다")
    private String businessAddress;
    
    @NotNull(message = "개업일자는 필수입니다")
    private LocalDate establishmentDate;
    
    @Size(max = 100, message = "업종은 100자 이하여야 합니다")
    private String businessType;
    
    // 인증 상태
    @NotNull(message = "인증 상태는 필수입니다")
    private VerificationStatus status;
    
    private LocalDateTime statusUpdatedAt; // 상태 변경 일시
    
    // 국세청 검증 정보
    private NtsVerificationStatus ntsStatus; // 국세청 조회 상태
    private String ntsResponseCode; // 국세청 응답 코드
    private String ntsResponseMessage; // 국세청 응답 메시지
    private LocalDateTime ntsVerifiedAt; // 국세청 검증 일시
    
    // 문서 정보
    @Size(max = 255, message = "사업자등록증 파일 경로는 255자 이하여야 합니다")
    private String businessLicenseFilePath; // 사업자등록증 파일 경로
    
    @Size(max = 255, message = "추가 문서 파일 경로는 255자 이하여야 합니다")
    private String additionalDocumentPath; // 추가 증빙 문서
    
    // 승인/거부 정보
    private Long approvedBy; // 승인자 ID
    private LocalDateTime approvedAt; // 승인 일시
    private LocalDateTime rejectedAt; // 거부 일시
    
    @Size(max = 500, message = "거부 사유는 500자 이하여야 합니다")
    private String rejectionReason; // 거부 사유
    
    // 인증 유효성
    private LocalDate verificationExpiryDate; // 인증 만료일
    private Boolean isActive; // 활성 상태
    
    // 재검증 정보
    private Integer verificationAttempts; // 검증 시도 횟수
    private LocalDateTime lastVerificationAttemptAt; // 마지막 검증 시도 일시
    private LocalDateTime nextAllowedVerificationAt; // 다음 검증 허용 일시
    
    // 메타데이터
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    private Long createdBy;
    private Long updatedBy;
    
    /**
     * 인증 상태 열거형
     */
    public enum VerificationStatus {
        @JsonProperty("PENDING")
        PENDING("인증 대기"),
        
        @JsonProperty("DOCUMENT_REQUIRED")
        DOCUMENT_REQUIRED("서류 제출 필요"),
        
        @JsonProperty("IN_REVIEW")
        IN_REVIEW("검토 중"),
        
        @JsonProperty("NTS_VERIFICATION")
        NTS_VERIFICATION("국세청 조회 중"),
        
        @JsonProperty("ADMIN_REVIEW")
        ADMIN_REVIEW("관리자 승인 대기"),
        
        @JsonProperty("VERIFIED")
        VERIFIED("인증 완료"),
        
        @JsonProperty("REJECTED")
        REJECTED("인증 거부"),
        
        @JsonProperty("EXPIRED")
        EXPIRED("인증 만료"),
        
        @JsonProperty("SUSPENDED")
        SUSPENDED("인증 정지"),
        
        @JsonProperty("CANCELLED")
        CANCELLED("인증 취소");
        
        private final String description;
        
        VerificationStatus(String description) {
            this.description = description;
        }
        
        public String getDescription() {
            return description;
        }
        
        /**
         * 완료된 인증 상태인지 확인
         */
        public boolean isCompleted() {
            return this == VERIFIED;
        }
        
        /**
         * 진행 중인 상태인지 확인
         */
        public boolean isInProgress() {
            return this == PENDING || this == DOCUMENT_REQUIRED || 
                   this == IN_REVIEW || this == NTS_VERIFICATION || 
                   this == ADMIN_REVIEW;
        }
        
        /**
         * 실패 상태인지 확인
         */
        public boolean isFailed() {
            return this == REJECTED || this == EXPIRED || 
                   this == SUSPENDED || this == CANCELLED;
        }
    }
    
    /**
     * 국세청 검증 상태 열거형
     */
    public enum NtsVerificationStatus {
        @JsonProperty("NOT_VERIFIED")
        NOT_VERIFIED("미검증"),
        
        @JsonProperty("VERIFIED")
        VERIFIED("검증 완료"),
        
        @JsonProperty("INVALID")
        INVALID("유효하지 않은 사업자번호"),
        
        @JsonProperty("CLOSED")
        CLOSED("폐업"),
        
        @JsonProperty("SUSPENDED")
        SUSPENDED("사업자 정지"),
        
        @JsonProperty("ERROR")
        ERROR("조회 오류"),
        
        @JsonProperty("TIMEOUT")
        TIMEOUT("조회 시간 초과");
        
        private final String description;
        
        NtsVerificationStatus(String description) {
            this.description = description;
        }
        
        public String getDescription() {
            return description;
        }
        
        /**
         * 유효한 사업자인지 확인
         */
        public boolean isValid() {
            return this == VERIFIED;
        }
    }
    
    /**
     * 인증 완료 여부 확인
     */
    public boolean isVerified() {
        return status == VerificationStatus.VERIFIED && isActive == Boolean.TRUE;
    }
    
    /**
     * 인증 만료 여부 확인
     */
    public boolean isExpired() {
        return verificationExpiryDate != null && 
               verificationExpiryDate.isBefore(LocalDate.now());
    }
    
    /**
     * 재검증 가능 여부 확인
     */
    public boolean canReVerify() {
        return nextAllowedVerificationAt == null || 
               nextAllowedVerificationAt.isBefore(LocalDateTime.now());
    }
    
    /**
     * 문서 업로드 완료 여부 확인
     */
    public boolean hasRequiredDocuments() {
        return businessLicenseFilePath != null && !businessLicenseFilePath.trim().isEmpty();
    }
    
    /**
     * 국세청 검증 완료 여부 확인
     */
    public boolean isNtsVerified() {
        return ntsStatus != null && ntsStatus.isValid();
    }
    
    /**
     * 관리자 승인 필요 여부 확인
     */
    public boolean needsAdminApproval() {
        return status == VerificationStatus.ADMIN_REVIEW;
    }
    
    /**
     * 인증 가능 여부 종합 확인
     */
    public boolean canBeVerified() {
        return hasRequiredDocuments() && isNtsVerified() && canReVerify();
    }
    
    /**
     * 다음 인증 상태 제안
     */
    public VerificationStatus getNextRecommendedStatus() {
        switch (status) {
            case PENDING:
                return hasRequiredDocuments() ? VerificationStatus.IN_REVIEW : VerificationStatus.DOCUMENT_REQUIRED;
            case DOCUMENT_REQUIRED:
                return hasRequiredDocuments() ? VerificationStatus.IN_REVIEW : VerificationStatus.DOCUMENT_REQUIRED;
            case IN_REVIEW:
                return VerificationStatus.NTS_VERIFICATION;
            case NTS_VERIFICATION:
                return isNtsVerified() ? VerificationStatus.ADMIN_REVIEW : VerificationStatus.REJECTED;
            case ADMIN_REVIEW:
                return VerificationStatus.VERIFIED; // 관리자 판단 필요
            default:
                return status; // 현재 상태 유지
        }
    }
    
    /**
     * 인증까지 남은 단계 수 계산
     */
    public int getRemainingSteps() {
        switch (status) {
            case PENDING:
            case DOCUMENT_REQUIRED:
                return hasRequiredDocuments() ? 3 : 4; // 서류 검토 -> 국세청 -> 관리자 -> 완료
            case IN_REVIEW:
                return 3; // 국세청 -> 관리자 -> 완료
            case NTS_VERIFICATION:
                return 2; // 관리자 -> 완료
            case ADMIN_REVIEW:
                return 1; // 완료
            case VERIFIED:
                return 0; // 완료됨
            default:
                return -1; // 실패 상태
        }
    }
    
    /**
     * 인증 진행률 계산 (0-100%)
     */
    public int getVerificationProgress() {
        int totalSteps = 4; // 서류 -> 검토 -> 국세청 -> 관리자 -> 완료
        int remainingSteps = getRemainingSteps();
        
        if (remainingSteps < 0) return 0; // 실패 상태
        if (remainingSteps == 0) return 100; // 완료 상태
        
        return Math.max(0, (totalSteps - remainingSteps) * 100 / totalSteps);
    }
} 