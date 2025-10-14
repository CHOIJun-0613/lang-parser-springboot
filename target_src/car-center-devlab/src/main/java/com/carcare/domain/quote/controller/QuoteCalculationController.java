package com.carcare.domain.quote.controller;

import com.carcare.domain.quote.service.QuoteCalculationService;
import com.carcare.domain.quote.service.QuoteCalculationService.QuoteCalculationResult;
import com.carcare.domain.quote.service.QuoteCalculationService.DiscountType;
import com.carcare.common.dto.ApiResponse;
import com.carcare.common.util.ResponseUtils;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;

import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotNull;
import java.math.BigDecimal;

/**
 * 견적서 계산 관리 컨트롤러
 */
@RestController
@RequestMapping("/api/v1/quotes/{quoteId}/calculations")
@Tag(name = "Quote Calculation", description = "견적서 계산 API")
@RequiredArgsConstructor
@Slf4j
public class QuoteCalculationController {
    
    private final QuoteCalculationService calculationService;

    /**
     * 견적서 총 금액 계산
     */
    @PostMapping("/total")
    @Operation(summary = "견적서 총 금액 계산", description = "견적서의 모든 항목을 기반으로 총 금액을 계산합니다.")
    public ResponseEntity<ApiResponse<QuoteCalculationResult>> calculateTotal(
            @Parameter(description = "견적서 ID", example = "1")
            @PathVariable Long quoteId) {
        
        log.info("견적서 총 금액 계산 API 호출: quoteId={}", quoteId);
        
        QuoteCalculationResult result = calculationService.calculateQuoteTotal(quoteId);
        
        return ResponseEntity.ok(ResponseUtils.success("견적서 총 금액 계산이 완료되었습니다.", result));
    }

    /**
     * 할인 적용 계산
     */
    @PostMapping("/discount")
    @Operation(summary = "할인 적용 계산", description = "견적서에 할인을 적용하여 최종 금액을 계산합니다.")
    public ResponseEntity<ApiResponse<QuoteCalculationResult>> applyDiscount(
            @Parameter(description = "견적서 ID", example = "1")
            @PathVariable Long quoteId,
            @Parameter(description = "할인 금액 또는 할인율", example = "50000")
            @RequestParam @NotNull @DecimalMin("0") BigDecimal discountAmount,
            @Parameter(description = "할인 유형", example = "FIXED_AMOUNT")
            @RequestParam DiscountType discountType) {
        
        log.info("할인 적용 계산 API 호출: quoteId={}, discountAmount={}, discountType={}", 
                quoteId, discountAmount, discountType);
        
        QuoteCalculationResult result = calculationService.applyDiscount(quoteId, discountAmount, discountType);
        
        return ResponseEntity.ok(ResponseUtils.success("할인 적용 계산이 완료되었습니다.", result));
    }

    /**
     * 부가세 계산
     */
    @PostMapping("/vat")
    @Operation(summary = "부가세 계산", description = "주어진 금액에 대한 부가세를 계산합니다.")
    public ResponseEntity<ApiResponse<VatCalculationResponse>> calculateVAT(
            @Parameter(description = "견적서 ID", example = "1")
            @PathVariable Long quoteId,
            @Parameter(description = "과세 대상 금액", example = "100000")
            @RequestParam @NotNull @DecimalMin("0") BigDecimal amount) {
        
        log.info("부가세 계산 API 호출: quoteId={}, amount={}", quoteId, amount);
        
        BigDecimal vatAmount = calculationService.calculateVAT(amount);
        BigDecimal totalWithVat = amount.add(vatAmount);
        
        VatCalculationResponse response = VatCalculationResponse.builder()
            .baseAmount(amount)
            .vatAmount(vatAmount)
            .totalAmount(totalWithVat)
            .build();
        
        return ResponseEntity.ok(ResponseUtils.success("부가세 계산이 완료되었습니다.", response));
    }

    /**
     * 견적 항목 총액 계산
     */
    @PostMapping("/item-total")
    @Operation(summary = "견적 항목 총액 계산", description = "수량과 단가를 기반으로 항목 총액을 계산합니다.")
    public ResponseEntity<ApiResponse<ItemTotalResponse>> calculateItemTotal(
            @Parameter(description = "견적서 ID", example = "1")
            @PathVariable Long quoteId,
            @Parameter(description = "수량", example = "2")
            @RequestParam @NotNull Integer quantity,
            @Parameter(description = "단가", example = "50000")
            @RequestParam @NotNull @DecimalMin("0") BigDecimal unitPrice) {
        
        log.info("견적 항목 총액 계산 API 호출: quoteId={}, quantity={}, unitPrice={}", 
                quoteId, quantity, unitPrice);
        
        BigDecimal totalPrice = calculationService.calculateItemTotal(quantity, unitPrice);
        
        ItemTotalResponse response = ItemTotalResponse.builder()
            .quantity(quantity)
            .unitPrice(unitPrice)
            .totalPrice(totalPrice)
            .build();
        
        return ResponseEntity.ok(ResponseUtils.success("견적 항목 총액 계산이 완료되었습니다.", response));
    }

    /**
     * 부가세 계산 응답 DTO
     */
    @lombok.Data
    @lombok.Builder
    @lombok.NoArgsConstructor
    @lombok.AllArgsConstructor
    public static class VatCalculationResponse {
        private BigDecimal baseAmount;      // 과세 대상 금액
        private BigDecimal vatAmount;       // 부가세 금액
        private BigDecimal totalAmount;     // 부가세 포함 총액
    }

    /**
     * 항목 총액 계산 응답 DTO
     */
    @lombok.Data
    @lombok.Builder
    @lombok.NoArgsConstructor
    @lombok.AllArgsConstructor
    public static class ItemTotalResponse {
        private Integer quantity;           // 수량
        private BigDecimal unitPrice;       // 단가
        private BigDecimal totalPrice;      // 총액
    }
} 