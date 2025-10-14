package com.carcare.domain.quote.dto;

import com.carcare.domain.quote.entity.QuoteItem;
import lombok.Data;
import lombok.Builder;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.*;

import java.time.LocalDateTime;
import java.math.BigDecimal;

/**
 * 견적 항목 DTO 클래스
 */
public class QuoteItemDto {

    /**
     * 견적 항목 생성 요청 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "견적 항목 생성 요청")
    public static class CreateRequest {
        
        @NotNull(message = "항목 타입은 필수입니다")
        @Schema(description = "항목 타입", example = "LABOR")
        private QuoteItem.QuoteItemType itemType;
        
        @NotBlank(message = "항목 설명은 필수입니다")
        @Size(max = 500, message = "설명은 500자를 초과할 수 없습니다")
        @Schema(description = "항목 설명", example = "엔진 점검 공임비")
        private String description;
        
        @Min(value = 1, message = "수량은 1 이상이어야 합니다")
        @Schema(description = "수량", example = "1")
        private Integer quantity;
        
        @NotNull(message = "단가는 필수입니다")
        @DecimalMin(value = "0.0", message = "단가는 0 이상이어야 합니다")
        @Schema(description = "단가", example = "50000.00")
        private BigDecimal unitPrice;
        
        @Min(value = 0, message = "보증기간은 0 이상이어야 합니다")
        @Schema(description = "보증기간 (개월)", example = "12")
        private Integer warrantyPeriod;
        
        @Size(max = 500, message = "메모는 500자를 초과할 수 없습니다")
        @Schema(description = "항목별 메모", example = "순정 부품 사용")
        private String notes;
    }

    /**
     * 견적 항목 수정 요청 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "견적 항목 수정 요청")
    public static class UpdateRequest {
        
        @NotNull(message = "항목 타입은 필수입니다")
        @Schema(description = "항목 타입", example = "PART")
        private QuoteItem.QuoteItemType itemType;
        
        @NotBlank(message = "항목 설명은 필수입니다")
        @Size(max = 500, message = "설명은 500자를 초과할 수 없습니다")
        @Schema(description = "항목 설명", example = "브레이크 패드 교체")
        private String description;
        
        @Min(value = 1, message = "수량은 1 이상이어야 합니다")
        @Schema(description = "수량", example = "2")
        private Integer quantity;
        
        @NotNull(message = "단가는 필수입니다")
        @DecimalMin(value = "0.0", message = "단가는 0 이상이어야 합니다")
        @Schema(description = "단가", example = "75000.00")
        private BigDecimal unitPrice;
        
        @Min(value = 0, message = "보증기간은 0 이상이어야 합니다")
        @Schema(description = "보증기간 (개월)", example = "6")
        private Integer warrantyPeriod;
        
        @Size(max = 500, message = "메모는 500자를 초과할 수 없습니다")
        @Schema(description = "항목별 메모", example = "고품질 브레이크 패드")
        private String notes;
    }

    /**
     * 견적 항목 응답 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "견적 항목 응답")
    public static class Response {
        
        @Schema(description = "견적 항목 ID", example = "1")
        private Long id;
        
        @Schema(description = "견적서 ID", example = "1")
        private Long quoteId;
        
        @Schema(description = "항목 타입", example = "LABOR")
        private QuoteItem.QuoteItemType itemType;
        
        @Schema(description = "항목 설명", example = "엔진 점검 공임비")
        private String description;
        
        @Schema(description = "수량", example = "1")
        private Integer quantity;
        
        @Schema(description = "단가", example = "50000.00")
        private BigDecimal unitPrice;
        
        @Schema(description = "총액", example = "50000.00")
        private BigDecimal totalPrice;
        
        @Schema(description = "보증기간 (개월)", example = "12")
        private Integer warrantyPeriod;
        
        @Schema(description = "항목별 메모", example = "순정 부품 사용")
        private String notes;
        
        @Schema(description = "생성 일시", example = "2024-01-10T09:00:00")
        private LocalDateTime createdAt;
    }
} 