package com.carcare.domain.quote.entity;

import lombok.Data;
import lombok.Builder;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.math.BigDecimal;
import java.util.UUID;
import java.util.List;

/**
 * 견적서 엔티티
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Quote {
    
    /**
     * 견적서 고유 ID
     */
    private Long id;
    
    /**
     * 견적서 UUID (외부 참조용)
     */
    private UUID quoteUuid;
    
    /**
     * 예약 ID
     */
    private Long reservationId;
    
    /**
     * 공임비
     */
    private BigDecimal laborCost;
    
    /**
     * 부품비
     */
    private BigDecimal partsCost;
    
    /**
     * 세금
     */
    private BigDecimal taxAmount;
    
    /**
     * 할인금액
     */
    private BigDecimal discountAmount;
    
    /**
     * 총액
     */
    private BigDecimal totalAmount;
    
    /**
     * 견적서 상태
     */
    private QuoteStatus status;
    
    /**
     * 견적 유효기간
     */
    private LocalDateTime validUntil;
    
    /**
     * 견적 관련 메모
     */
    private String notes;
    
    /**
     * 승인 시간
     */
    private OffsetDateTime approvedAt;
    
    /**
     * 거절 시간
     */
    private OffsetDateTime rejectedAt;
    
    /**
     * 거절 사유
     */
    private String rejectionReason;
    
    /**
     * 생성 일시
     */
    private LocalDateTime createdAt;
    
    /**
     * 수정 일시
     */
    private LocalDateTime updatedAt;
    
    /**
     * 견적 항목 목록 (조인 시 사용)
     */
    private List<QuoteItem> quoteItems;
    
    /**
     * 견적서 상태 ENUM
     */
    public enum QuoteStatus {
        DRAFT("임시저장"),
        PENDING("발송됨"),
        APPROVED("승인됨"),
        REJECTED("거절됨"),
        EXPIRED("만료됨");
        
        private final String description;
        
        QuoteStatus(String description) {
            this.description = description;
        }
        
        public String getDescription() {
            return description;
        }
    }
    
    /**
     * 견적서 승인 여부 확인
     */
    public boolean isApproved() {
        return status == QuoteStatus.APPROVED;
    }
    
    /**
     * 견적서 거절 여부 확인
     */
    public boolean isRejected() {
        return status == QuoteStatus.REJECTED;
    }
    
    /**
     * 견적서 유효 여부 확인
     */
    public boolean isValid() {
        return validUntil != null && LocalDateTime.now().isBefore(validUntil) && 
               status != QuoteStatus.EXPIRED && status != QuoteStatus.REJECTED;
    }
    
    /**
     * 수정 가능 여부 확인
     */
    public boolean isEditable() {
        return status == QuoteStatus.DRAFT;
    }
    
    /**
     * 견적서 상태 변경 메서드
     */
    public void approve() {
        if (!isValid()) {
            throw new IllegalStateException("유효하지 않은 견적서는 승인할 수 없습니다.");
        }
        if (status != QuoteStatus.PENDING) {
            throw new IllegalStateException("발송된 견적서만 승인할 수 있습니다.");
        }
        this.status = QuoteStatus.APPROVED;
        this.approvedAt = OffsetDateTime.now();
    }
    
    public void reject(String reason) {
        if (status == QuoteStatus.APPROVED) {
            throw new IllegalStateException("승인된 견적서는 거절할 수 없습니다.");
        }
        this.status = QuoteStatus.REJECTED;
        this.rejectionReason = reason;
        this.rejectedAt = OffsetDateTime.now();
    }
    
    public void send() {
        if (status != QuoteStatus.DRAFT) {
            throw new IllegalStateException("임시저장 상태의 견적서만 발송할 수 있습니다.");
        }
        if (totalAmount == null || totalAmount.compareTo(BigDecimal.ZERO) <= 0) {
            throw new IllegalStateException("견적 금액이 유효하지 않습니다.");
        }
        this.status = QuoteStatus.PENDING;
    }
    
    public void expire() {
        if (status == QuoteStatus.APPROVED || status == QuoteStatus.REJECTED) {
            throw new IllegalStateException("승인되거나 거절된 견적서는 만료시킬 수 없습니다.");
        }
        this.status = QuoteStatus.EXPIRED;
    }
    
    /**
     * 기본값 설정
     */
    public void setDefaults() {
        if (this.quoteUuid == null) {
            this.quoteUuid = UUID.randomUUID();
        }
        if (this.status == null) {
            this.status = QuoteStatus.DRAFT;
        }
        if (this.laborCost == null) {
            this.laborCost = BigDecimal.ZERO;
        }
        if (this.partsCost == null) {
            this.partsCost = BigDecimal.ZERO;
        }
        if (this.taxAmount == null) {
            this.taxAmount = BigDecimal.ZERO;
        }
        if (this.discountAmount == null) {
            this.discountAmount = BigDecimal.ZERO;
        }
        if (this.totalAmount == null) {
            this.totalAmount = BigDecimal.ZERO;
        }
    }
} 