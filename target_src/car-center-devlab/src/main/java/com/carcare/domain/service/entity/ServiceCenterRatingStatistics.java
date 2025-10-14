package com.carcare.domain.service.entity;

import lombok.Data;
import lombok.Builder;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

import jakarta.validation.constraints.*;
import java.time.LocalDateTime;
import java.math.BigDecimal;

/**
 * 정비소 평점 통계 엔티티
 * 평점 분포, 트렌드, 신뢰성 등의 상세 통계 정보를 관리
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ServiceCenterRatingStatistics {
    
    private Long id;
    
    @NotNull(message = "정비소 ID는 필수입니다")
    private Long serviceCenterId;
    
    // 기본 평점 정보
    @NotNull(message = "현재 평점은 필수입니다")
    @DecimalMin(value = "0.0", message = "평점은 0.0 이상이어야 합니다")
    @DecimalMax(value = "5.0", message = "평점은 5.0 이하여야 합니다")
    private BigDecimal currentRating;
    
    @NotNull(message = "총 리뷰 수는 필수입니다")
    @Min(value = 0, message = "리뷰 수는 0 이상이어야 합니다")
    private Integer totalReviewCount;
    
    // 평점 분포 (1~5점 각각의 개수)
    @Min(value = 0, message = "1점 리뷰 수는 0 이상이어야 합니다")
    private Integer rating1Count;
    
    @Min(value = 0, message = "2점 리뷰 수는 0 이상이어야 합니다")
    private Integer rating2Count;
    
    @Min(value = 0, message = "3점 리뷰 수는 0 이상이어야 합니다")
    private Integer rating3Count;
    
    @Min(value = 0, message = "4점 리뷰 수는 0 이상이어야 합니다")
    private Integer rating4Count;
    
    @Min(value = 0, message = "5점 리뷰 수는 0 이상이어야 합니다")
    private Integer rating5Count;
    
    // 통계 지표
    @DecimalMin(value = "0.0", message = "평점 분산은 0.0 이상이어야 합니다")
    private BigDecimal ratingVariance; // 평점의 분산
    
    @DecimalMin(value = "0.0", message = "평점 표준편차는 0.0 이상이어야 합니다")
    private BigDecimal ratingStandardDeviation; // 평점의 표준편차
    
    @DecimalMin(value = "0.0", message = "신뢰성 점수는 0.0 이상이어야 합니다")
    @DecimalMax(value = "1.0", message = "신뢰성 점수는 1.0 이하여야 합니다")
    private BigDecimal reliabilityScore; // 평점의 신뢰성 점수
    
    // 트렌드 분석 (최근 30일)
    @DecimalMin(value = "0.0", message = "최근 평점은 0.0 이상이어야 합니다")
    @DecimalMax(value = "5.0", message = "최근 평점은 5.0 이하여야 합니다")
    private BigDecimal recentRating; // 최근 30일 평점
    
    @Min(value = 0, message = "최근 리뷰 수는 0 이상이어야 합니다")
    private Integer recentReviewCount; // 최근 30일 리뷰 수
    
    private BigDecimal ratingTrend; // 평점 트렌드 (양수: 상승, 음수: 하락)
    
    // 베이지안 평점 (낮은 리뷰 수에 대한 보정)
    @DecimalMin(value = "0.0", message = "베이지안 평점은 0.0 이상이어야 합니다")
    @DecimalMax(value = "5.0", message = "베이지안 평점은 5.0 이하여야 합니다")
    private BigDecimal bayesianRating;
    
    @Min(value = 0, message = "베이지안 가중치는 0 이상이어야 합니다")
    private Integer bayesianWeight; // 베이지안 계산에 사용된 가중치
    
    // 윌슨 점수 (신뢰구간 기반 평점)
    @DecimalMin(value = "0.0", message = "윌슨 점수 하한은 0.0 이상이어야 합니다")
    @DecimalMax(value = "1.0", message = "윌슨 점수 하한은 1.0 이하여야 합니다")
    private BigDecimal wilsonScoreLower; // 윌슨 점수 하한 (95% 신뢰구간)
    
    @DecimalMin(value = "0.0", message = "윌슨 점수 상한은 0.0 이상이어야 합니다")
    @DecimalMax(value = "1.0", message = "윌슨 점수 상한은 1.0 이하여야 합니다")
    private BigDecimal wilsonScoreUpper; // 윌슨 점수 상한 (95% 신뢰구간)
    
    // 품질 지표
    @NotNull(message = "평점 품질 레벨은 필수입니다")
    private QualityLevel qualityLevel;
    
    @DecimalMin(value = "0.0", message = "품질 점수는 0.0 이상이어야 합니다")
    @DecimalMax(value = "100.0", message = "품질 점수는 100.0 이하여야 합니다")
    private BigDecimal qualityScore; // 0-100 점수
    
    // 시간 정보
    private LocalDateTime lastReviewDate; // 마지막 리뷰 등록일
    private LocalDateTime lastCalculatedAt; // 마지막 통계 계산일
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    
    /**
     * 평점 품질 레벨
     */
    public enum QualityLevel {
        EXCELLENT("최우수", 90),
        VERY_GOOD("매우좋음", 80),
        GOOD("좋음", 70),
        AVERAGE("보통", 60),
        BELOW_AVERAGE("평균이하", 40),
        POOR("나쁨", 20),
        VERY_POOR("매우나쁨", 0);
        
        private final String description;
        private final int minScore;
        
        QualityLevel(String description, int minScore) {
            this.description = description;
            this.minScore = minScore;
        }
        
        public String getDescription() {
            return description;
        }
        
        public int getMinScore() {
            return minScore;
        }
        
        /**
         * 점수를 기반으로 품질 레벨 결정
         */
        public static QualityLevel fromScore(BigDecimal score) {
            int scoreInt = score.intValue();
            
            for (QualityLevel level : values()) {
                if (scoreInt >= level.minScore) {
                    return level;
                }
            }
            return VERY_POOR;
        }
    }
    
    /**
     * 평점 분포 배열 반환
     */
    public int[] getRatingDistribution() {
        return new int[]{
            rating1Count != null ? rating1Count : 0,
            rating2Count != null ? rating2Count : 0,
            rating3Count != null ? rating3Count : 0,
            rating4Count != null ? rating4Count : 0,
            rating5Count != null ? rating5Count : 0
        };
    }
    
    /**
     * 평균 평점 대비 최근 평점 변화율 계산
     */
    public BigDecimal getRecentTrendPercentage() {
        if (currentRating == null || currentRating.compareTo(BigDecimal.ZERO) == 0) {
            return BigDecimal.ZERO;
        }
        
        if (recentRating == null) {
            return BigDecimal.ZERO;
        }
        
        return recentRating.subtract(currentRating)
                .divide(currentRating, 4, BigDecimal.ROUND_HALF_UP)
                .multiply(new BigDecimal("100"));
    }
    
    /**
     * 긍정적 리뷰 비율 계산 (4점, 5점)
     */
    public BigDecimal getPositiveReviewRatio() {
        if (totalReviewCount == null || totalReviewCount == 0) {
            return BigDecimal.ZERO;
        }
        
        int positiveCount = (rating4Count != null ? rating4Count : 0) + 
                           (rating5Count != null ? rating5Count : 0);
        
        return new BigDecimal(positiveCount)
                .divide(new BigDecimal(totalReviewCount), 4, BigDecimal.ROUND_HALF_UP)
                .multiply(new BigDecimal("100"));
    }
    
    /**
     * 부정적 리뷰 비율 계산 (1점, 2점)
     */
    public BigDecimal getNegativeReviewRatio() {
        if (totalReviewCount == null || totalReviewCount == 0) {
            return BigDecimal.ZERO;
        }
        
        int negativeCount = (rating1Count != null ? rating1Count : 0) + 
                           (rating2Count != null ? rating2Count : 0);
        
        return new BigDecimal(negativeCount)
                .divide(new BigDecimal(totalReviewCount), 4, BigDecimal.ROUND_HALF_UP)
                .multiply(new BigDecimal("100"));
    }
    
    /**
     * 통계의 신뢰성 확인
     */
    public boolean isStatisticsReliable() {
        return totalReviewCount != null && totalReviewCount >= 5 && 
               reliabilityScore != null && reliabilityScore.compareTo(new BigDecimal("0.7")) >= 0;
    }
    
    /**
     * 최근 활동 여부 확인 (30일 이내)
     */
    public boolean hasRecentActivity() {
        if (lastReviewDate == null) {
            return false;
        }
        
        return lastReviewDate.isAfter(LocalDateTime.now().minusDays(30));
    }
} 