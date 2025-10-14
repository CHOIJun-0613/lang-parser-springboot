package com.carcare.domain.review.dto;

import lombok.Data;
import lombok.Builder;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import java.time.LocalDateTime;
import java.util.List;

/**
 * 리뷰 DTO 클래스들
 */
public class ReviewDto {

    /**
     * 리뷰 생성 요청 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class CreateRequest {
        private Long reservationId;
        private String reservationUuid;  // UUID로도 예약 조회 가능
        private Long serviceCenterId;    // 서비스 센터 ID
        private Integer rating;          // 전체 평점 (1-5)
        private String title;            // 리뷰 제목
        private String content;          // 리뷰 내용 (comment -> content로 변경)
        private String comment;          // 기존 호환성을 위해 유지
        private List<String> imageUrls;
        
        // 세부 평점
        private Integer serviceQuality;  // 서비스 품질 (1-5)
        private Integer priceValue;      // 가격 대비 만족도 (1-5)
        private Integer facilities;      // 시설 만족도 (1-5)
        private Integer waitTime;        // 대기시간 만족도 (1-5)
        
        // content가 있으면 comment로 설정 (후처리용)
        public String getComment() {
            return content != null ? content : comment;
        }
    }

    /**
     * 리뷰 수정 요청 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class UpdateRequest {
        private Integer rating;
        private String comment;
        private List<String> imageUrls;
    }

    /**
     * 리뷰 응답 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Response {
        private Long id;
        private String reviewUuid;
        private Long reservationId;
        private Integer rating;
        private String comment;
        private Boolean isVisible;
        private LocalDateTime createdAt;
        private LocalDateTime updatedAt;
        private List<String> imageUrls;
        
        // 연관 데이터
        private String userName;
        private String serviceCenterName;
        private List<ReviewReplyDto.Response> replies;
    }

    /**
     * 리뷰 목록 조회 요청 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class SearchRequest {
        private Long serviceCenterId;
        private Integer minRating;
        private Integer maxRating;
        private Boolean visibleOnly;
        private String sortBy; // created_at, rating
        private String sortOrder; // asc, desc
        private Integer page;
        private Integer size;
        private Integer offset; // calculated field
    }

    /**
     * 리뷰 통계 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Statistics {
        private Long serviceCenterId;
        private Double averageRating;
        private Long totalReviews;
        private Long rating5Count;
        private Long rating4Count;
        private Long rating3Count;
        private Long rating2Count;
        private Long rating1Count;
    }
} 