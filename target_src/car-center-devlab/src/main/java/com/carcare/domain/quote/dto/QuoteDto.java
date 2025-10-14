package com.carcare.domain.quote.dto;

import com.carcare.domain.quote.entity.Quote;
import com.carcare.domain.quote.entity.QuoteItem;
import lombok.Data;
import lombok.Builder;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.*;

import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.math.BigDecimal;
import java.util.List;
import java.util.UUID;

/**
 * 견적서 DTO 클래스
 */
public class QuoteDto {

    /**
     * 견적서 생성 요청 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "견적서 생성 요청")
    public static class CreateRequest {
        
        @NotNull(message = "예약 ID는 필수입니다")
        @Schema(description = "예약 ID", example = "1")
        private Long reservationId;
        
        @Schema(description = "공임비", example = "100000.00")
        private BigDecimal laborCost;
        
        @Schema(description = "부품비", example = "200000.00")
        private BigDecimal partsCost;
        
        @Schema(description = "세금", example = "30000.00")
        private BigDecimal taxAmount;
        
        @Schema(description = "할인금액", example = "10000.00")
        private BigDecimal discountAmount;
        
        @Future(message = "유효기간은 현재 시간 이후여야 합니다")
        @Schema(description = "견적 유효기간", example = "2024-12-31T23:59:59")
        private LocalDateTime validUntil;
        
        @Size(max = 1000, message = "메모는 1000자를 초과할 수 없습니다")
        @Schema(description = "견적 관련 메모", example = "엔진 점검 관련 견적서입니다.")
        private String notes;
        
        @Schema(description = "견적 항목 목록")
        private List<QuoteItemDto.CreateRequest> items;
    }

    /**
     * 견적서 수정 요청 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "견적서 수정 요청")
    public static class UpdateRequest {
        
        @Schema(description = "공임비", example = "120000.00")
        private BigDecimal laborCost;
        
        @Schema(description = "부품비", example = "250000.00")
        private BigDecimal partsCost;
        
        @Schema(description = "세금", example = "37000.00")
        private BigDecimal taxAmount;
        
        @Schema(description = "할인금액", example = "15000.00")
        private BigDecimal discountAmount;
        
        @Future(message = "유효기간은 현재 시간 이후여야 합니다")
        @Schema(description = "견적 유효기간", example = "2024-12-31T23:59:59")
        private LocalDateTime validUntil;
        
        @Size(max = 1000, message = "메모는 1000자를 초과할 수 없습니다")
        @Schema(description = "견적 관련 메모", example = "수정된 견적서입니다.")
        private String notes;
    }

    /**
     * 견적서 응답 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "견적서 응답")
    public static class Response {
        
        @Schema(description = "견적서 ID", example = "1")
        private Long id;
        
        @Schema(description = "견적서 UUID", example = "550e8400-e29b-41d4-a716-446655440000")
        private UUID quoteUuid;
        
        @Schema(description = "예약 ID", example = "1")
        private Long reservationId;
        
        @Schema(description = "공임비", example = "100000.00")
        private BigDecimal laborCost;
        
        @Schema(description = "부품비", example = "200000.00")
        private BigDecimal partsCost;
        
        @Schema(description = "세금", example = "30000.00")
        private BigDecimal taxAmount;
        
        @Schema(description = "할인금액", example = "10000.00")
        private BigDecimal discountAmount;
        
        @Schema(description = "총액", example = "320000.00")
        private BigDecimal totalAmount;
        
        @Schema(description = "견적서 상태", example = "DRAFT")
        private Quote.QuoteStatus status;
        
        @Schema(description = "견적 유효기간", example = "2024-12-31T23:59:59")
        private LocalDateTime validUntil;
        
        @Schema(description = "견적 관련 메모", example = "엔진 점검 관련 견적서입니다.")
        private String notes;
        
        @Schema(description = "승인 시간", example = "2024-01-15T10:30:00+09:00")
        private OffsetDateTime approvedAt;
        
        @Schema(description = "거절 시간", example = "2024-01-15T10:30:00+09:00")
        private OffsetDateTime rejectedAt;
        
        @Schema(description = "거절 사유", example = "가격이 너무 높습니다.")
        private String rejectionReason;
        
        @Schema(description = "생성 일시", example = "2024-01-10T09:00:00")
        private LocalDateTime createdAt;
        
        @Schema(description = "수정 일시", example = "2024-01-12T14:30:00")
        private LocalDateTime updatedAt;
        
        @Schema(description = "견적 항목 목록")
        private List<QuoteItemDto.Response> items;
    }

    /**
     * 견적서 목록 응답 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "견적서 목록 응답")
    public static class ListResponse {
        
        @Schema(description = "견적서 목록")
        private List<Response> quotes;
        
        @Schema(description = "총 개수", example = "50")
        private long totalCount;
        
        @Schema(description = "현재 페이지", example = "1")
        private int currentPage;
        
        @Schema(description = "페이지 크기", example = "10")
        private int pageSize;
        
        @Schema(description = "총 페이지 수", example = "5")
        private int totalPages;
    }

    /**
     * 견적서 상태 변경 요청 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "견적서 상태 변경 요청")
    public static class StatusChangeRequest {
        
        @Size(max = 500, message = "사유는 500자를 초과할 수 없습니다")
        @Schema(description = "변경 사유", example = "고객 요청에 의한 거절")
        private String reason;
    }

    /**
     * 견적서 검색 조건 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "견적서 검색 조건")
    public static class SearchCriteria {
        
        @Schema(description = "견적서 상태", example = "PENDING")
        private Quote.QuoteStatus status;
        
        @Schema(description = "예약 ID", example = "1")
        private Long reservationId;
        
        @Schema(description = "시작 날짜", example = "2024-01-01T00:00:00")
        private LocalDateTime startDate;
        
        @Schema(description = "종료 날짜", example = "2024-12-31T23:59:59")
        private LocalDateTime endDate;
        
        @Schema(description = "최소 금액", example = "100000.00")
        private BigDecimal minAmount;
        
        @Schema(description = "최대 금액", example = "500000.00")
        private BigDecimal maxAmount;
        
        @Min(value = 0, message = "페이지는 0 이상이어야 합니다")
        @Schema(description = "페이지 번호", example = "0")
        private int page = 0;
        
        @Min(value = 1, message = "페이지 크기는 1 이상이어야 합니다")
        @Max(value = 100, message = "페이지 크기는 100 이하여야 합니다")
        @Schema(description = "페이지 크기", example = "10")
        private int size = 10;
    }
} 