package com.carcare.domain.service.entity;

import lombok.Data;
import lombok.Builder;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

import jakarta.validation.constraints.*;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.LocalDateTime;
import java.math.BigDecimal;

/**
 * 정비소 엔티티
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ServiceCenter {
    
    private Long id;
    
    @NotBlank(message = "정비소명은 필수입니다")
    @Size(max = 100, message = "정비소명은 100자 이하여야 합니다")
    private String name;
    
    @Size(max = 500, message = "설명은 500자 이하여야 합니다")
    private String description;
    
    @NotBlank(message = "주소는 필수입니다")
    @Size(max = 200, message = "주소는 200자 이하여야 합니다")
    private String address;
    
    @Size(max = 100, message = "상세주소는 100자 이하여야 합니다")
    private String addressDetail;
    
    @NotBlank(message = "전화번호는 필수입니다")
    @Pattern(regexp = "^\\d{2,3}-\\d{3,4}-\\d{4}$", message = "올바른 전화번호 형식이 아닙니다")
    private String phoneNumber;
    
    @Email(message = "올바른 이메일 형식이 아닙니다")
    @Size(max = 100, message = "이메일은 100자 이하여야 합니다")
    private String email;
    
    @Size(max = 255, message = "웹사이트 URL은 255자 이하여야 합니다")
    private String website;
    
    // 사업자 정보
    @NotBlank(message = "사업자 등록번호는 필수입니다")
    @Pattern(regexp = "^\\d{3}-\\d{2}-\\d{5}$", message = "올바른 사업자 등록번호 형식이 아닙니다")
    private String businessNumber;
    
    @NotBlank(message = "대표자명은 필수입니다")
    @Size(max = 50, message = "대표자명은 50자 이하여야 합니다")
    private String ownerName;
    
    // 위치 정보
    @NotNull(message = "위도는 필수입니다")
    @DecimalMin(value = "33.0", message = "유효한 위도 범위가 아닙니다")
    @DecimalMax(value = "39.0", message = "유효한 위도 범위가 아닙니다")
    private BigDecimal latitude;
    
    @NotNull(message = "경도는 필수입니다")
    @DecimalMin(value = "124.0", message = "유효한 경도 범위가 아닙니다")
    @DecimalMax(value = "132.0", message = "유효한 경도 범위가 아닙니다")
    private BigDecimal longitude;
    
    // 평점 정보
    @DecimalMin(value = "0.0", message = "평점은 0.0 이상이어야 합니다")
    @DecimalMax(value = "5.0", message = "평점은 5.0 이하여야 합니다")
    private BigDecimal averageRating;
    
    @Min(value = 0, message = "리뷰 수는 0 이상이어야 합니다")
    private Integer reviewCount;
    
    // 인증 상태
    private VerificationStatus verificationStatus;
    
    private LocalDateTime verificationDate;
    
    // 상태 정보
    private Boolean isActive;
    
    private Boolean isOperating; // 현재 운영 중 여부
    
    // 서비스 정보
    @Size(max = 1000, message = "특화서비스는 1000자 이하여야 합니다")
    private String specializedServices;
    
    @Size(max = 1000, message = "시설정보는 1000자 이하여야 합니다")
    private String facilities;
    
    // 기타 정보
    @Size(max = 1000, message = "특이사항은 1000자 이하여야 합니다")
    private String specialNotes;
    
    @Size(max = 255, message = "이미지 URL은 255자 이하여야 합니다")
    private String imageUrl;
    
    // 편의 메서드
    // 추가 getter: 인증 상태 여부
    public Boolean getIsVerified() {
        return verificationStatus != null && verificationStatus.isApproved();
    }
    
    // 생성/수정 정보
    private LocalDateTime createdAt;
    
    private LocalDateTime updatedAt;
    
    private Long createdBy; // 등록한 사용자 ID
    
    private Long updatedBy; // 수정한 사용자 ID
    
    /**
     * 정비소 인증 상태 열거형
     */
    public enum VerificationStatus {
        @JsonProperty("PENDING")
        PENDING("대기중"),
        
        @JsonProperty("IN_REVIEW")
        IN_REVIEW("검토중"),
        
        @JsonProperty("APPROVED")
        APPROVED("승인완료"),
        
        @JsonProperty("VERIFIED")
        VERIFIED("인증완료"),
        
        @JsonProperty("REJECTED")
        REJECTED("인증거부"),
        
        @JsonProperty("EXPIRED")
        EXPIRED("인증만료");
        
        private final String description;
        
        VerificationStatus(String description) {
            this.description = description;
        }
        
        public String getDescription() {
            return description;
        }
        
        /**
         * 승인된 상태인지 확인 (APPROVED 또는 VERIFIED)
         */
        public boolean isApproved() {
            return this == APPROVED || this == VERIFIED;
        }
    }
} 