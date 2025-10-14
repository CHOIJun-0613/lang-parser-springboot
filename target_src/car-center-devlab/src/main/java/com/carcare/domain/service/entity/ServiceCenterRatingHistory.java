package com.carcare.domain.service.entity;

import lombok.Data;
import lombok.Builder;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

import jakarta.validation.constraints.*;
import java.time.LocalDateTime;
import java.math.BigDecimal;

/**
 * 정비소 평점 히스토리 엔티티
 * 평점 변경 이력을 추적하고 분석하기 위한 엔티티
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ServiceCenterRatingHistory {
    
    private Long id;
    
    @NotNull(message = "정비소 ID는 필수입니다")
    private Long serviceCenterId;
    
    // 평점 정보
    @NotNull(message = "이전 평점은 필수입니다")
    @DecimalMin(value = "0.0", message = "평점은 0.0 이상이어야 합니다")
    @DecimalMax(value = "5.0", message = "평점은 5.0 이하여야 합니다")
    private BigDecimal previousRating;
    
    @NotNull(message = "현재 평점은 필수입니다")
    @DecimalMin(value = "0.0", message = "평점은 0.0 이상이어야 합니다")
    @DecimalMax(value = "5.0", message = "평점은 5.0 이하여야 합니다")
    private BigDecimal currentRating;
    
    @NotNull(message = "평점 변화량은 필수입니다")
    private BigDecimal ratingChange; // currentRating - previousRating
    
    // 리뷰 수 정보
    @NotNull(message = "이전 리뷰 수는 필수입니다")
    @Min(value = 0, message = "리뷰 수는 0 이상이어야 합니다")
    private Integer previousReviewCount;
    
    @NotNull(message = "현재 리뷰 수는 필수입니다")
    @Min(value = 0, message = "리뷰 수는 0 이상이어야 합니다")
    private Integer currentReviewCount;
    
    @NotNull(message = "리뷰 수 변화량은 필수입니다")
    private Integer reviewCountChange; // currentReviewCount - previousReviewCount
    
    // 변경 원인 정보
    @NotNull(message = "변경 타입은 필수입니다")
    private ChangeType changeType;
    
    private Long relatedReviewId; // 변경을 유발한 리뷰 ID (있는 경우)
    
    @NotNull(message = "변경 사유는 필수입니다")
    @Size(max = 500, message = "변경 사유는 500자 이하여야 합니다")
    private String changeReason;
    
    // 계산 방식 정보
    @NotNull(message = "계산 방법은 필수입니다")
    private CalculationMethod calculationMethod;
    
    @Size(max = 1000, message = "계산 세부사항은 1000자 이하여야 합니다")
    private String calculationDetails; // JSON 형태로 계산 세부사항 저장
    
    // 신뢰성 지표
    @DecimalMin(value = "0.0", message = "신뢰성 점수는 0.0 이상이어야 합니다")
    @DecimalMax(value = "1.0", message = "신뢰성 점수는 1.0 이하여야 합니다")
    private BigDecimal reliabilityScore; // 평점의 신뢰성 점수 (0.0 ~ 1.0)
    
    // 메타데이터
    private LocalDateTime createdAt;
    private Long createdBy; // 시스템 또는 관리자 ID
    
    /**
     * 평점 변경 타입
     */
    public enum ChangeType {
        REVIEW_ADDED("리뷰 추가"),
        REVIEW_UPDATED("리뷰 수정"),
        REVIEW_DELETED("리뷰 삭제"),
        MANUAL_ADJUSTMENT("수동 조정"),
        SYSTEM_RECALCULATION("시스템 재계산"),
        DATA_MIGRATION("데이터 마이그레이션"),
        BULK_UPDATE("일괄 업데이트");
        
        private final String description;
        
        ChangeType(String description) {
            this.description = description;
        }
        
        public String getDescription() {
            return description;
        }
    }
    
    /**
     * 평점 계산 방법
     */
    public enum CalculationMethod {
        SIMPLE_AVERAGE("단순 평균"),
        WEIGHTED_AVERAGE("가중 평균"),
        BAYESIAN_AVERAGE("베이지안 평균"),
        WILSON_SCORE("윌슨 점수"),
        CUSTOM_ALGORITHM("커스텀 알고리즘");
        
        private final String description;
        
        CalculationMethod(String description) {
            this.description = description;
        }
        
        public String getDescription() {
            return description;
        }
    }
    
    /**
     * 평점 변화 정도 계산
     */
    public RatingChangeLevel getChangeLevel() {
        BigDecimal absChange = ratingChange.abs();
        
        if (absChange.compareTo(new BigDecimal("0.01")) < 0) {
            return RatingChangeLevel.MINIMAL;
        } else if (absChange.compareTo(new BigDecimal("0.1")) < 0) {
            return RatingChangeLevel.SMALL;
        } else if (absChange.compareTo(new BigDecimal("0.3")) < 0) {
            return RatingChangeLevel.MODERATE;
        } else if (absChange.compareTo(new BigDecimal("0.5")) < 0) {
            return RatingChangeLevel.SIGNIFICANT;
        } else {
            return RatingChangeLevel.MAJOR;
        }
    }
    
    /**
     * 평점 변화 정도 열거형
     */
    public enum RatingChangeLevel {
        MINIMAL("미미한 변화"),
        SMALL("작은 변화"),
        MODERATE("보통 변화"),
        SIGNIFICANT("큰 변화"),
        MAJOR("주요 변화");
        
        private final String description;
        
        RatingChangeLevel(String description) {
            this.description = description;
        }
        
        public String getDescription() {
            return description;
        }
    }
    
    /**
     * 평점 변화가 개선인지 악화인지 판단
     */
    public boolean isImprovement() {
        return ratingChange.compareTo(BigDecimal.ZERO) > 0;
    }
    
    /**
     * 평점 변화가 악화인지 판단
     */
    public boolean isDegradation() {
        return ratingChange.compareTo(BigDecimal.ZERO) < 0;
    }
} 