package com.carcare.domain.review.dto;

import lombok.Data;
import lombok.Builder;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import java.time.LocalDateTime;

/**
 * 리뷰 답글 DTO 클래스들
 */
public class ReviewReplyDto {

    /**
     * 리뷰 답글 생성 요청 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class CreateRequest {
        private Long reviewId;
        private String content;
    }

    /**
     * 리뷰 답글 수정 요청 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class UpdateRequest {
        private String content;
    }

    /**
     * 리뷰 답글 응답 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Response {
        private Long id;
        private Long reviewId;
        private Long authorId;
        private String content;
        private LocalDateTime createdAt;
        private LocalDateTime updatedAt;
        
        // 연관 데이터
        private String authorName;
        private String authorType;
    }
} 