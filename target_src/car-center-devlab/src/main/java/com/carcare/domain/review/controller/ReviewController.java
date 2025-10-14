package com.carcare.domain.review.controller;

import com.carcare.domain.review.service.ReviewService;
import com.carcare.domain.review.service.ReviewReplyService;
import com.carcare.domain.review.dto.ReviewDto;
import com.carcare.domain.review.dto.ReviewReplyDto;
import com.carcare.common.dto.ApiResponse;
import com.carcare.common.util.ResponseUtils;
import com.carcare.config.JwtAuthenticationFilter.JwtUserPrincipal;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.*;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;

import jakarta.validation.Valid;
import java.util.List;

/**
 * 리뷰 관리 컨트롤러
 */
@RestController
@RequestMapping("/api/v1/reviews")
@Tag(name = "Review", description = "리뷰 관리 API")
@RequiredArgsConstructor
@Slf4j
public class ReviewController {
    
    private final ReviewService reviewService;
    private final ReviewReplyService reviewReplyService;

    /**
     * SecurityContext에서 현재 사용자 ID 추출
     */
    private Long getCurrentUserId() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication != null && authentication.getPrincipal() instanceof JwtUserPrincipal) {
            JwtUserPrincipal userPrincipal = (JwtUserPrincipal) authentication.getPrincipal();
            return userPrincipal.getUserId();
        }
        throw new RuntimeException("인증된 사용자 정보를 찾을 수 없습니다.");
    }

    /**
     * 리뷰 생성
     */
    @PostMapping
    @Operation(summary = "리뷰 생성", description = "예약에 대한 리뷰를 작성합니다.")
    public ResponseEntity<ApiResponse<ReviewDto.Response>> createReview(
            @Valid @RequestBody ReviewDto.CreateRequest request) {
        
        Long userId = getCurrentUserId();
        ReviewDto.Response response = reviewService.createReview(request, userId);
        
        return ResponseEntity.ok(ResponseUtils.success("리뷰 생성이 완료되었습니다.", response));
    }

    /**
     * 리뷰 조회 (ID)
     */
    @GetMapping("/{reviewId}")
    @Operation(summary = "리뷰 조회", description = "리뷰 ID로 리뷰 상세 정보를 조회합니다.")
    public ResponseEntity<ApiResponse<ReviewDto.Response>> getReview(
            @Parameter(description = "리뷰 ID") @PathVariable Long reviewId) {
        
        ReviewDto.Response response = reviewService.getReview(reviewId);
        
        return ResponseEntity.ok(ResponseUtils.success("리뷰 조회가 완료되었습니다.", response));
    }

    /**
     * 리뷰 조회 (UUID)
     */
    @GetMapping("/uuid/{reviewUuid}")
    @Operation(summary = "리뷰 조회 (UUID)", description = "리뷰 UUID로 리뷰 상세 정보를 조회합니다.")
    public ResponseEntity<ApiResponse<ReviewDto.Response>> getReviewByUuid(
            @Parameter(description = "리뷰 UUID") @PathVariable String reviewUuid) {
        
        ReviewDto.Response response = reviewService.getReviewByUuid(reviewUuid);
        
        return ResponseEntity.ok(ResponseUtils.success("리뷰 조회가 완료되었습니다.", response));
    }

    /**
     * 리뷰 수정
     */
    @PutMapping("/{reviewId}")
    @Operation(summary = "리뷰 수정", description = "리뷰 내용을 수정합니다.")
    public ResponseEntity<ApiResponse<ReviewDto.Response>> updateReview(
            @Parameter(description = "리뷰 ID") @PathVariable Long reviewId,
            @Valid @RequestBody ReviewDto.UpdateRequest request) {
        
        Long userId = getCurrentUserId();
        ReviewDto.Response response = reviewService.updateReview(reviewId, request, userId);
        
        return ResponseEntity.ok(ResponseUtils.success("리뷰 수정이 완료되었습니다.", response));
    }

    /**
     * 리뷰 삭제
     */
    @DeleteMapping("/{reviewId}")
    @Operation(summary = "리뷰 삭제", description = "리뷰를 삭제합니다.")
    public ResponseEntity<ApiResponse<Void>> deleteReview(
            @Parameter(description = "리뷰 ID") @PathVariable Long reviewId) {
        
        Long userId = getCurrentUserId();
        reviewService.deleteReview(reviewId, userId);
        
        return ResponseEntity.ok(ResponseUtils.success("리뷰 삭제가 완료되었습니다."));
    }

    /**
     * 정비소별 리뷰 목록 조회
     */
    @GetMapping("/service-center/{serviceCenterId}")
    @Operation(summary = "정비소별 리뷰 목록", description = "특정 정비소의 리뷰 목록을 조회합니다.")
    public ResponseEntity<ApiResponse<List<ReviewDto.Response>>> getServiceCenterReviews(
            @Parameter(description = "정비소 ID") @PathVariable Long serviceCenterId,
            @Parameter(description = "공개된 리뷰만 조회") @RequestParam(defaultValue = "true") Boolean visibleOnly,
            @Parameter(description = "페이지 번호 (0부터 시작)") @RequestParam(defaultValue = "0") Integer page,
            @Parameter(description = "페이지 크기") @RequestParam(defaultValue = "10") Integer size) {
        
        List<ReviewDto.Response> reviews = reviewService.getServiceCenterReviews(serviceCenterId, visibleOnly, page, size);
        
        return ResponseEntity.ok(ResponseUtils.success("정비소 리뷰 목록 조회가 완료되었습니다.", reviews));
    }

    /**
     * 사용자별 리뷰 목록 조회
     */
    @GetMapping("/my")
    @Operation(summary = "내 리뷰 목록", description = "로그인한 사용자의 리뷰 목록을 조회합니다.")
    public ResponseEntity<ApiResponse<List<ReviewDto.Response>>> getMyReviews(
            @Parameter(description = "페이지 번호 (0부터 시작)") @RequestParam(defaultValue = "0") Integer page,
            @Parameter(description = "페이지 크기") @RequestParam(defaultValue = "10") Integer size) {
        
        Long userId = getCurrentUserId();
        List<ReviewDto.Response> reviews = reviewService.getUserReviews(userId, page, size);
        
        return ResponseEntity.ok(ResponseUtils.success("내 리뷰 목록 조회가 완료되었습니다.", reviews));
    }

    /**
     * 리뷰 검색
     */
    @GetMapping("/search")
    @Operation(summary = "리뷰 검색", description = "다양한 조건으로 리뷰를 검색합니다.")
    public ResponseEntity<ApiResponse<List<ReviewDto.Response>>> searchReviews(
            @Parameter(description = "정비소 ID") @RequestParam(required = false) Long serviceCenterId,
            @Parameter(description = "최소 평점") @RequestParam(required = false) Integer minRating,
            @Parameter(description = "최대 평점") @RequestParam(required = false) Integer maxRating,
            @Parameter(description = "공개된 리뷰만 조회") @RequestParam(defaultValue = "true") Boolean visibleOnly,
            @Parameter(description = "정렬 기준 (created_at, rating)") @RequestParam(defaultValue = "created_at") String sortBy,
            @Parameter(description = "정렬 순서 (asc, desc)") @RequestParam(defaultValue = "desc") String sortOrder,
            @Parameter(description = "페이지 번호 (0부터 시작)") @RequestParam(defaultValue = "0") Integer page,
            @Parameter(description = "페이지 크기") @RequestParam(defaultValue = "10") Integer size) {
        
        ReviewDto.SearchRequest searchRequest = ReviewDto.SearchRequest.builder()
                .serviceCenterId(serviceCenterId)
                .minRating(minRating)
                .maxRating(maxRating)
                .visibleOnly(visibleOnly)
                .sortBy(sortBy)
                .sortOrder(sortOrder)
                .page(page)
                .size(size)
                .offset(page * size)
                .build();
        
        List<ReviewDto.Response> reviews = reviewService.searchReviews(searchRequest);
        
        return ResponseEntity.ok(ResponseUtils.success("리뷰 검색이 완료되었습니다.", reviews));
    }

    /**
     * 정비소별 리뷰 통계 조회
     */
    @GetMapping("/statistics/service-center/{serviceCenterId}")
    @Operation(summary = "정비소 리뷰 통계", description = "특정 정비소의 리뷰 통계를 조회합니다.")
    public ResponseEntity<ApiResponse<ReviewDto.Statistics>> getServiceCenterStatistics(
            @Parameter(description = "정비소 ID") @PathVariable Long serviceCenterId) {
        
        ReviewDto.Statistics statistics = reviewService.getServiceCenterStatistics(serviceCenterId);
        
        return ResponseEntity.ok(ResponseUtils.success("정비소 리뷰 통계 조회가 완료되었습니다.", statistics));
    }

    /**
     * 리뷰 가시성 변경 (관리자 기능)
     */
    @PatchMapping("/{reviewId}/visibility")
    @Operation(summary = "리뷰 가시성 변경", description = "리뷰의 공개/비공개 상태를 변경합니다. (관리자 전용)")
    public ResponseEntity<ApiResponse<Void>> updateReviewVisibility(
            @Parameter(description = "리뷰 ID") @PathVariable Long reviewId,
            @Parameter(description = "가시성 변경 요청") @RequestBody VisibilityUpdateRequest request) {
        
        reviewService.updateReviewVisibility(reviewId, request.isVisible);
        
        return ResponseEntity.ok(ResponseUtils.success("리뷰 가시성 변경이 완료되었습니다."));
    }

    /**
     * 가시성 변경 요청 DTO
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class VisibilityUpdateRequest {
        @Parameter(description = "공개 여부")
        private Boolean isVisible;
    }

    // ========== 리뷰 답글 관련 API ==========

    /**
     * 리뷰 답글 생성
     */
    @PostMapping("/{reviewId}/replies")
    @Operation(summary = "리뷰 답글 작성", description = "리뷰에 답글을 작성합니다.")
    public ResponseEntity<ApiResponse<ReviewReplyDto.Response>> createReply(
            @Parameter(description = "리뷰 ID") @PathVariable Long reviewId,
            @Valid @RequestBody ReviewReplyDto.CreateRequest request) {
        
        Long authorId = getCurrentUserId();
        request.setReviewId(reviewId); // PathVariable로 받은 reviewId 설정
        
        ReviewReplyDto.Response response = reviewReplyService.createReply(request, authorId);
        
        return ResponseEntity.ok(ResponseUtils.success("리뷰 답글 작성이 완료되었습니다.", response));
    }

    /**
     * 리뷰별 답글 목록 조회
     */
    @GetMapping("/{reviewId}/replies")
    @Operation(summary = "리뷰 답글 목록", description = "특정 리뷰의 답글 목록을 조회합니다.")
    public ResponseEntity<ApiResponse<List<ReviewReplyDto.Response>>> getReviewReplies(
            @Parameter(description = "리뷰 ID") @PathVariable Long reviewId) {
        
        List<ReviewReplyDto.Response> replies = reviewReplyService.getReviewReplies(reviewId);
        
        return ResponseEntity.ok(ResponseUtils.success("리뷰 답글 목록 조회가 완료되었습니다.", replies));
    }

    /**
     * 리뷰 답글 수정
     */
    @PutMapping("/replies/{replyId}")
    @Operation(summary = "리뷰 답글 수정", description = "리뷰 답글을 수정합니다.")
    public ResponseEntity<ApiResponse<ReviewReplyDto.Response>> updateReply(
            @Parameter(description = "답글 ID") @PathVariable Long replyId,
            @Valid @RequestBody ReviewReplyDto.UpdateRequest request) {
        
        Long authorId = getCurrentUserId();
        ReviewReplyDto.Response response = reviewReplyService.updateReply(replyId, request, authorId);
        
        return ResponseEntity.ok(ResponseUtils.success("리뷰 답글 수정이 완료되었습니다.", response));
    }

    /**
     * 리뷰 답글 삭제
     */
    @DeleteMapping("/replies/{replyId}")
    @Operation(summary = "리뷰 답글 삭제", description = "리뷰 답글을 삭제합니다.")
    public ResponseEntity<ApiResponse<Void>> deleteReply(
            @Parameter(description = "답글 ID") @PathVariable Long replyId) {
        
        Long authorId = getCurrentUserId();
        reviewReplyService.deleteReply(replyId, authorId);
        
        return ResponseEntity.ok(ResponseUtils.success("리뷰 답글 삭제가 완료되었습니다."));
    }

    /**
     * 내 답글 목록 조회
     */
    @GetMapping("/replies/my")
    @Operation(summary = "내 답글 목록", description = "로그인한 사용자가 작성한 답글 목록을 조회합니다.")
    public ResponseEntity<ApiResponse<List<ReviewReplyDto.Response>>> getMyReplies(
            @Parameter(description = "페이지 번호 (0부터 시작)") @RequestParam(defaultValue = "0") Integer page,
            @Parameter(description = "페이지 크기") @RequestParam(defaultValue = "10") Integer size) {
        
        Long authorId = getCurrentUserId();
        List<ReviewReplyDto.Response> replies = reviewReplyService.getAuthorReplies(authorId, page, size);
        
        return ResponseEntity.ok(ResponseUtils.success("내 답글 목록 조회가 완료되었습니다.", replies));
    }
} 