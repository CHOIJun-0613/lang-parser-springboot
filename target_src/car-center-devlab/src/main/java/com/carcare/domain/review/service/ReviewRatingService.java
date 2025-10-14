package com.carcare.domain.review.service;

import com.carcare.domain.review.repository.ReviewRepository;
import com.carcare.domain.review.dto.ReviewDto;
import com.carcare.domain.service.repository.ServiceCenterRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.math.BigDecimal;

/**
 * 리뷰 평점 계산 서비스
 */
@Service
@RequiredArgsConstructor
@Slf4j
@Transactional(readOnly = true)
public class ReviewRatingService {

    private final ReviewRepository reviewRepository;
    private final ServiceCenterRepository serviceCenterRepository;

    /**
     * 정비소별 평점 계산 및 업데이트
     */
    @Transactional
    public void updateServiceCenterRating(Long serviceCenterId) {
        log.info("정비소 평점 업데이트 시작: serviceCenterId={}", serviceCenterId);

        try {
            // 정비소별 리뷰 통계 조회
            ReviewDto.Statistics statistics = reviewRepository.getStatisticsByServiceCenterId(serviceCenterId);
            
            if (statistics != null && statistics.getTotalReviews() > 0) {
                // 정비소 평점 업데이트
                BigDecimal averageRating = BigDecimal.valueOf(statistics.getAverageRating());
                Integer reviewCount = statistics.getTotalReviews().intValue();
                serviceCenterRepository.updateRating(serviceCenterId, averageRating, reviewCount);
                
                log.info("정비소 평점 업데이트 완료: serviceCenterId={}, rating={}, totalReviews={}", 
                    serviceCenterId, statistics.getAverageRating(), statistics.getTotalReviews());
            } else {
                // 리뷰가 없는 경우 평점을 0으로 설정
                serviceCenterRepository.updateRating(serviceCenterId, BigDecimal.ZERO, 0);
                
                log.info("정비소 평점 초기화: serviceCenterId={}", serviceCenterId);
            }
            
        } catch (Exception e) {
            log.error("정비소 평점 업데이트 실패: serviceCenterId={}", serviceCenterId, e);
            throw e;
        }
    }

    /**
     * 정비소별 리뷰 통계 조회
     */
    public ReviewDto.Statistics getServiceCenterRatingStatistics(Long serviceCenterId) {
        log.debug("정비소 리뷰 통계 조회: serviceCenterId={}", serviceCenterId);
        
        ReviewDto.Statistics statistics = reviewRepository.getStatisticsByServiceCenterId(serviceCenterId);
        
        // 리뷰가 없는 경우 기본값 설정
        if (statistics == null) {
            statistics = ReviewDto.Statistics.builder()
                    .serviceCenterId(serviceCenterId)
                    .averageRating(0.0)
                    .totalReviews(0L)
                    .rating5Count(0L)
                    .rating4Count(0L)
                    .rating3Count(0L)
                    .rating2Count(0L)
                    .rating1Count(0L)
                    .build();
        }
        
        return statistics;
    }

    /**
     * 평점 분포 계산
     */
    public ReviewDto.Statistics calculateRatingDistribution(Long serviceCenterId) {
        log.debug("평점 분포 계산: serviceCenterId={}", serviceCenterId);
        
        ReviewDto.Statistics statistics = getServiceCenterRatingStatistics(serviceCenterId);
        
        if (statistics.getTotalReviews() > 0) {
            log.debug("평점 분포: 5점={}개, 4점={}개, 3점={}개, 2점={}개, 1점={}개",
                statistics.getRating5Count(),
                statistics.getRating4Count(),
                statistics.getRating3Count(),
                statistics.getRating2Count(),
                statistics.getRating1Count());
        }
        
        return statistics;
    }

    /**
     * 모든 정비소의 평점 재계산 (배치 작업용)
     */
    @Transactional
    public void recalculateAllServiceCenterRatings() {
        log.info("모든 정비소 평점 재계산 시작");
        
        try {
            // 모든 정비소 ID 조회
            // 실제 구현에서는 ServiceCenterRepository에서 모든 정비소 ID 목록을 조회
            // 현재는 임시로 로그만 출력
            log.info("모든 정비소 평점 재계산은 배치 작업으로 구현 예정");
            
        } catch (Exception e) {
            log.error("모든 정비소 평점 재계산 실패", e);
            throw e;
        }
    }

    /**
     * 평점 유효성 검증
     */
    public boolean isValidRating(Integer rating) {
        return rating != null && rating >= 1 && rating <= 5;
    }

    /**
     * 평점 범위 검증
     */
    public boolean isValidRatingRange(Integer minRating, Integer maxRating) {
        if (minRating == null && maxRating == null) {
            return true;
        }
        
        if (minRating != null && !isValidRating(minRating)) {
            return false;
        }
        
        if (maxRating != null && !isValidRating(maxRating)) {
            return false;
        }
        
        if (minRating != null && maxRating != null) {
            return minRating <= maxRating;
        }
        
        return true;
    }
} 