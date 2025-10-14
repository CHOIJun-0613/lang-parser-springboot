package com.carcare.domain.quote.service;

import com.carcare.domain.quote.entity.Quote;
import com.carcare.domain.quote.entity.QuoteItem;
import com.carcare.domain.quote.repository.QuoteItemRepository;
import com.carcare.domain.quote.repository.QuoteRepository;
import com.carcare.domain.quote.dto.QuoteItemDto;
import com.carcare.common.exception.BusinessException;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.stream.Collectors;

/**
 * 견적 항목 서비스
 */
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
@Slf4j
public class QuoteItemService {

    private final QuoteItemRepository quoteItemRepository;
    private final QuoteCalculationService calculationService;
    private final QuoteRepository quoteRepository;

    /**
     * 견적 항목 생성
     */
    @Transactional
    public QuoteItemDto.Response createQuoteItem(Long quoteId, QuoteItemDto.CreateRequest request) {
        log.info("견적 항목 생성 요청: quoteId={}, itemType={}", quoteId, request.getItemType());
        
        // 견적 항목 엔티티 생성
        QuoteItem quoteItem = QuoteItem.builder()
            .quoteId(quoteId)
            .itemType(request.getItemType())
            .description(request.getDescription())
            .quantity(request.getQuantity())
            .unitPrice(request.getUnitPrice())
            .warrantyPeriod(request.getWarrantyPeriod())
            .notes(request.getNotes())
            .build();

        quoteItem.setDefaults();
        quoteItem.calculateTotalPrice();

        // 유효성 검증
        if (!quoteItem.isValid()) {
            throw new BusinessException("견적 항목 정보가 유효하지 않습니다.");
        }

        // 견적 항목 저장
        int result = quoteItemRepository.insertQuoteItem(quoteItem);
        if (result == 0) {
            throw new BusinessException("견적 항목 생성에 실패했습니다.");
        }

        // 견적서 총액 재계산
        recalculateQuoteTotal(quoteId);
        
        log.info("견적 항목 생성 완료: itemId={}", quoteItem.getId());
        return findQuoteItemById(quoteItem.getId());
    }

    /**
     * 견적 항목 조회
     */
    public QuoteItemDto.Response findQuoteItemById(Long id) {
        QuoteItem quoteItem = quoteItemRepository.findById(id)
            .orElseThrow(() -> new BusinessException("견적 항목을 찾을 수 없습니다."));

        return convertToDto(quoteItem);
    }

    /**
     * 견적서별 항목 목록 조회
     */
    public List<QuoteItemDto.Response> findQuoteItemsByQuoteId(Long quoteId) {
        List<QuoteItem> items = quoteItemRepository.findByQuoteId(quoteId);
        return items.stream()
            .map(this::convertToDto)
            .collect(Collectors.toList());
    }

    /**
     * 견적서별 특정 타입 항목 목록 조회
     */
    public List<QuoteItemDto.Response> findQuoteItemsByQuoteIdAndType(Long quoteId, QuoteItem.QuoteItemType itemType) {
        List<QuoteItem> items = quoteItemRepository.findByQuoteIdAndType(quoteId, itemType.name());
        return items.stream()
            .map(this::convertToDto)
            .collect(Collectors.toList());
    }

    /**
     * 견적 항목 수정
     */
    @Transactional
    public QuoteItemDto.Response updateQuoteItem(Long id, QuoteItemDto.UpdateRequest request) {
        log.info("견적 항목 수정 요청: itemId={}", id);

        QuoteItem quoteItem = quoteItemRepository.findById(id)
            .orElseThrow(() -> new BusinessException("견적 항목을 찾을 수 없습니다."));

        // 견적 항목 정보 업데이트
        quoteItem.setItemType(request.getItemType());
        quoteItem.setDescription(request.getDescription());
        quoteItem.setQuantity(request.getQuantity());
        quoteItem.setUnitPrice(request.getUnitPrice());
        quoteItem.setWarrantyPeriod(request.getWarrantyPeriod());
        quoteItem.setNotes(request.getNotes());

        // 총액 재계산
        quoteItem.calculateTotalPrice();

        // 유효성 검증
        if (!quoteItem.isValid()) {
            throw new BusinessException("견적 항목 정보가 유효하지 않습니다.");
        }

        int result = quoteItemRepository.updateQuoteItem(quoteItem);
        if (result == 0) {
            throw new BusinessException("견적 항목 수정에 실패했습니다.");
        }

        // 견적서 총액 재계산
        recalculateQuoteTotal(quoteItem.getQuoteId());

        log.info("견적 항목 수정 완료: itemId={}", id);
        return findQuoteItemById(id);
    }

