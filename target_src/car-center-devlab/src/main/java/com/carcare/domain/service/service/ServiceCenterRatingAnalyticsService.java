package com.carcare.domain.service.service;

import com.carcare.domain.service.entity.ServiceCenter;
import com.carcare.domain.service.entity.ServiceCenterRatingStatistics;
import com.carcare.domain.service.repository.ServiceCenterRepository;
import com.carcare.common.exception.BusinessException;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.util.*;
import java.util.stream.Collectors;

/**
 * 정비소 평점 분석 서비스
 * 평점 트렌드 분석, 비교 분석, 예측 등의 고급 분석 기능 제공
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ServiceCenterRatingAnalyticsService {

    private final ServiceCenterRepository serviceCenterRepository;
    private final ServiceCenterRatingCalculationService calculationService;

    /**
     * 정비소 평점 트렌드 분석
     */
    public RatingTrendAnalysis analyzeTrend(Long serviceCenterId, int days) {
        log.info("평점 트렌드 분석 시작: 정비소ID={}, 기간={}일", serviceCenterId, days);

        try {
            ServiceCenter serviceCenter = serviceCenterRepository.findById(serviceCenterId)
                .orElseThrow(() -> new BusinessException("정비소를 찾을 수 없습니다: " + serviceCenterId));

            // TODO: 실제 구현에서는 리뷰 히스토리 데이터를 조회하여 분석
            // 현재는 시뮬레이션 데이터로 분석

            List<DailyRatingData> dailyData = generateSimulationTrendData(serviceCenterId, days);
            
            return calculateTrendAnalysis(dailyData, serviceCenter.getAverageRating());

        } catch (Exception e) {
            log.error("평점 트렌드 분석 중 오류 발생: 정비소ID={}, 오류={}", serviceCenterId, e.getMessage(), e);
            throw new BusinessException("트렌드 분석 중 오류가 발생했습니다: " + e.getMessage());
        }
    }

    /**
     * 정비소 평점 비교 분석
     */
    public RatingComparisonAnalysis compareRatings(List<Long> serviceCenterIds) {
        log.info("평점 비교 분석 시작: 정비소 수={}", serviceCenterIds.size());

        try {
            List<ServiceCenter> serviceCenters = serviceCenterIds.stream()
                .map(id -> serviceCenterRepository.findById(id)
                    .orElseThrow(() -> new BusinessException("정비소를 찾을 수 없습니다: " + id)))
                .collect(Collectors.toList());

            return calculateComparisonAnalysis(serviceCenters);

        } catch (Exception e) {
            log.error("평점 비교 분석 중 오류 발생: 오류={}", e.getMessage(), e);
            throw new BusinessException("비교 분석 중 오류가 발생했습니다: " + e.getMessage());
        }
    }

    /**
     * 지역별 평점 분석
     */
    public RegionalRatingAnalysis analyzeRegionalRatings(String region) {
        log.info("지역별 평점 분석 시작: 지역={}", region);

        try {
            // TODO: 실제 구현에서는 지역별 정비소 조회
            List<ServiceCenter> regionalServiceCenters = serviceCenterRepository.findByAddress(region);

            return calculateRegionalAnalysis(regionalServiceCenters, region);

        } catch (Exception e) {
            log.error("지역별 평점 분석 중 오류 발생: 지역={}, 오류={}", region, e.getMessage(), e);
            throw new BusinessException("지역별 분석 중 오류가 발생했습니다: " + e.getMessage());
        }
    }

    /**
     * 평점 예측 분석
     */
    public RatingPrediction predictRating(Long serviceCenterId, int futureDays) {
        log.info("평점 예측 분석 시작: 정비소ID={}, 예측기간={}일", serviceCenterId, futureDays);

        try {
            ServiceCenter serviceCenter = serviceCenterRepository.findById(serviceCenterId)
                .orElseThrow(() -> new BusinessException("정비소를 찾을 수 없습니다: " + serviceCenterId));

            // 최근 30일 트렌드 분석
            RatingTrendAnalysis recentTrend = analyzeTrend(serviceCenterId, 30);
            
            return calculateRatingPrediction(serviceCenter, recentTrend, futureDays);

        } catch (Exception e) {
            log.error("평점 예측 분석 중 오류 발생: 정비소ID={}, 오류={}", serviceCenterId, e.getMessage(), e);
            throw new BusinessException("평점 예측 중 오류가 발생했습니다: " + e.getMessage());
        }
    }

    /**
     * 평점 품질 진단
     */
    public RatingQualityDiagnosis diagnoseRatingQuality(Long serviceCenterId) {
        log.info("평점 품질 진단 시작: 정비소ID={}", serviceCenterId);

        try {
            ServiceCenter serviceCenter = serviceCenterRepository.findById(serviceCenterId)
                .orElseThrow(() -> new BusinessException("정비소를 찾을 수 없습니다: " + serviceCenterId));

            return calculateQualityDiagnosis(serviceCenter);

        } catch (Exception e) {
            log.error("평점 품질 진단 중 오류 발생: 정비소ID={}, 오류={}", serviceCenterId, e.getMessage(), e);
            throw new BusinessException("품질 진단 중 오류가 발생했습니다: " + e.getMessage());
        }
    }

    /**
     * 업계 벤치마크 분석
     */
    public IndustryBenchmark getIndustryBenchmark() {
        log.info("업계 벤치마크 분석 시작");

        try {
            List<ServiceCenter> allServiceCenters = serviceCenterRepository.findAll();
            
            return calculateIndustryBenchmark(allServiceCenters);

        } catch (Exception e) {
            log.error("업계 벤치마크 분석 중 오류 발생: 오류={}", e.getMessage(), e);
            throw new BusinessException("벤치마크 분석 중 오류가 발생했습니다: " + e.getMessage());
        }
    }

    // === 내부 계산 메서드들 ===

    private RatingTrendAnalysis calculateTrendAnalysis(List<DailyRatingData> dailyData, BigDecimal currentRating) {
        if (dailyData.isEmpty()) {
            return RatingTrendAnalysis.builder()
                .trendDirection(TrendDirection.STABLE)
                .changeRate(BigDecimal.ZERO)
                .volatility(BigDecimal.ZERO)
                .confidence(BigDecimal.ZERO)
                .build();
        }

        // 트렌드 방향 계산
        BigDecimal firstRating = dailyData.get(0).getAverageRating();
        BigDecimal lastRating = dailyData.get(dailyData.size() - 1).getAverageRating();
        BigDecimal changeRate = lastRating.subtract(firstRating)
            .divide(firstRating, 4, RoundingMode.HALF_UP)
            .multiply(new BigDecimal("100"));

        TrendDirection direction = determineTrendDirection(changeRate);

        // 변동성 계산 (표준편차)
        BigDecimal volatility = calculateVolatility(dailyData);

        // 신뢰도 계산
        BigDecimal confidence = calculateTrendConfidence(dailyData, volatility);

        return RatingTrendAnalysis.builder()
            .trendDirection(direction)
            .changeRate(changeRate)
            .volatility(volatility)
            .confidence(confidence)
            .dailyData(dailyData)
            .analyzedPeriodDays(dailyData.size())
            .startRating(firstRating)
            .endRating(lastRating)
            .build();
    }

    private RatingComparisonAnalysis calculateComparisonAnalysis(List<ServiceCenter> serviceCenters) {
        List<ServiceCenterComparison> comparisons = serviceCenters.stream()
            .map(this::createServiceCenterComparison)
            .sorted(Comparator.comparing(ServiceCenterComparison::getRating).reversed())
            .collect(Collectors.toList());

        // 통계 계산
        BigDecimal avgRating = comparisons.stream()
            .map(ServiceCenterComparison::getRating)
            .reduce(BigDecimal.ZERO, BigDecimal::add)
            .divide(new BigDecimal(comparisons.size()), 2, RoundingMode.HALF_UP);

        BigDecimal maxRating = comparisons.stream()
            .map(ServiceCenterComparison::getRating)
            .max(BigDecimal::compareTo)
            .orElse(BigDecimal.ZERO);

        BigDecimal minRating = comparisons.stream()
            .map(ServiceCenterComparison::getRating)
            .min(BigDecimal::compareTo)
            .orElse(BigDecimal.ZERO);

        return RatingComparisonAnalysis.builder()
            .comparisons(comparisons)
            .averageRating(avgRating)
            .maxRating(maxRating)
            .minRating(minRating)
            .ratingRange(maxRating.subtract(minRating))
            .comparedServiceCenterCount(comparisons.size())
            .build();
    }

    private RegionalRatingAnalysis calculateRegionalAnalysis(List<ServiceCenter> serviceCenters, String region) {
        if (serviceCenters.isEmpty()) {
            return RegionalRatingAnalysis.builder()
                .region(region)
                .serviceCenterCount(0)
                .averageRating(BigDecimal.ZERO)
                .build();
        }

        BigDecimal totalRating = serviceCenters.stream()
            .map(ServiceCenter::getAverageRating)
            .reduce(BigDecimal.ZERO, BigDecimal::add);

        BigDecimal avgRating = totalRating.divide(new BigDecimal(serviceCenters.size()), 2, RoundingMode.HALF_UP);

        Integer totalReviews = serviceCenters.stream()
            .mapToInt(ServiceCenter::getReviewCount)
            .sum();

        return RegionalRatingAnalysis.builder()
            .region(region)
            .serviceCenterCount(serviceCenters.size())
            .averageRating(avgRating)
            .totalReviews(totalReviews)
            .topRatedServiceCenter(serviceCenters.stream()
                .max(Comparator.comparing(ServiceCenter::getAverageRating))
                .map(ServiceCenter::getName)
                .orElse("없음"))
            .build();
    }

    private RatingPrediction calculateRatingPrediction(ServiceCenter serviceCenter, 
                                                     RatingTrendAnalysis trend, int futureDays) {
        BigDecimal currentRating = serviceCenter.getAverageRating();
        BigDecimal trendRate = trend.getChangeRate().divide(new BigDecimal("100"), 6, RoundingMode.HALF_UP);
        
        // 선형 예측 (실제로는 더 복잡한 모델 사용)
        BigDecimal dailyChange = trendRate.divide(new BigDecimal(trend.getAnalyzedPeriodDays()), 6, RoundingMode.HALF_UP);
        BigDecimal predictedChange = dailyChange.multiply(new BigDecimal(futureDays));
        BigDecimal predictedRating = currentRating.add(currentRating.multiply(predictedChange));
        
        // 예측 신뢰도 (변동성이 클수록 낮아짐)
        BigDecimal confidence = BigDecimal.ONE.subtract(trend.getVolatility().divide(new BigDecimal("2"), 4, RoundingMode.HALF_UP))
            .max(new BigDecimal("0.1"));

        return RatingPrediction.builder()
            .currentRating(currentRating)
            .predictedRating(predictedRating.max(BigDecimal.ZERO).min(new BigDecimal("5")))
            .predictionDays(futureDays)
            .confidence(confidence)
            .trendDirection(trend.getTrendDirection())
            .expectedChange(predictedChange)
            .build();
    }

    private RatingQualityDiagnosis calculateQualityDiagnosis(ServiceCenter serviceCenter) {
        List<QualityIssue> issues = new ArrayList<>();
        BigDecimal qualityScore = new BigDecimal("100");

        // 리뷰 수 검사
        if (serviceCenter.getReviewCount() < 5) {
            issues.add(new QualityIssue("INSUFFICIENT_REVIEWS", "리뷰 수 부족", 
                "신뢰할 수 있는 평점을 위해 최소 5개 이상의 리뷰가 필요합니다.", QualityIssue.Severity.MEDIUM));
            qualityScore = qualityScore.subtract(new BigDecimal("20"));
        }

        // 평점 범위 검사
        if (serviceCenter.getAverageRating().compareTo(new BigDecimal("1")) < 0 || 
            serviceCenter.getAverageRating().compareTo(new BigDecimal("5")) > 0) {
            issues.add(new QualityIssue("INVALID_RATING_RANGE", "평점 범위 오류", 
                "평점이 유효한 범위(1-5)를 벗어났습니다.", QualityIssue.Severity.HIGH));
            qualityScore = qualityScore.subtract(new BigDecimal("30"));
        }

        // 평점 품질 레벨 결정
        ServiceCenterRatingStatistics.QualityLevel qualityLevel = 
            ServiceCenterRatingStatistics.QualityLevel.fromScore(qualityScore);

        return RatingQualityDiagnosis.builder()
            .serviceCenterId(serviceCenter.getId())
            .qualityScore(qualityScore)
            .qualityLevel(qualityLevel)
            .issues(issues)
            .isHealthy(issues.stream().noneMatch(issue -> issue.getSeverity() == QualityIssue.Severity.HIGH))
            .lastDiagnosedAt(LocalDateTime.now())
            .build();
    }

    private IndustryBenchmark calculateIndustryBenchmark(List<ServiceCenter> allServiceCenters) {
        if (allServiceCenters.isEmpty()) {
            return IndustryBenchmark.builder()
                .totalServiceCenters(0)
                .industryAverageRating(BigDecimal.ZERO)
                .build();
        }

        BigDecimal totalRating = allServiceCenters.stream()
            .map(ServiceCenter::getAverageRating)
            .reduce(BigDecimal.ZERO, BigDecimal::add);

        BigDecimal industryAverage = totalRating.divide(new BigDecimal(allServiceCenters.size()), 2, RoundingMode.HALF_UP);

        // 백분위수 계산
        List<BigDecimal> sortedRatings = allServiceCenters.stream()
            .map(ServiceCenter::getAverageRating)
            .sorted()
            .collect(Collectors.toList());

        int size = sortedRatings.size();
        BigDecimal percentile25 = sortedRatings.get(size / 4);
        BigDecimal percentile50 = sortedRatings.get(size / 2);
        BigDecimal percentile75 = sortedRatings.get(size * 3 / 4);
        BigDecimal percentile90 = sortedRatings.get(size * 9 / 10);

        return IndustryBenchmark.builder()
            .totalServiceCenters(allServiceCenters.size())
            .industryAverageRating(industryAverage)
            .percentile25(percentile25)
            .percentile50(percentile50)
            .percentile75(percentile75)
            .percentile90(percentile90)
            .topPerformers(allServiceCenters.stream()
                .filter(sc -> sc.getAverageRating().compareTo(percentile90) >= 0)
                .limit(10)
                .map(ServiceCenter::getName)
                .collect(Collectors.toList()))
            .calculatedAt(LocalDateTime.now())
            .build();
    }

    // === 헬퍼 메서드들 ===

    private List<DailyRatingData> generateSimulationTrendData(Long serviceCenterId, int days) {
        // TODO: 실제 구현에서는 데이터베이스에서 조회
        List<DailyRatingData> data = new ArrayList<>();
        Random random = new Random();
        BigDecimal baseRating = new BigDecimal("4.0");

        for (int i = 0; i < days; i++) {
            LocalDateTime date = LocalDateTime.now().minusDays(days - i);
            BigDecimal rating = baseRating.add(new BigDecimal(random.nextGaussian() * 0.5));
            rating = rating.max(new BigDecimal("1")).min(new BigDecimal("5"));
            
            data.add(DailyRatingData.builder()
                .date(date)
                .averageRating(rating.setScale(2, RoundingMode.HALF_UP))
                .reviewCount(random.nextInt(10) + 1)
                .build());
        }
        
        return data;
    }

    private TrendDirection determineTrendDirection(BigDecimal changeRate) {
        if (changeRate.compareTo(new BigDecimal("5")) >= 0) {
            return TrendDirection.STRONG_UPWARD;
        } else if (changeRate.compareTo(new BigDecimal("1")) >= 0) {
            return TrendDirection.UPWARD;
        } else if (changeRate.compareTo(new BigDecimal("-1")) >= 0) {
            return TrendDirection.STABLE;
        } else if (changeRate.compareTo(new BigDecimal("-5")) >= 0) {
            return TrendDirection.DOWNWARD;
        } else {
            return TrendDirection.STRONG_DOWNWARD;
        }
    }

    private BigDecimal calculateVolatility(List<DailyRatingData> dailyData) {
        if (dailyData.size() < 2) return BigDecimal.ZERO;

        BigDecimal mean = dailyData.stream()
            .map(DailyRatingData::getAverageRating)
            .reduce(BigDecimal.ZERO, BigDecimal::add)
            .divide(new BigDecimal(dailyData.size()), 4, RoundingMode.HALF_UP);

        BigDecimal variance = dailyData.stream()
            .map(data -> data.getAverageRating().subtract(mean).pow(2))
            .reduce(BigDecimal.ZERO, BigDecimal::add)
            .divide(new BigDecimal(dailyData.size() - 1), 4, RoundingMode.HALF_UP);

        return variance.sqrt(new java.math.MathContext(4));
    }

    private BigDecimal calculateTrendConfidence(List<DailyRatingData> dailyData, BigDecimal volatility) {
        // 데이터 점 수와 변동성을 기반으로 신뢰도 계산
        BigDecimal dataPointWeight = new BigDecimal(Math.min(dailyData.size(), 30))
            .divide(new BigDecimal("30"), 4, RoundingMode.HALF_UP);
        
        BigDecimal volatilityWeight = BigDecimal.ONE.subtract(
            volatility.divide(new BigDecimal("2"), 4, RoundingMode.HALF_UP)
        ).max(BigDecimal.ZERO);

        return dataPointWeight.multiply(volatilityWeight)
            .max(new BigDecimal("0.1"))
            .min(BigDecimal.ONE);
    }

    private ServiceCenterComparison createServiceCenterComparison(ServiceCenter serviceCenter) {
        return ServiceCenterComparison.builder()
            .serviceCenterId(serviceCenter.getId())
            .name(serviceCenter.getName())
            .rating(serviceCenter.getAverageRating())
            .reviewCount(serviceCenter.getReviewCount())
            .isVerified(serviceCenter.getIsVerified())
            .build();
    }

    // === 결과 클래스들 ===

    public enum TrendDirection {
        STRONG_UPWARD("강한 상승"), UPWARD("상승"), STABLE("안정"), 
        DOWNWARD("하락"), STRONG_DOWNWARD("강한 하락");
        
        private final String description;
        TrendDirection(String description) { this.description = description; }
        public String getDescription() { return description; }
    }

    @lombok.Data @lombok.Builder
    public static class DailyRatingData {
        private LocalDateTime date;
        private BigDecimal averageRating;
        private Integer reviewCount;
    }

    @lombok.Data @lombok.Builder
    public static class RatingTrendAnalysis {
        private TrendDirection trendDirection;
        private BigDecimal changeRate; // 변화율 (%)
        private BigDecimal volatility; // 변동성
        private BigDecimal confidence; // 신뢰도
        private List<DailyRatingData> dailyData;
        private Integer analyzedPeriodDays;
        private BigDecimal startRating;
        private BigDecimal endRating;
    }

    @lombok.Data @lombok.Builder
    public static class ServiceCenterComparison {
        private Long serviceCenterId;
        private String name;
        private BigDecimal rating;
        private Integer reviewCount;
        private Boolean isVerified;
    }

    @lombok.Data @lombok.Builder
    public static class RatingComparisonAnalysis {
        private List<ServiceCenterComparison> comparisons;
        private BigDecimal averageRating;
        private BigDecimal maxRating;
        private BigDecimal minRating;
        private BigDecimal ratingRange;
        private Integer comparedServiceCenterCount;
    }

    @lombok.Data @lombok.Builder
    public static class RegionalRatingAnalysis {
        private String region;
        private Integer serviceCenterCount;
        private BigDecimal averageRating;
        private Integer totalReviews;
        private String topRatedServiceCenter;
    }

    @lombok.Data @lombok.Builder
    public static class RatingPrediction {
        private BigDecimal currentRating;
        private BigDecimal predictedRating;
        private Integer predictionDays;
        private BigDecimal confidence;
        private TrendDirection trendDirection;
        private BigDecimal expectedChange;
    }

    @lombok.Data @lombok.Builder
    public static class QualityIssue {
        private String code;
        private String title;
        private String description;
        private Severity severity;
        
        public enum Severity { LOW, MEDIUM, HIGH, CRITICAL }
    }

    @lombok.Data @lombok.Builder
    public static class RatingQualityDiagnosis {
        private Long serviceCenterId;
        private BigDecimal qualityScore;
        private ServiceCenterRatingStatistics.QualityLevel qualityLevel;
        private List<QualityIssue> issues;
        private Boolean isHealthy;
        private LocalDateTime lastDiagnosedAt;
    }

    @lombok.Data @lombok.Builder
    public static class IndustryBenchmark {
        private Integer totalServiceCenters;
        private BigDecimal industryAverageRating;
        private BigDecimal percentile25;
        private BigDecimal percentile50;
        private BigDecimal percentile75;
        private BigDecimal percentile90;
        private List<String> topPerformers;
        private LocalDateTime calculatedAt;
    }
} 