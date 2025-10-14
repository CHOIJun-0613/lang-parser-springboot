package com.carcare.domain.service.service;

import com.carcare.domain.service.entity.ServiceCenterRatingHistory;
import com.carcare.domain.service.entity.ServiceCenterRatingStatistics;
import com.carcare.common.exception.BusinessException;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

/**
 * 정비소 평점 계산 서비스
 * 다양한 알고리즘을 사용하여 정비소 평점을 계산하고 관리
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ServiceCenterRatingCalculationService {

    // 베이지안 평점 계산을 위한 기본값
    private static final BigDecimal DEFAULT_PRIOR_RATING = new BigDecimal("3.0"); // 기본 평점
    private static final int DEFAULT_PRIOR_COUNT = 10; // 기본 리뷰 수 가중치
    
    // 윌슨 점수 계산을 위한 Z값 (95% 신뢰구간)
    private static final BigDecimal Z_SCORE_95 = new BigDecimal("1.96");

    /**
     * 단순 평균 평점 계산
     */
    public BigDecimal calculateSimpleAverage(List<Integer> ratings) {
        if (ratings == null || ratings.isEmpty()) {
            return BigDecimal.ZERO;
        }

        log.debug("단순 평균 계산: 리뷰 수={}", ratings.size());

        BigDecimal sum = ratings.stream()
            .map(BigDecimal::new)
            .reduce(BigDecimal.ZERO, BigDecimal::add);

        return sum.divide(new BigDecimal(ratings.size()), 2, RoundingMode.HALF_UP);
    }

    /**
     * 가중 평균 평점 계산 (최근 리뷰에 더 높은 가중치)
     */
    public BigDecimal calculateWeightedAverage(List<RatingWithTimestamp> ratings) {
        if (ratings == null || ratings.isEmpty()) {
            return BigDecimal.ZERO;
        }

        log.debug("가중 평균 계산: 리뷰 수={}", ratings.size());

        LocalDateTime now = LocalDateTime.now();
        BigDecimal weightedSum = BigDecimal.ZERO;
        BigDecimal totalWeight = BigDecimal.ZERO;

        for (RatingWithTimestamp rating : ratings) {
            // 최근성에 따른 가중치 계산 (최근 30일 = 1.0, 그 이후는 감소)
            long daysSinceReview = java.time.Duration.between(rating.getTimestamp(), now).toDays();
            BigDecimal weight = calculateTimeWeight(daysSinceReview);
            
            weightedSum = weightedSum.add(new BigDecimal(rating.getRating()).multiply(weight));
            totalWeight = totalWeight.add(weight);
        }

        return weightedSum.divide(totalWeight, 2, RoundingMode.HALF_UP);
    }

    /**
     * 베이지안 평점 계산 (낮은 리뷰 수에 대한 보정)
     */
    public BayesianRatingResult calculateBayesianAverage(List<Integer> ratings) {
        if (ratings == null || ratings.isEmpty()) {
            return BayesianRatingResult.builder()
                .rating(DEFAULT_PRIOR_RATING)
                .confidence(BigDecimal.ZERO)
                .effectiveReviewCount(DEFAULT_PRIOR_COUNT)
                .build();
        }

        log.debug("베이지안 평균 계산: 리뷰 수={}", ratings.size());

        // 실제 평점 계산
        BigDecimal actualAverage = calculateSimpleAverage(ratings);
        int actualCount = ratings.size();

        // 베이지안 평점 = (prior_count * prior_rating + actual_count * actual_rating) / (prior_count + actual_count)
        BigDecimal numerator = DEFAULT_PRIOR_RATING.multiply(new BigDecimal(DEFAULT_PRIOR_COUNT))
            .add(actualAverage.multiply(new BigDecimal(actualCount)));
        
        BigDecimal denominator = new BigDecimal(DEFAULT_PRIOR_COUNT + actualCount);
        BigDecimal bayesianRating = numerator.divide(denominator, 2, RoundingMode.HALF_UP);

        // 신뢰도 계산 (실제 리뷰 수 비율)
        BigDecimal confidence = new BigDecimal(actualCount)
            .divide(new BigDecimal(DEFAULT_PRIOR_COUNT + actualCount), 4, RoundingMode.HALF_UP);

        return BayesianRatingResult.builder()
            .rating(bayesianRating)
            .confidence(confidence)
            .effectiveReviewCount(DEFAULT_PRIOR_COUNT + actualCount)
            .priorWeight(DEFAULT_PRIOR_COUNT)
            .actualWeight(actualCount)
            .build();
    }

    /**
     * 윌슨 점수 계산 (신뢰구간 기반)
     * 좋은 평점 비율에 대한 95% 신뢰구간의 하한값
     */
    public WilsonScoreResult calculateWilsonScore(List<Integer> ratings) {
        if (ratings == null || ratings.isEmpty()) {
            return WilsonScoreResult.builder()
                .lowerBound(BigDecimal.ZERO)
                .upperBound(BigDecimal.ZERO)
                .score(BigDecimal.ZERO)
                .sampleSize(0)
                .build();
        }

        log.debug("윌슨 점수 계산: 리뷰 수={}", ratings.size());

        int n = ratings.size();
        
        // 좋은 평점(4점, 5점)의 개수 계산
        long positiveCount = ratings.stream()
            .filter(rating -> rating >= 4)
            .count();

        if (n == 0) {
            return WilsonScoreResult.builder()
                .lowerBound(BigDecimal.ZERO)
                .upperBound(BigDecimal.ZERO)
                .score(BigDecimal.ZERO)
                .sampleSize(0)
                .build();
        }

        BigDecimal p = new BigDecimal(positiveCount).divide(new BigDecimal(n), 6, RoundingMode.HALF_UP);
        BigDecimal nBig = new BigDecimal(n);
        BigDecimal z = Z_SCORE_95;
        BigDecimal zSquared = z.multiply(z);

        // 윌슨 점수 공식
        BigDecimal numerator1 = p.add(zSquared.divide(nBig.multiply(new BigDecimal(2)), 6, RoundingMode.HALF_UP));
        BigDecimal sqrtTerm = z.multiply(
            p.multiply(BigDecimal.ONE.subtract(p)).divide(nBig, 6, RoundingMode.HALF_UP)
            .add(zSquared.divide(nBig.multiply(new BigDecimal(4)), 6, RoundingMode.HALF_UP))
        ).sqrt(new java.math.MathContext(6));
        
        BigDecimal denominator = BigDecimal.ONE.add(zSquared.divide(nBig, 6, RoundingMode.HALF_UP));

        BigDecimal lowerBound = numerator1.subtract(sqrtTerm).divide(denominator, 4, RoundingMode.HALF_UP);
        BigDecimal upperBound = numerator1.add(sqrtTerm).divide(denominator, 4, RoundingMode.HALF_UP);

        return WilsonScoreResult.builder()
            .lowerBound(lowerBound)
            .upperBound(upperBound)
            .score(lowerBound) // 보수적으로 하한값을 점수로 사용
            .sampleSize(n)
            .positiveCount((int) positiveCount)
            .positiveRatio(p)
            .build();
    }

    /**
     * 평점 분포 분석
     */
    public RatingDistributionAnalysis analyzeRatingDistribution(List<Integer> ratings) {
        if (ratings == null || ratings.isEmpty()) {
            return RatingDistributionAnalysis.builder()
                .totalCount(0)
                .distribution(new int[5])
                .mean(BigDecimal.ZERO)
                .variance(BigDecimal.ZERO)
                .standardDeviation(BigDecimal.ZERO)
                .skewness(BigDecimal.ZERO)
                .kurtosis(BigDecimal.ZERO)
                .build();
        }

        log.debug("평점 분포 분석: 리뷰 수={}", ratings.size());

        // 분포 계산
        int[] distribution = new int[5];
        for (Integer rating : ratings) {
            if (rating >= 1 && rating <= 5) {
                distribution[rating - 1]++;
            }
        }

        // 기본 통계
        BigDecimal mean = calculateSimpleAverage(ratings);
        BigDecimal variance = calculateVariance(ratings, mean);
        BigDecimal stdDev = variance.sqrt(new java.math.MathContext(4));
        
        // 왜도와 첨도 계산
        BigDecimal skewness = calculateSkewness(ratings, mean, stdDev);
        BigDecimal kurtosis = calculateKurtosis(ratings, mean, stdDev);

        return RatingDistributionAnalysis.builder()
            .totalCount(ratings.size())
            .distribution(distribution)
            .mean(mean)
            .variance(variance)
            .standardDeviation(stdDev)
            .skewness(skewness)
            .kurtosis(kurtosis)
            .build();
    }

    /**
     * 종합 평점 계산 (여러 알고리즘의 결합)
     */
    public ComprehensiveRatingResult calculateComprehensiveRating(List<RatingWithTimestamp> ratings) {
        if (ratings == null || ratings.isEmpty()) {
            return ComprehensiveRatingResult.builder()
                .finalRating(BigDecimal.ZERO)
                .confidence(BigDecimal.ZERO)
                .qualityScore(BigDecimal.ZERO)
                .reliabilityScore(BigDecimal.ZERO)
                .build();
        }

        log.info("종합 평점 계산 시작: 리뷰 수={}", ratings.size());

        // 각 알고리즘별 계산
        List<Integer> simpleRatings = ratings.stream()
            .map(RatingWithTimestamp::getRating)
            .toList();

        BigDecimal simpleAverage = calculateSimpleAverage(simpleRatings);
        BigDecimal weightedAverage = calculateWeightedAverage(ratings);
        BayesianRatingResult bayesian = calculateBayesianAverage(simpleRatings);
        WilsonScoreResult wilson = calculateWilsonScore(simpleRatings);
        RatingDistributionAnalysis distribution = analyzeRatingDistribution(simpleRatings);

        // 가중치 계산 (리뷰 수와 다양성에 따라)
        BigDecimal reviewCountWeight = calculateReviewCountWeight(ratings.size());
        BigDecimal diversityWeight = calculateDiversityWeight(distribution);
        BigDecimal recencyWeight = calculateRecencyWeight(ratings);

        // 최종 평점 계산 (가중 평균)
        BigDecimal finalRating = simpleAverage.multiply(new BigDecimal("0.3"))
            .add(weightedAverage.multiply(new BigDecimal("0.2")))
            .add(bayesian.getRating().multiply(new BigDecimal("0.3")))
            .add(wilson.getScore().multiply(new BigDecimal("5")).multiply(new BigDecimal("0.2")));

        // 신뢰도 점수 계산
        BigDecimal confidence = reviewCountWeight
            .multiply(diversityWeight)
            .multiply(recencyWeight)
            .multiply(bayesian.getConfidence());

        // 품질 점수 계산 (0-100)
        BigDecimal qualityScore = calculateQualityScore(finalRating, confidence, distribution, ratings.size());

        // 신뢰성 점수 계산
        BigDecimal reliabilityScore = calculateReliabilityScore(distribution, ratings.size(), confidence);

        return ComprehensiveRatingResult.builder()
            .finalRating(finalRating)
            .simpleAverage(simpleAverage)
            .weightedAverage(weightedAverage)
            .bayesianRating(bayesian.getRating())
            .wilsonScore(wilson.getScore().multiply(new BigDecimal("5"))) // 0-1을 0-5로 변환
            .confidence(confidence)
            .qualityScore(qualityScore)
            .reliabilityScore(reliabilityScore)
            .reviewCount(ratings.size())
            .distributionAnalysis(distribution)
            .calculationMethod(ServiceCenterRatingHistory.CalculationMethod.CUSTOM_ALGORITHM)
            .build();
    }

    // === 내부 헬퍼 메서드들 ===

    private BigDecimal calculateTimeWeight(long daysSinceReview) {
        if (daysSinceReview <= 30) {
            return BigDecimal.ONE; // 최근 30일은 100% 가중치
        } else if (daysSinceReview <= 90) {
            return new BigDecimal("0.8"); // 30-90일은 80% 가중치
        } else if (daysSinceReview <= 180) {
            return new BigDecimal("0.6"); // 90-180일은 60% 가중치
        } else if (daysSinceReview <= 365) {
            return new BigDecimal("0.4"); // 180-365일은 40% 가중치
        } else {
            return new BigDecimal("0.2"); // 1년 이상은 20% 가중치
        }
    }

    private BigDecimal calculateVariance(List<Integer> ratings, BigDecimal mean) {
        if (ratings.size() <= 1) {
            return BigDecimal.ZERO;
        }

        BigDecimal sumSquaredDiff = ratings.stream()
            .map(BigDecimal::new)
            .map(rating -> rating.subtract(mean).pow(2))
            .reduce(BigDecimal.ZERO, BigDecimal::add);

        return sumSquaredDiff.divide(new BigDecimal(ratings.size() - 1), 4, RoundingMode.HALF_UP);
    }

    private BigDecimal calculateSkewness(List<Integer> ratings, BigDecimal mean, BigDecimal stdDev) {
        if (ratings.size() < 3 || stdDev.compareTo(BigDecimal.ZERO) == 0) {
            return BigDecimal.ZERO;
        }

        BigDecimal sumCubedDiff = ratings.stream()
            .map(BigDecimal::new)
            .map(rating -> rating.subtract(mean).divide(stdDev, 6, RoundingMode.HALF_UP).pow(3))
            .reduce(BigDecimal.ZERO, BigDecimal::add);

        return sumCubedDiff.divide(new BigDecimal(ratings.size()), 4, RoundingMode.HALF_UP);
    }

    private BigDecimal calculateKurtosis(List<Integer> ratings, BigDecimal mean, BigDecimal stdDev) {
        if (ratings.size() < 4 || stdDev.compareTo(BigDecimal.ZERO) == 0) {
            return BigDecimal.ZERO;
        }

        BigDecimal sumFourthDiff = ratings.stream()
            .map(BigDecimal::new)
            .map(rating -> rating.subtract(mean).divide(stdDev, 6, RoundingMode.HALF_UP).pow(4))
            .reduce(BigDecimal.ZERO, BigDecimal::add);

        return sumFourthDiff.divide(new BigDecimal(ratings.size()), 4, RoundingMode.HALF_UP)
            .subtract(new BigDecimal("3")); // 정규분포의 첨도(3)를 뺀 excess kurtosis
    }

    private BigDecimal calculateReviewCountWeight(int reviewCount) {
        if (reviewCount >= 100) return BigDecimal.ONE;
        if (reviewCount >= 50) return new BigDecimal("0.9");
        if (reviewCount >= 20) return new BigDecimal("0.8");
        if (reviewCount >= 10) return new BigDecimal("0.7");
        if (reviewCount >= 5) return new BigDecimal("0.6");
        return new BigDecimal("0.5");
    }

    private BigDecimal calculateDiversityWeight(RatingDistributionAnalysis distribution) {
        // 평점 분포의 다양성을 측정 (표준편차 기반)
        if (distribution.getStandardDeviation().compareTo(new BigDecimal("1.0")) >= 0) {
            return BigDecimal.ONE;
        }
        return distribution.getStandardDeviation();
    }

    private BigDecimal calculateRecencyWeight(List<RatingWithTimestamp> ratings) {
        if (ratings.isEmpty()) return BigDecimal.ZERO;

        LocalDateTime now = LocalDateTime.now();
        long recentCount = ratings.stream()
            .filter(rating -> rating.getTimestamp().isAfter(now.minusDays(90)))
            .count();

        BigDecimal recencyRatio = new BigDecimal(recentCount)
            .divide(new BigDecimal(ratings.size()), 4, RoundingMode.HALF_UP);

        return recencyRatio.multiply(new BigDecimal("0.5")).add(new BigDecimal("0.5"));
    }

    private BigDecimal calculateQualityScore(BigDecimal finalRating, BigDecimal confidence, 
                                           RatingDistributionAnalysis distribution, int reviewCount) {
        // 평점 기여도 (40%)
        BigDecimal ratingScore = finalRating.multiply(new BigDecimal("20"));
        
        // 신뢰도 기여도 (30%)
        BigDecimal confidenceScore = confidence.multiply(new BigDecimal("30"));
        
        // 리뷰 수 기여도 (20%)
        BigDecimal reviewScore = calculateReviewCountWeight(reviewCount).multiply(new BigDecimal("20"));
        
        // 분포 안정성 기여도 (10%)
        BigDecimal stabilityScore = BigDecimal.ONE.subtract(
            distribution.getStandardDeviation().divide(new BigDecimal("2"), 4, RoundingMode.HALF_UP)
        ).multiply(new BigDecimal("10"));

        return ratingScore.add(confidenceScore).add(reviewScore).add(stabilityScore)
            .max(BigDecimal.ZERO).min(new BigDecimal("100"));
    }

    private BigDecimal calculateReliabilityScore(RatingDistributionAnalysis distribution, 
                                               int reviewCount, BigDecimal confidence) {
        // 샘플 크기 신뢰성
        BigDecimal sampleReliability = calculateReviewCountWeight(reviewCount);
        
        // 분포 신뢰성 (극단값 비율 확인)
        int[] dist = distribution.getDistribution();
        int extremeCount = dist[0] + dist[4]; // 1점과 5점
        BigDecimal extremeRatio = new BigDecimal(extremeCount)
            .divide(new BigDecimal(reviewCount), 4, RoundingMode.HALF_UP);
        BigDecimal distributionReliability = BigDecimal.ONE.subtract(extremeRatio.multiply(new BigDecimal("0.5")));

        return sampleReliability
            .multiply(distributionReliability)
            .multiply(confidence)
            .max(BigDecimal.ZERO)
            .min(BigDecimal.ONE);
    }

    // === 결과 클래스들 ===

    @lombok.Data
    @lombok.Builder
    public static class RatingWithTimestamp {
        private int rating;
        private LocalDateTime timestamp;
    }

    @lombok.Data
    @lombok.Builder
    public static class BayesianRatingResult {
        private BigDecimal rating;
        private BigDecimal confidence;
        private int effectiveReviewCount;
        private int priorWeight;
        private int actualWeight;
    }

    @lombok.Data
    @lombok.Builder
    public static class WilsonScoreResult {
        private BigDecimal lowerBound;
        private BigDecimal upperBound;
        private BigDecimal score;
        private int sampleSize;
        private int positiveCount;
        private BigDecimal positiveRatio;
    }

    @lombok.Data
    @lombok.Builder
    public static class RatingDistributionAnalysis {
        private int totalCount;
        private int[] distribution; // [1점, 2점, 3점, 4점, 5점] 개수
        private BigDecimal mean;
        private BigDecimal variance;
        private BigDecimal standardDeviation;
        private BigDecimal skewness; // 왜도
        private BigDecimal kurtosis; // 첨도
    }

    @lombok.Data
    @lombok.Builder
    public static class ComprehensiveRatingResult {
        private BigDecimal finalRating;
        private BigDecimal simpleAverage;
        private BigDecimal weightedAverage;
        private BigDecimal bayesianRating;
        private BigDecimal wilsonScore;
        private BigDecimal confidence;
        private BigDecimal qualityScore;
        private BigDecimal reliabilityScore;
        private int reviewCount;
        private RatingDistributionAnalysis distributionAnalysis;
        private ServiceCenterRatingHistory.CalculationMethod calculationMethod;
    }
} 