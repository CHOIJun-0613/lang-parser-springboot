package com.carcare.domain.service.service;

import com.carcare.domain.service.entity.ServiceCenter;
import com.carcare.domain.service.entity.ServiceCenterRatingHistory;
import com.carcare.domain.service.entity.ServiceCenterRatingStatistics;
import com.carcare.domain.service.repository.ServiceCenterRepository;
import com.carcare.common.exception.BusinessException;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.context.ApplicationEventPublisher;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

/**
 * 정비소 평점 관리 서비스
 * 평점 업데이트 이벤트 처리, 히스토리 관리, 통계 계산을 담당
 */
@Slf4j
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class ServiceCenterRatingManagementService {

    private final ServiceCenterRepository serviceCenterRepository;
    private final ServiceCenterRatingCalculationService calculationService;
    private final ApplicationEventPublisher eventPublisher;

    /**
     * 리뷰 추가 시 평점 업데이트
     */
    @Transactional
    public void handleReviewAdded(Long serviceCenterId, Integer newRating, Long reviewId, Long userId) {
        log.info("리뷰 추가 이벤트 처리 시작: 정비소ID={}, 평점={}, 리뷰ID={}", serviceCenterId, newRating, reviewId);

        try {
            // 현재 정비소 정보 조회
            ServiceCenter serviceCenter = serviceCenterRepository.findById(serviceCenterId)
                .orElseThrow(() -> new BusinessException("정비소를 찾을 수 없습니다: " + serviceCenterId));

            // 이전 평점 정보 저장
            BigDecimal previousRating = serviceCenter.getAverageRating();
            Integer previousReviewCount = serviceCenter.getReviewCount();

            // 새로운 평점 계산
            RatingUpdateResult updateResult = calculateNewRating(serviceCenterId, newRating, RatingChangeType.REVIEW_ADDED);

            // 정비소 평점 업데이트
            updateServiceCenterRating(serviceCenterId, updateResult, userId);

            // 평점 히스토리 기록
            recordRatingHistory(serviceCenterId, previousRating, previousReviewCount, 
                              updateResult, ServiceCenterRatingHistory.ChangeType.REVIEW_ADDED, 
                              reviewId, "새로운 리뷰 추가", userId);

            // 통계 업데이트
            updateRatingStatistics(serviceCenterId, updateResult);

            // 이벤트 발행 (캐시 무효화, 알림 등)
            publishRatingUpdateEvent(serviceCenterId, previousRating, updateResult.getNewRating(), userId);

            log.info("리뷰 추가 이벤트 처리 완료: 정비소ID={}, 이전평점={}, 신규평점={}", 
                    serviceCenterId, previousRating, updateResult.getNewRating());

        } catch (Exception e) {
            log.error("리뷰 추가 이벤트 처리 중 오류 발생: 정비소ID={}, 오류={}", serviceCenterId, e.getMessage(), e);
            throw new BusinessException("평점 업데이트 중 오류가 발생했습니다: " + e.getMessage());
        }
    }

    /**
     * 리뷰 수정 시 평점 업데이트
     */
    @Transactional
    public void handleReviewUpdated(Long serviceCenterId, Integer oldRating, Integer newRating, 
                                   Long reviewId, Long userId) {
        log.info("리뷰 수정 이벤트 처리 시작: 정비소ID={}, 이전평점={}, 신규평점={}, 리뷰ID={}", 
                serviceCenterId, oldRating, newRating, reviewId);

        if (oldRating.equals(newRating)) {
            log.debug("평점 변경 없음: 처리 생략");
            return;
        }

        try {
            ServiceCenter serviceCenter = serviceCenterRepository.findById(serviceCenterId)
                .orElseThrow(() -> new BusinessException("정비소를 찾을 수 없습니다: " + serviceCenterId));

            BigDecimal previousRating = serviceCenter.getAverageRating();
            Integer previousReviewCount = serviceCenter.getReviewCount();

            // 평점 재계산 (기존 리뷰를 제거하고 새 리뷰 추가한 효과)
            RatingUpdateResult updateResult = recalculateRatingAfterReviewUpdate(serviceCenterId, oldRating, newRating);

            updateServiceCenterRating(serviceCenterId, updateResult, userId);

            recordRatingHistory(serviceCenterId, previousRating, previousReviewCount, 
                              updateResult, ServiceCenterRatingHistory.ChangeType.REVIEW_UPDATED, 
                              reviewId, String.format("리뷰 평점 수정: %d점 → %d점", oldRating, newRating), userId);

            updateRatingStatistics(serviceCenterId, updateResult);

            publishRatingUpdateEvent(serviceCenterId, previousRating, updateResult.getNewRating(), userId);

            log.info("리뷰 수정 이벤트 처리 완료: 정비소ID={}", serviceCenterId);

        } catch (Exception e) {
            log.error("리뷰 수정 이벤트 처리 중 오류 발생: 정비소ID={}, 오류={}", serviceCenterId, e.getMessage(), e);
            throw new BusinessException("평점 업데이트 중 오류가 발생했습니다: " + e.getMessage());
        }
    }

    /**
     * 리뷰 삭제 시 평점 업데이트
     */
    @Transactional
    public void handleReviewDeleted(Long serviceCenterId, Integer deletedRating, Long reviewId, Long userId) {
        log.info("리뷰 삭제 이벤트 처리 시작: 정비소ID={}, 삭제된평점={}, 리뷰ID={}", 
                serviceCenterId, deletedRating, reviewId);

        try {
            ServiceCenter serviceCenter = serviceCenterRepository.findById(serviceCenterId)
                .orElseThrow(() -> new BusinessException("정비소를 찾을 수 없습니다: " + serviceCenterId));

            BigDecimal previousRating = serviceCenter.getAverageRating();
            Integer previousReviewCount = serviceCenter.getReviewCount();

            if (previousReviewCount <= 1) {
                // 마지막 리뷰 삭제 시 평점 초기화
                RatingUpdateResult updateResult = RatingUpdateResult.builder()
                    .newRating(BigDecimal.ZERO)
                    .newReviewCount(0)
                    .ratingChange(previousRating.negate())
                    .reviewCountChange(-1)
                    .calculationMethod(ServiceCenterRatingHistory.CalculationMethod.SIMPLE_AVERAGE)
                    .build();

                updateServiceCenterRating(serviceCenterId, updateResult, userId);
                recordRatingHistory(serviceCenterId, previousRating, previousReviewCount, 
                                  updateResult, ServiceCenterRatingHistory.ChangeType.REVIEW_DELETED, 
                                  reviewId, "마지막 리뷰 삭제로 평점 초기화", userId);
            } else {
                // 평점 재계산
                RatingUpdateResult updateResult = calculateNewRating(serviceCenterId, -deletedRating, RatingChangeType.REVIEW_DELETED);
                
                updateServiceCenterRating(serviceCenterId, updateResult, userId);
                recordRatingHistory(serviceCenterId, previousRating, previousReviewCount, 
                                  updateResult, ServiceCenterRatingHistory.ChangeType.REVIEW_DELETED, 
                                  reviewId, String.format("리뷰 삭제: %d점", deletedRating), userId);
            }

            updateRatingStatistics(serviceCenterId, null); // 통계 재계산
            publishRatingUpdateEvent(serviceCenterId, previousRating, serviceCenter.getAverageRating(), userId);

            log.info("리뷰 삭제 이벤트 처리 완료: 정비소ID={}", serviceCenterId);

        } catch (Exception e) {
            log.error("리뷰 삭제 이벤트 처리 중 오류 발생: 정비소ID={}, 오류={}", serviceCenterId, e.getMessage(), e);
            throw new BusinessException("평점 업데이트 중 오류가 발생했습니다: " + e.getMessage());
        }
    }

    /**
     * 정비소 평점 일괄 재계산 (데이터 정합성 복구용)
     */
    @Transactional
    public void recalculateAllRatings(Long adminUserId) {
        log.info("전체 정비소 평점 일괄 재계산 시작");

        try {
            List<ServiceCenter> serviceCenters = serviceCenterRepository.findAll();
            int processedCount = 0;
            int errorCount = 0;

            for (ServiceCenter serviceCenter : serviceCenters) {
                try {
                    recalculateServiceCenterRating(serviceCenter.getId(), adminUserId);
                    processedCount++;
                } catch (Exception e) {
                    log.error("정비소 평점 재계산 실패: ID={}, 오류={}", serviceCenter.getId(), e.getMessage());
                    errorCount++;
                }
            }

            log.info("전체 정비소 평점 일괄 재계산 완료: 처리={}, 오류={}", processedCount, errorCount);

        } catch (Exception e) {
            log.error("전체 평점 재계산 중 오류 발생: {}", e.getMessage(), e);
            throw new BusinessException("평점 일괄 재계산 중 오류가 발생했습니다: " + e.getMessage());
        }
    }

    /**
     * 특정 정비소 평점 재계산
     */
    @Transactional
    public void recalculateServiceCenterRating(Long serviceCenterId, Long userId) {
        log.info("정비소 평점 재계산 시작: 정비소ID={}", serviceCenterId);

        try {
            ServiceCenter serviceCenter = serviceCenterRepository.findById(serviceCenterId)
                .orElseThrow(() -> new BusinessException("정비소를 찾을 수 없습니다: " + serviceCenterId));

            BigDecimal previousRating = serviceCenter.getAverageRating();
            Integer previousReviewCount = serviceCenter.getReviewCount();

            // 모든 리뷰를 다시 조회하여 평점 재계산
            RatingUpdateResult updateResult = recalculateFromAllReviews(serviceCenterId);

            updateServiceCenterRating(serviceCenterId, updateResult, userId);

            recordRatingHistory(serviceCenterId, previousRating, previousReviewCount, 
                              updateResult, ServiceCenterRatingHistory.ChangeType.SYSTEM_RECALCULATION, 
                              null, "시스템 평점 재계산", userId);

            updateRatingStatistics(serviceCenterId, updateResult);

            log.info("정비소 평점 재계산 완료: 정비소ID={}, 이전평점={}, 신규평점={}", 
                    serviceCenterId, previousRating, updateResult.getNewRating());

        } catch (Exception e) {
            log.error("정비소 평점 재계산 중 오류 발생: 정비소ID={}, 오류={}", serviceCenterId, e.getMessage(), e);
            throw new BusinessException("평점 재계산 중 오류가 발생했습니다: " + e.getMessage());
        }
    }

    /**
     * 평점 통계 조회
     */
    public ServiceCenterRatingStatistics getRatingStatistics(Long serviceCenterId) {
        log.debug("평점 통계 조회: 정비소ID={}", serviceCenterId);

        // TODO: 실제 구현에서는 별도 통계 테이블에서 조회
        ServiceCenter serviceCenter = serviceCenterRepository.findById(serviceCenterId)
            .orElseThrow(() -> new BusinessException("정비소를 찾을 수 없습니다: " + serviceCenterId));

        // 임시로 기본 통계 정보 반환
        return ServiceCenterRatingStatistics.builder()
            .serviceCenterId(serviceCenterId)
            .currentRating(serviceCenter.getAverageRating())
            .totalReviewCount(serviceCenter.getReviewCount())
            .qualityLevel(ServiceCenterRatingStatistics.QualityLevel.fromScore(
                serviceCenter.getAverageRating().multiply(new BigDecimal("20"))))
            .lastCalculatedAt(LocalDateTime.now())
            .build();
    }

    // === 내부 메서드들 ===

    private RatingUpdateResult calculateNewRating(Long serviceCenterId, Integer newRating, RatingChangeType changeType) {
        // TODO: 실제 구현에서는 리뷰 테이블에서 모든 리뷰를 조회하여 계산
        // 현재는 간단한 계산으로 대체
        
        ServiceCenter serviceCenter = serviceCenterRepository.findById(serviceCenterId)
            .orElseThrow(() -> new BusinessException("정비소를 찾을 수 없습니다: " + serviceCenterId));

        BigDecimal currentRating = serviceCenter.getAverageRating();
        Integer currentReviewCount = serviceCenter.getReviewCount();

        BigDecimal newAverageRating;
        Integer newReviewCount;

        if (changeType == RatingChangeType.REVIEW_ADDED) {
            newReviewCount = currentReviewCount + 1;
            newAverageRating = currentRating.multiply(new BigDecimal(currentReviewCount))
                .add(new BigDecimal(newRating))
                .divide(new BigDecimal(newReviewCount), 2, RoundingMode.HALF_UP);
        } else if (changeType == RatingChangeType.REVIEW_DELETED) {
            newReviewCount = Math.max(0, currentReviewCount - 1);
            if (newReviewCount == 0) {
                newAverageRating = BigDecimal.ZERO;
            } else {
                newAverageRating = currentRating.multiply(new BigDecimal(currentReviewCount))
                    .subtract(new BigDecimal(Math.abs(newRating)))
                    .divide(new BigDecimal(newReviewCount), 2, RoundingMode.HALF_UP);
            }
        } else {
            newReviewCount = currentReviewCount;
            newAverageRating = currentRating; // 기본값
        }

        return RatingUpdateResult.builder()
            .newRating(newAverageRating)
            .newReviewCount(newReviewCount)
            .ratingChange(newAverageRating.subtract(currentRating))
            .reviewCountChange(newReviewCount - currentReviewCount)
            .calculationMethod(ServiceCenterRatingHistory.CalculationMethod.SIMPLE_AVERAGE)
            .build();
    }

    private RatingUpdateResult recalculateRatingAfterReviewUpdate(Long serviceCenterId, Integer oldRating, Integer newRating) {
        ServiceCenter serviceCenter = serviceCenterRepository.findById(serviceCenterId)
            .orElseThrow(() -> new BusinessException("정비소를 찾을 수 없습니다: " + serviceCenterId));

        BigDecimal currentRating = serviceCenter.getAverageRating();
        Integer reviewCount = serviceCenter.getReviewCount();

        // 기존 평점을 제거하고 새 평점을 추가
        BigDecimal totalScore = currentRating.multiply(new BigDecimal(reviewCount));
        totalScore = totalScore.subtract(new BigDecimal(oldRating)).add(new BigDecimal(newRating));
        
        BigDecimal updatedRating = totalScore.divide(new BigDecimal(reviewCount), 2, RoundingMode.HALF_UP);

        return RatingUpdateResult.builder()
            .newRating(updatedRating)
            .newReviewCount(reviewCount)
            .ratingChange(updatedRating.subtract(currentRating))
            .reviewCountChange(0)
            .calculationMethod(ServiceCenterRatingHistory.CalculationMethod.SIMPLE_AVERAGE)
            .build();
    }

    private RatingUpdateResult recalculateFromAllReviews(Long serviceCenterId) {
        // TODO: 실제 구현에서는 리뷰 테이블에서 모든 리뷰를 조회하여 정확히 계산
        // 현재는 기존 값 유지
        ServiceCenter serviceCenter = serviceCenterRepository.findById(serviceCenterId)
            .orElseThrow(() -> new BusinessException("정비소를 찾을 수 없습니다: " + serviceCenterId));

        return RatingUpdateResult.builder()
            .newRating(serviceCenter.getAverageRating())
            .newReviewCount(serviceCenter.getReviewCount())
            .ratingChange(BigDecimal.ZERO)
            .reviewCountChange(0)
            .calculationMethod(ServiceCenterRatingHistory.CalculationMethod.CUSTOM_ALGORITHM)
            .build();
    }

    private void updateServiceCenterRating(Long serviceCenterId, RatingUpdateResult result, Long userId) {
        int updateCount = serviceCenterRepository.updateRating(serviceCenterId, result.getNewRating(), result.getNewReviewCount());
        if (updateCount == 0) {
            throw new BusinessException("정비소 평점 업데이트에 실패했습니다: " + serviceCenterId);
        }
    }

    private void recordRatingHistory(Long serviceCenterId, BigDecimal previousRating, Integer previousReviewCount,
                                   RatingUpdateResult result, ServiceCenterRatingHistory.ChangeType changeType,
                                   Long relatedReviewId, String changeReason, Long userId) {
        // TODO: 실제 구현에서는 평점 히스토리 테이블에 저장
        log.debug("평점 히스토리 기록: 정비소ID={}, 변경타입={}, 이전평점={}, 신규평점={}", 
                serviceCenterId, changeType, previousRating, result.getNewRating());
    }

    private void updateRatingStatistics(Long serviceCenterId, RatingUpdateResult result) {
        // TODO: 실제 구현에서는 통계 테이블 업데이트
        log.debug("평점 통계 업데이트: 정비소ID={}", serviceCenterId);
    }

    private void publishRatingUpdateEvent(Long serviceCenterId, BigDecimal oldRating, BigDecimal newRating, Long userId) {
        // TODO: 실제 구현에서는 이벤트 발행 (캐시 무효화, 알림 등)
        log.debug("평점 업데이트 이벤트 발행: 정비소ID={}, 이전평점={}, 신규평점={}", 
                serviceCenterId, oldRating, newRating);
    }

    // === 헬퍼 클래스들 ===

    public enum RatingChangeType {
        REVIEW_ADDED, REVIEW_UPDATED, REVIEW_DELETED
    }

    @lombok.Data
    @lombok.Builder
    public static class RatingUpdateResult {
        private BigDecimal newRating;
        private Integer newReviewCount;
        private BigDecimal ratingChange;
        private Integer reviewCountChange;
        private ServiceCenterRatingHistory.CalculationMethod calculationMethod;
    }
} 