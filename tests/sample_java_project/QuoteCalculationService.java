package com.carcare.domain.quote.service;

import com.carcare.domain.quote.entity.Quote;
import com.carcare.domain.quote.entity.QuoteItem;
import com.carcare.domain.quote.repository.QuoteItemRepository;
import com.carcare.common.exception.BusinessException;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;

/**
 * 견적서 계산 서비스
 * 세금 계산, 총액 계산, 할인 적용 등의 복잡한 계산 로직을 담당
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class QuoteCalculationService {

    private final QuoteItemRepository quoteItemRepository;

    // 부가세율 (10%)
    private static final BigDecimal VAT_RATE = new BigDecimal("0.10");
    
    // 계산 정밀도 (소수점 2자리)
    private static final int SCALE = 2;
    private static final RoundingMode ROUNDING_MODE = RoundingMode.HALF_UP;

    /**
     * 견적서 전체 금액 재계산
     */
    public QuoteCalculationResult calculateQuoteTotal(Long quoteId) {
        log.info("견적서 금액 계산 시작: quoteId={}", quoteId);
        
        // 견적 항목들 조회
        List<QuoteItem> items = quoteItemRepository.findByQuoteId(quoteId);
        
        if (items.isEmpty()) {
            log.warn("견적 항목이 없음: quoteId={}", quoteId);
            return QuoteCalculationResult.builder()
                .laborCost(BigDecimal.ZERO)
                .partsCost(BigDecimal.ZERO)
                .materialCost(BigDecimal.ZERO)
                .diagnosticCost(BigDecimal.ZERO)
                .otherCost(BigDecimal.ZERO)
                .subtotal(BigDecimal.ZERO)
                .taxAmount(BigDecimal.ZERO)
                .totalAmount(BigDecimal.ZERO)
                .build();
        }
        
        // 항목별 금액 합계 계산
        BigDecimal laborCost = calculateCostByType(items, QuoteItem.QuoteItemType.LABOR);
        BigDecimal partsCost = calculateCostByType(items, QuoteItem.QuoteItemType.PART);
        BigDecimal materialCost = calculateCostByType(items, QuoteItem.QuoteItemType.MATERIAL);
        BigDecimal diagnosticCost = calculateCostByType(items, QuoteItem.QuoteItemType.DIAGNOSTIC);
        BigDecimal otherCost = calculateCostByType(items, QuoteItem.QuoteItemType.OTHER);
        
        // 소계 계산
        BigDecimal subtotal = laborCost.add(partsCost).add(materialCost).add(diagnosticCost).add(otherCost);
        
        // 부가세 계산 (부품비, 소모품비에만 적용)
        BigDecimal taxableAmount = partsCost.add(materialCost);
        BigDecimal taxAmount = calculateVAT(taxableAmount);
        
        // 총액 계산
        BigDecimal totalAmount = subtotal.add(taxAmount);
        
        QuoteCalculationResult result = QuoteCalculationResult.builder()
            .laborCost(laborCost)
            .partsCost(partsCost)
            .materialCost(materialCost)
            .diagnosticCost(diagnosticCost)
            .otherCost(otherCost)
            .subtotal(subtotal)
            .taxableAmount(taxableAmount)
            .taxAmount(taxAmount)
            .totalAmount(totalAmount)
            .build();
        
        log.info("견적서 금액 계산 완료: quoteId={}, totalAmount={}", quoteId, totalAmount);
        return result;
    }

    /**
     * 견적서에 할인 적용
     */
    public QuoteCalculationResult applyDiscount(Long quoteId, BigDecimal discountAmount, DiscountType discountType) {
        log.info("할인 적용 시작: quoteId={}, discountAmount={}, discountType={}", 
                quoteId, discountAmount, discountType);
        
        QuoteCalculationResult baseResult = calculateQuoteTotal(quoteId);
        
        // 할인 금액 계산
        BigDecimal finalDiscountAmount = calculateDiscountAmount(baseResult.getTotalAmount(), discountAmount, discountType);
        
        // 할인 적용 후 총액
        BigDecimal discountedTotal = baseResult.getTotalAmount().subtract(finalDiscountAmount);
        
        // 음수 방지
        if (discountedTotal.compareTo(BigDecimal.ZERO) < 0) {
            discountedTotal = BigDecimal.ZERO;
            finalDiscountAmount = baseResult.getTotalAmount();
        }
        
        QuoteCalculationResult result = baseResult.toBuilder()
            .discountAmount(finalDiscountAmount)
            .discountType(discountType)
            .finalAmount(discountedTotal)
            .build();
        
        log.info("할인 적용 완료: quoteId={}, discountAmount={}, finalAmount={}", 
                quoteId, finalDiscountAmount, discountedTotal);
        
        return result;
    }

    /**
     * 부가세 계산
     */
    public BigDecimal calculateVAT(BigDecimal amount) {
        if (amount == null || amount.compareTo(BigDecimal.ZERO) <= 0) {
            return BigDecimal.ZERO;
        }
        
        return amount.multiply(VAT_RATE).setScale(SCALE, ROUNDING_MODE);
    }

    /**
     * 항목 타입별 금액 합계 계산
     */
    private BigDecimal calculateCostByType(List<QuoteItem> items, QuoteItem.QuoteItemType itemType) {
        return items.stream()
            .filter(item -> item.getItemType() == itemType)
            .map(QuoteItem::getTotalPrice)
            .filter(price -> price != null)
            .reduce(BigDecimal.ZERO, BigDecimal::add)
            .setScale(SCALE, ROUNDING_MODE);
    }

    /**
     * 할인 금액 계산
     */
    private BigDecimal calculateDiscountAmount(BigDecimal baseAmount, BigDecimal discountValue, DiscountType discountType) {
        return switch (discountType) {
            case FIXED_AMOUNT -> discountValue.setScale(SCALE, ROUNDING_MODE);
            case PERCENTAGE -> baseAmount.multiply(discountValue.divide(new BigDecimal("100"), SCALE, ROUNDING_MODE))
                                      .setScale(SCALE, ROUNDING_MODE);
        };
    }

    /**
     * 견적 항목의 총액 재계산
     */
    public BigDecimal calculateItemTotal(Integer quantity, BigDecimal unitPrice) {
        if (quantity == null || unitPrice == null) {
            return BigDecimal.ZERO;
        }
        
        if (quantity <= 0 || unitPrice.compareTo(BigDecimal.ZERO) < 0) {
            throw new BusinessException("수량과 단가는 유효한 값이어야 합니다.");
        }
        
        return unitPrice.multiply(BigDecimal.valueOf(quantity)).setScale(SCALE, ROUNDING_MODE);
    }

    /**
     * 견적서 유효성 검증
     */
    public boolean validateQuoteAmounts(Quote quote) {
        if (quote.getTotalAmount() == null || quote.getTotalAmount().compareTo(BigDecimal.ZERO) < 0) {
            return false;
        }
        
        if (quote.getTaxAmount() != null && quote.getTaxAmount().compareTo(BigDecimal.ZERO) < 0) {
            return false;
        }
        
        if (quote.getDiscountAmount() != null && quote.getDiscountAmount().compareTo(BigDecimal.ZERO) < 0) {
            return false;
        }
        
        // 할인 금액이 총액을 초과하지 않는지 확인
        if (quote.getDiscountAmount() != null && 
            quote.getDiscountAmount().compareTo(quote.getTotalAmount()) > 0) {
            return false;
        }
        
        return true;
    }

    /**
     * 견적서 계산 결과 클래스
     */
    @lombok.Data
    @lombok.Builder(toBuilder = true)
    @lombok.NoArgsConstructor
    @lombok.AllArgsConstructor
    public static class QuoteCalculationResult {
        private BigDecimal laborCost;           // 공임비
        private BigDecimal partsCost;           // 부품비
        private BigDecimal materialCost;        // 소모품비
        private BigDecimal diagnosticCost;      // 진단비
        private BigDecimal otherCost;           // 기타비용
        private BigDecimal subtotal;            // 소계
        private BigDecimal taxableAmount;       // 과세 대상 금액
        private BigDecimal taxAmount;           // 부가세
        private BigDecimal totalAmount;         // 세전 총액
        private BigDecimal discountAmount;      // 할인금액
        private DiscountType discountType;      // 할인 유형
        private BigDecimal finalAmount;         // 최종 금액
    }

    /**
     * 할인 유형 enum
     */
    public enum DiscountType {
        FIXED_AMOUNT("정액 할인"),
        PERCENTAGE("비율 할인");
        
        private final String description;
        
        DiscountType(String description) {
            this.description = description;
        }
        
        public String getDescription() {
            return description;
        }
    }
} 