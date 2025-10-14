package com.carcare.domain.review.entity;

import lombok.Data;
import lombok.Builder;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import java.time.LocalDateTime;
import java.util.List;

/**
 * 리뷰 엔티티
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Review {
    
    private Long id;
    private String reviewUuid;
    private Long reservationId;
    private Integer rating;
    private String comment;
    private Boolean isVisible;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    private String reviewImages; // JSON 형태로 저장되는 이미지 URL 배열
    
    // 연관 데이터
    private String userName;
    private String serviceCenterName;
    private List<ReviewReply> replies;
    
    /**
     * 리뷰 이미지 URL 리스트로 변환
     */
    public List<String> getImageList() {
        if (reviewImages == null || reviewImages.isEmpty()) {
            return List.of();
        }
        // JSON 배열 파싱 로직 (실제 구현시 ObjectMapper 사용)
        return List.of();
    }
    
    /**
     * 리뷰 이미지 URL 리스트를 JSON 문자열로 변환
     */
    public void setImageList(List<String> images) {
        if (images == null || images.isEmpty()) {
            this.reviewImages = null;
            return;
        }
        // JSON 배열 직렬화 로직 (실제 구현시 ObjectMapper 사용)
        this.reviewImages = images.toString();
    }
} 