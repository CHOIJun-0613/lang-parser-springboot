package com.carcare.domain.quote.entity;

import lombok.Data;
import lombok.Builder;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import java.time.LocalDateTime;
import java.math.BigDecimal;

/**
 * 견적 항목 엔티티
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class QuoteItem {
    
    /**
     * 견적 항목 고유 ID
     */
    private Long id;
    
    /**
     * 견적서 ID
     */
    private Long quoteId;
    
    /**
     * 항목 타입
     */
    private QuoteItemType itemType;
    
    /**
     * 항목 설명
     */
    private String description;
    
    /**
     * 수량
     */
    private Integer quantity;
    
    /**
     * 단가
     */
    private BigDecimal unitPrice;
    
    /**
     * 총액
     */
    private BigDecimal totalPrice;
    
    /**
     * 보증기간 (개월)
     */
    private Integer warrantyPeriod;
    
    /**
     * 항목별 메모
     */
    private String notes;
    
    /**
     * 생성 일시
     */
    private LocalDateTime createdAt;
    
    /**
     * 견적 항목 타입 ENUM
     */
    public enum QuoteItemType {
        LABOR("공임비"),
        PART("부품비"),
        MATERIAL("소모품"),
        DIAGNOSTIC("진단비"),
        OTHER("기타");
        
        private final String description;
        
        QuoteItemType(String description) {
            this.description = description;
        }
        
        public String getDescription() {
            return description;
        }
    }
    
    /**
     * 총액 계산
     */
    public void calculateTotalPrice() {
        if (quantity != null && unitPrice != null) {
            this.totalPrice = unitPrice.multiply(BigDecimal.valueOf(quantity));
        }
    }
    
    /**
     * 유효성 검증
     */
    public boolean isValid() {
        return description != null && !description.trim().isEmpty() &&
               quantity != null && quantity > 0 &&
               unitPrice != null && unitPrice.compareTo(BigDecimal.ZERO) >= 0 &&
               itemType != null;
    }
    
    /**
     * 기본값 설정
     */
    public void setDefaults() {
        if (this.quantity == null) {
            this.quantity = 1;
        }
        if (this.unitPrice == null) {
            this.unitPrice = BigDecimal.ZERO;
        }
        if (this.totalPrice == null) {
            calculateTotalPrice();
        }
    }
} 