package com.carcare.domain.quote.entity;

import lombok.Data;
import lombok.Builder;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import java.time.LocalDateTime;

/**
 * 견적서 상태 변경 이력 엔티티
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class QuoteStatusHistory {
    
    /**
     * 이력 고유 ID
     */
    private Long id;
    
    /**
     * 견적서 ID
     */
    private Long quoteId;
    
    /**
     * 이전 상태
     */
    private Quote.QuoteStatus fromStatus;
    
    /**
     * 변경된 상태
     */
    private Quote.QuoteStatus toStatus;
    
    /**
     * 변경 사유
     */
    private String reason;
    
    /**
     * 변경자 정보 (사용자 ID 또는 시스템)
     */
    private String changedBy;
    
    /**
     * 변경 일시
     */
    private LocalDateTime changedAt;
    
    /**
     * 추가 메모
     */
    private String notes;
} 