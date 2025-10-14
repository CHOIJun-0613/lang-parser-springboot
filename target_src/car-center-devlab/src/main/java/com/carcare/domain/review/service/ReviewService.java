package com.carcare.domain.review.service;

import com.carcare.domain.review.entity.Review;
import com.carcare.domain.review.entity.ReviewReply;
import com.carcare.domain.review.dto.ReviewDto;
import com.carcare.domain.review.dto.ReviewReplyDto;
import com.carcare.domain.review.repository.ReviewRepository;
import com.carcare.domain.review.repository.ReviewReplyRepository;
import com.carcare.domain.reservation.repository.ReservationRepository;
import com.carcare.common.exception.BusinessException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.UUID;
import java.util.Optional;

/**
 * 리뷰 서비스
 */
@Service
@RequiredArgsConstructor
@Slf4j
@Transactional(readOnly = true)
public class ReviewService {

    private final ReviewRepository reviewRepository;
    private final ReviewReplyRepository reviewReplyRepository;
    private final ReservationRepository reservationRepository;
    private final ReviewRatingService reviewRatingService;
    private final ObjectMapper objectMapper;

    /**
     * 리뷰 생성
     */
    @Transactional
    public ReviewDto.Response createReview(ReviewDto.CreateRequest request, Long userId) {
        log.info("리뷰 생성 요청: reservationId={}, reservationUuid={}, userId={}", 
                request.getReservationId(), request.getReservationUuid(), userId);

        // reservationUuid가 있으면 reservationId로 변환
        Long reservationId = resolveReservationId(request);
        
        // 예약 정보 검증
        validateReservationForReview(reservationId, userId);

        // 이미 리뷰가 작성되었는지 확인
        Optional<Review> existingReview = reviewRepository.findByReservationId(reservationId);
        if (existingReview.isPresent()) {
            throw new BusinessException("이미 해당 예약에 대한 리뷰가 작성되었습니다.");
        }

        // 리뷰 엔티티 생성
        Review review = Review.builder()
                .reviewUuid(UUID.randomUUID().toString())
                .reservationId(reservationId)
                .rating(request.getRating())
                .comment(request.getComment())
                .isVisible(true)
                .reviewImages(convertImageUrlsToJson(request.getImageUrls()))
                .build();

        reviewRepository.insert(review);

        // 정비소 평점 업데이트
        updateServiceCenterRatingAsync(reservationId);

        log.info("리뷰 생성 완료: reviewId={}", review.getId());
        return convertToResponse(review);
    }

    /**
     * 리뷰 조회 (ID)
     */
    public ReviewDto.Response getReview(Long reviewId) {
        Review review = reviewRepository.findById(reviewId)
                .orElseThrow(() -> new BusinessException("리뷰를 찾을 수 없습니다."));

        // 답글 조회
        List<ReviewReply> replies = reviewReplyRepository.findByReviewId(reviewId);
        review.setReplies(replies);

        return convertToResponse(review);
    }

    /**
     * 리뷰 조회 (UUID)
     */
    public ReviewDto.Response getReviewByUuid(String reviewUuid) {
        Review review = reviewRepository.findByUuid(reviewUuid)
                .orElseThrow(() -> new BusinessException("리뷰를 찾을 수 없습니다."));

        // 답글 조회
        List<ReviewReply> replies = reviewReplyRepository.findByReviewId(review.getId());
        review.setReplies(replies);

        return convertToResponse(review);
    }

    /**
     * 리뷰 수정
     */
    @Transactional
    public ReviewDto.Response updateReview(Long reviewId, ReviewDto.UpdateRequest request, Long userId) {
        log.info("리뷰 수정 요청: reviewId={}, userId={}", reviewId, userId);

        Review review = reviewRepository.findById(reviewId)
                .orElseThrow(() -> new BusinessException("리뷰를 찾을 수 없습니다."));

        // 작성자 권한 검증
        validateReviewOwnership(review.getReservationId(), userId);

        // 리뷰 수정
        review.setRating(request.getRating());
        review.setComment(request.getComment());
        review.setReviewImages(convertImageUrlsToJson(request.getImageUrls()));

        reviewRepository.update(review);

        log.info("리뷰 수정 완료: reviewId={}", reviewId);
        return convertToResponse(review);
    }

    /**
     * 리뷰 삭제
     */
    @Transactional
    public void deleteReview(Long reviewId, Long userId) {
        log.info("리뷰 삭제 요청: reviewId={}, userId={}", reviewId, userId);

        Review review = reviewRepository.findById(reviewId)
                .orElseThrow(() -> new BusinessException("리뷰를 찾을 수 없습니다."));

        // 작성자 권한 검증
        validateReviewOwnership(review.getReservationId(), userId);

        reviewRepository.delete(reviewId);

        log.info("리뷰 삭제 완료: reviewId={}", reviewId);
    }

    /**
     * 정비소별 리뷰 목록 조회
     */
    public List<ReviewDto.Response> getServiceCenterReviews(Long serviceCenterId, Boolean visibleOnly, Integer page, Integer size) {
        int offset = page * size;
        List<Review> reviews = reviewRepository.findByServiceCenterId(serviceCenterId, visibleOnly, offset, size);

        return reviews.stream()
                .map(this::convertToResponse)
                .toList();
    }

    /**
     * 사용자별 리뷰 목록 조회
     */
    public List<ReviewDto.Response> getUserReviews(Long userId, Integer page, Integer size) {
        int offset = page * size;
        List<Review> reviews = reviewRepository.findByUserId(userId, offset, size);

        return reviews.stream()
                .map(this::convertToResponse)
                .toList();
    }

