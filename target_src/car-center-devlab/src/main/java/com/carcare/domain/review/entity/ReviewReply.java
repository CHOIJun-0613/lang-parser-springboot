package com.carcare.domain.review.entity;

import lombok.Data;
import lombok.Builder;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import java.time.LocalDateTime;

/**
 * 리뷰 답글 엔티티
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ReviewReply {
    
    private Long id;
    private Long reviewId;
    private Long authorId;
    private String content;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    
    // 연관 데이터
    private String authorName;
    private String authorType; // SERVICE_CENTER, ADMIN 등
} 