    /**
     * 견적 항목 삭제
     */
    @Transactional
    public void deleteQuoteItem(Long id) {
        log.info("견적 항목 삭제 요청: itemId={}", id);

        QuoteItem quoteItem = quoteItemRepository.findById(id)
            .orElseThrow(() -> new BusinessException("견적 항목을 찾을 수 없습니다."));

        Long quoteId = quoteItem.getQuoteId();

        int result = quoteItemRepository.deleteQuoteItem(id);
        if (result == 0) {
            throw new BusinessException("견적 항목 삭제에 실패했습니다.");
        }

        // 견적서 총액 재계산
        recalculateQuoteTotal(quoteId);

        log.info("견적 항목 삭제 완료: itemId={}", id);
    }

    /**
     * 견적서의 모든 항목 삭제
     */
    @Transactional
    public void deleteQuoteItemsByQuoteId(Long quoteId) {
        log.info("견적서 모든 항목 삭제 요청: quoteId={}", quoteId);

        int result = quoteItemRepository.deleteByQuoteId(quoteId);
        
        log.info("견적서 모든 항목 삭제 완료: quoteId={}, 삭제된 항목 수={}", quoteId, result);
    }

    /**
     * 견적 항목 일괄 생성
     */
    @Transactional
    public List<QuoteItemDto.Response> createQuoteItems(Long quoteId, List<QuoteItemDto.CreateRequest> requests) {
        log.info("견적 항목 일괄 생성 요청: quoteId={}, 항목 수={}", quoteId, requests.size());

        List<QuoteItem> items = requests.stream()
            .map(request -> {
                QuoteItem item = QuoteItem.builder()
                    .quoteId(quoteId)
                    .itemType(request.getItemType())
                    .description(request.getDescription())
                    .quantity(request.getQuantity())
                    .unitPrice(request.getUnitPrice())
                    .warrantyPeriod(request.getWarrantyPeriod())
                    .notes(request.getNotes())
                    .build();
                item.setDefaults();
                item.calculateTotalPrice();
                
                // 유효성 검증
                if (!item.isValid()) {
                    throw new BusinessException("견적 항목 정보가 유효하지 않습니다: " + item.getDescription());
                }
                
                return item;
            })
            .collect(Collectors.toList());

        int result = quoteItemRepository.insertQuoteItems(items);
        if (result == 0) {
            throw new BusinessException("견적 항목 일괄 생성에 실패했습니다.");
        }

        log.info("견적 항목 일괄 생성 완료: quoteId={}, 생성된 항목 수={}", quoteId, result);
        return findQuoteItemsByQuoteId(quoteId);
    }

    /**
     * 견적 항목 일괄 업데이트 (기존 항목 삭제 후 새로 생성)
     */
    @Transactional
    public List<QuoteItemDto.Response> replaceQuoteItems(Long quoteId, List<QuoteItemDto.CreateRequest> requests) {
        log.info("견적 항목 일괄 교체 요청: quoteId={}, 항목 수={}", quoteId, requests.size());

        // 기존 항목 삭제
        deleteQuoteItemsByQuoteId(quoteId);

        // 새 항목 생성
        if (!requests.isEmpty()) {
            return createQuoteItems(quoteId, requests);
        }

        return List.of();
    }

    /**
     * 견적 항목 개수 조회
     */
    public long countQuoteItemsByQuoteId(Long quoteId) {
        return quoteItemRepository.countByQuoteId(quoteId);
    }

    /**
     * 엔티티를 DTO로 변환
     */
    private QuoteItemDto.Response convertToDto(QuoteItem item) {
        return QuoteItemDto.Response.builder()
            .id(item.getId())
            .quoteId(item.getQuoteId())
            .itemType(item.getItemType())
            .description(item.getDescription())
            .quantity(item.getQuantity())
            .unitPrice(item.getUnitPrice())
            .totalPrice(item.getTotalPrice())
            .warrantyPeriod(item.getWarrantyPeriod())
            .notes(item.getNotes())
            .createdAt(item.getCreatedAt())
            .build();
    }

    /**
     * 견적서 총액 재계산
     */
    private void recalculateQuoteTotal(Long quoteId) {
        try {
            QuoteCalculationService.QuoteCalculationResult calculationResult = 
                calculationService.calculateQuoteTotal(quoteId);
            
            Quote quote = quoteRepository.findById(quoteId)
                .orElseThrow(() -> new BusinessException("견적서를 찾을 수 없습니다."));
            
            // 계산된 총액으로 업데이트
            quote.setTotalAmount(calculationResult.getTotalAmount());
            quoteRepository.updateQuote(quote);
            
            log.info("견적 항목 변경으로 인한 총액 재계산 완료: quoteId={}, totalAmount={}", 
                quoteId, quote.getTotalAmount());
                
        } catch (Exception e) {
            log.warn("견적서 총액 재계산 실패: quoteId={}, error={}", quoteId, e.getMessage());
        }
    }
} 