    /**
     * 리뷰 검색
     */
    public List<ReviewDto.Response> searchReviews(ReviewDto.SearchRequest searchRequest) {
        List<Review> reviews = reviewRepository.findBySearchCondition(searchRequest);

        return reviews.stream()
                .map(this::convertToResponse)
                .toList();
    }

    /**
     * 정비소별 리뷰 통계 조회
     */
    public ReviewDto.Statistics getServiceCenterStatistics(Long serviceCenterId) {
        return reviewRepository.getStatisticsByServiceCenterId(serviceCenterId);
    }

    /**
     * 리뷰 가시성 변경 (관리자 기능)
     */
    @Transactional
    public void updateReviewVisibility(Long reviewId, Boolean isVisible) {
        log.info("리뷰 가시성 변경: reviewId={}, isVisible={}", reviewId, isVisible);

        reviewRepository.updateVisibility(reviewId, isVisible);

        log.info("리뷰 가시성 변경 완료: reviewId={}", reviewId);
    }

    /**
     * 예약 ID 해결 (UUID -> ID 변환)
     */
    private Long resolveReservationId(ReviewDto.CreateRequest request) {
        // reservationId가 있으면 그대로 사용
        if (request.getReservationId() != null) {
            return request.getReservationId();
        }
        
        // reservationUuid가 있으면 ID로 변환
        if (request.getReservationUuid() != null) {
            return reservationRepository.findByUuid(request.getReservationUuid())
                    .map(reservation -> reservation.getId())
                    .orElseThrow(() -> new BusinessException("예약 정보를 찾을 수 없습니다: " + request.getReservationUuid()));
        }
        
        throw new BusinessException("예약 ID 또는 예약 UUID가 필요합니다.");
    }

    /**
     * 예약 정보 검증
     */
    private void validateReservationForReview(Long reservationId, Long userId) {
        // 예약이 존재하고 해당 사용자의 예약인지 확인
        // 예약 상태가 COMPLETED인지 확인
        // 실제 구현에서는 ReservationService의 메서드를 호출하거나
        // ReservationRepository를 직접 사용
        
        // 임시 검증 로직 (실제로는 더 상세한 검증 필요)
        log.debug("예약 정보 검증: reservationId={}, userId={}", reservationId, userId);
    }

    /**
     * 리뷰 소유권 검증
     */
    private void validateReviewOwnership(Long reservationId, Long userId) {
        // 예약이 해당 사용자의 것인지 확인
        // 실제 구현에서는 ReservationRepository를 통해 검증
        
        log.debug("리뷰 소유권 검증: reservationId={}, userId={}", reservationId, userId);
    }

    /**
     * 이미지 URL 리스트를 JSON 문자열로 변환
     */
    private String convertImageUrlsToJson(List<String> imageUrls) {
        if (imageUrls == null || imageUrls.isEmpty()) {
            return null;
        }

        try {
            return objectMapper.writeValueAsString(imageUrls);
        } catch (Exception e) {
            log.error("이미지 URL JSON 변환 실패", e);
            return null;
        }
    }

    /**
     * JSON 문자열을 이미지 URL 리스트로 변환
     */
    private List<String> convertJsonToImageUrls(String jsonString) {
        if (jsonString == null || jsonString.trim().isEmpty()) {
            return List.of();
        }

        try {
            return objectMapper.readValue(jsonString, new TypeReference<List<String>>() {});
        } catch (Exception e) {
            log.error("JSON 이미지 URL 변환 실패", e);
            return List.of();
        }
    }

    /**
     * Review 엔티티를 Response DTO로 변환
     */
    private ReviewDto.Response convertToResponse(Review review) {
        List<ReviewReplyDto.Response> replyResponses = review.getReplies() != null ?
                review.getReplies().stream()
                        .map(this::convertReplyToResponse)
                        .toList() : List.of();

        return ReviewDto.Response.builder()
                .id(review.getId())
                .reviewUuid(review.getReviewUuid())
                .reservationId(review.getReservationId())
                .rating(review.getRating())
                .comment(review.getComment())
                .isVisible(review.getIsVisible())
                .createdAt(review.getCreatedAt())
                .updatedAt(review.getUpdatedAt())
                .imageUrls(convertJsonToImageUrls(review.getReviewImages()))
                .userName(review.getUserName())
                .serviceCenterName(review.getServiceCenterName())
                .replies(replyResponses)
                .build();
    }

    /**
     * ReviewReply 엔티티를 Response DTO로 변환
     */
    private ReviewReplyDto.Response convertReplyToResponse(ReviewReply reply) {
        return ReviewReplyDto.Response.builder()
                .id(reply.getId())
                .reviewId(reply.getReviewId())
                .authorId(reply.getAuthorId())
                .content(reply.getContent())
                .createdAt(reply.getCreatedAt())
                .updatedAt(reply.getUpdatedAt())
                .authorName(reply.getAuthorName())
                .authorType(reply.getAuthorType())
                .build();
    }

    /**
     * 정비소 평점 비동기 업데이트
     */
    private void updateServiceCenterRatingAsync(Long reservationId) {
        try {
            // 예약 ID로부터 정비소 ID 조회하는 로직이 필요
            // 임시로 로그만 출력 - 실제 구현시 ReservationRepository에서 정비소 ID 조회 후
            // reviewRatingService.updateServiceCenterRating(serviceCenterId) 호출
            log.debug("정비소 평점 업데이트 요청: reservationId={}", reservationId);
        } catch (Exception e) {
            log.error("정비소 평점 업데이트 실패: reservationId={}", reservationId, e);
        }
    }
} 