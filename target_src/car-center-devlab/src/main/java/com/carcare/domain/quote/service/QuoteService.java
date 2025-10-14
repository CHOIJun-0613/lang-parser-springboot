package com.carcare.domain.quote.service;

import com.carcare.domain.quote.entity.Quote;
import com.carcare.domain.quote.entity.QuoteItem;
import com.carcare.domain.quote.repository.QuoteRepository;
import com.carcare.domain.quote.repository.QuoteItemRepository;
import com.carcare.domain.quote.dto.QuoteDto;
import com.carcare.domain.quote.dto.QuoteItemDto;
import com.carcare.common.exception.BusinessException;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

/**
 * 견적서 서비스
 */
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
@Slf4j
public class QuoteService {

    private final QuoteRepository quoteRepository;
    private final QuoteItemRepository quoteItemRepository;
    private final QuoteCalculationService calculationService;

    /**
     * 견적서 생성
     */
    @Transactional
    public QuoteDto.Response createQuote(QuoteDto.CreateRequest request) {
        log.info("견적서 생성 요청: reservationId={}", request.getReservationId());
        
        // 예약 ID로 기존 견적서 중복 체크
        quoteRepository.findByReservationId(request.getReservationId())
            .ifPresent(existing -> {
                throw new BusinessException("해당 예약에 대한 견적서가 이미 존재합니다.");
            });

        // 견적서 엔티티 생성
        Quote quote = Quote.builder()
            .reservationId(request.getReservationId())
            .laborCost(request.getLaborCost())
            .partsCost(request.getPartsCost())
            .taxAmount(request.getTaxAmount())
            .discountAmount(request.getDiscountAmount())
            .validUntil(request.getValidUntil())
            .notes(request.getNotes())
            .build();

        quote.setDefaults();

        // 견적서 저장
        int result = quoteRepository.insertQuote(quote);
        if (result == 0) {
            throw new BusinessException("견적서 생성에 실패했습니다.");
        }

        // 견적 항목 저장
        if (request.getItems() != null && !request.getItems().isEmpty()) {
            List<QuoteItem> items = request.getItems().stream()
                .map(itemRequest -> {
                    QuoteItem item = QuoteItem.builder()
                        .quoteId(quote.getId())
                        .itemType(itemRequest.getItemType())
                        .description(itemRequest.getDescription())
                        .quantity(itemRequest.getQuantity())
                        .unitPrice(itemRequest.getUnitPrice())
                        .warrantyPeriod(itemRequest.getWarrantyPeriod())
                        .notes(itemRequest.getNotes())
                        .build();
                    item.setDefaults();
                    item.calculateTotalPrice();
                    return item;
                })
                .collect(Collectors.toList());

            quoteItemRepository.insertQuoteItems(items);
            
            // 견적 항목 기반으로 총액 자동 계산 및 업데이트
            try {
                QuoteCalculationService.QuoteCalculationResult calculationResult = 
                    calculationService.calculateQuoteTotal(quote.getId());
                
                // 계산된 금액으로 견적서 업데이트
                quote.setLaborCost(calculationResult.getLaborCost());
                quote.setPartsCost(calculationResult.getPartsCost());
                quote.setTaxAmount(calculationResult.getTaxAmount());
                quote.setTotalAmount(calculationResult.getTotalAmount());
                
                // 견적서 재저장
                quoteRepository.updateQuote(quote);
                
                log.info("견적서 총액 자동 계산 완료: quoteId={}, totalAmount={}", 
                    quote.getId(), quote.getTotalAmount());
            } catch (Exception e) {
                log.warn("견적서 총액 자동 계산 실패: quoteId={}, error={}", quote.getId(), e.getMessage());
                // 계산 실패해도 견적서 생성은 완료
            }
        }

        log.info("견적서 생성 완료: quoteId={}", quote.getId());
        return findQuoteById(quote.getId());
    }

    /**
     * 견적서 조회
     */
    public QuoteDto.Response findQuoteById(Long id) {
        Quote quote = quoteRepository.findByIdWithItems(id)
            .orElseThrow(() -> new BusinessException("견적서를 찾을 수 없습니다."));

        return convertToDto(quote);
    }

    /**
     * UUID로 견적서 조회
     */
    public QuoteDto.Response findQuoteByUuid(UUID uuid) {
        Quote quote = quoteRepository.findByUuid(uuid)
            .orElseThrow(() -> new BusinessException("견적서를 찾을 수 없습니다."));

        // 견적 항목 조회
        List<QuoteItem> items = quoteItemRepository.findByQuoteId(quote.getId());
        quote.setQuoteItems(items);

        return convertToDto(quote);
    }

    /**
     * 예약 ID로 견적서 조회
     */
    public QuoteDto.Response findQuoteByReservationId(Long reservationId) {
        Quote quote = quoteRepository.findByReservationId(reservationId)
            .orElseThrow(() -> new BusinessException("해당 예약에 대한 견적서를 찾을 수 없습니다."));

        // 견적 항목 조회
        List<QuoteItem> items = quoteItemRepository.findByQuoteId(quote.getId());
        quote.setQuoteItems(items);

        return convertToDto(quote);
    }

    /**
     * 견적서 수정
     */
    @Transactional
    public QuoteDto.Response updateQuote(Long id, QuoteDto.UpdateRequest request) {
        log.info("견적서 수정 요청: quoteId={}", id);

        Quote quote = quoteRepository.findById(id)
            .orElseThrow(() -> new BusinessException("견적서를 찾을 수 없습니다."));

        // 수정 가능 여부 검증
        if (!quote.isEditable()) {
            throw new BusinessException("임시저장 상태의 견적서만 수정할 수 있습니다.");
        }

        // 견적서 정보 업데이트
        if (request.getLaborCost() != null) {
            quote.setLaborCost(request.getLaborCost());
        }
        if (request.getPartsCost() != null) {
            quote.setPartsCost(request.getPartsCost());
        }
        if (request.getTaxAmount() != null) {
            quote.setTaxAmount(request.getTaxAmount());
        }
        if (request.getDiscountAmount() != null) {
            quote.setDiscountAmount(request.getDiscountAmount());
        }
        if (request.getValidUntil() != null) {
            quote.setValidUntil(request.getValidUntil());
        }
        if (request.getNotes() != null) {
            quote.setNotes(request.getNotes());
        }

        int result = quoteRepository.updateQuote(quote);
        if (result == 0) {
            throw new BusinessException("견적서 수정에 실패했습니다.");
        }

        // 견적서 총액 재계산
        try {
            // 수동 입력된 금액 + 견적 항목 기반 계산
            BigDecimal laborCost = quote.getLaborCost() != null ? quote.getLaborCost() : BigDecimal.ZERO;
            BigDecimal partsCost = quote.getPartsCost() != null ? quote.getPartsCost() : BigDecimal.ZERO;
            BigDecimal taxAmount = quote.getTaxAmount() != null ? quote.getTaxAmount() : BigDecimal.ZERO;
            BigDecimal discountAmount = quote.getDiscountAmount() != null ? quote.getDiscountAmount() : BigDecimal.ZERO;
            
            // 견적 항목이 있는 경우 항목별 금액도 포함
            List<QuoteItem> items = quoteItemRepository.findByQuoteId(quote.getId());
            if (!items.isEmpty()) {
                // 견적 항목에서 타입별 금액 계산
                BigDecimal itemLaborCost = items.stream()
                    .filter(item -> item.getItemType() == QuoteItem.QuoteItemType.LABOR)
                    .map(QuoteItem::getTotalPrice)
                    .reduce(BigDecimal.ZERO, BigDecimal::add);
                
                BigDecimal itemPartsCost = items.stream()
                    .filter(item -> item.getItemType() == QuoteItem.QuoteItemType.PART)
                    .map(QuoteItem::getTotalPrice)
                    .reduce(BigDecimal.ZERO, BigDecimal::add);
                
                BigDecimal itemMaterialCost = items.stream()
                    .filter(item -> item.getItemType() == QuoteItem.QuoteItemType.MATERIAL)
                    .map(QuoteItem::getTotalPrice)
                    .reduce(BigDecimal.ZERO, BigDecimal::add);
                
                BigDecimal itemDiagnosticCost = items.stream()
                    .filter(item -> item.getItemType() == QuoteItem.QuoteItemType.DIAGNOSTIC)
                    .map(QuoteItem::getTotalPrice)
                    .reduce(BigDecimal.ZERO, BigDecimal::add);
                
                BigDecimal itemOtherCost = items.stream()
                    .filter(item -> item.getItemType() == QuoteItem.QuoteItemType.OTHER)
                    .map(QuoteItem::getTotalPrice)
                    .reduce(BigDecimal.ZERO, BigDecimal::add);
                
                // 수동 입력 금액과 항목 금액 중 더 큰 값 사용
                laborCost = laborCost.max(itemLaborCost);
                partsCost = partsCost.max(itemPartsCost.add(itemMaterialCost));
                
                // 부가세 재계산 (부품비와 소모품비에 10% 적용)
                BigDecimal calculatedTax = partsCost.multiply(new BigDecimal("0.10"));
                if (taxAmount.compareTo(calculatedTax) < 0) {
                    taxAmount = calculatedTax;
                }
                
                // 진단비와 기타비용은 총액에 직접 추가
                laborCost = laborCost.add(itemDiagnosticCost).add(itemOtherCost);
            }
            
            // 최종 총액 계산: (공임비 + 부품비 + 부가세) - 할인금액
            BigDecimal totalAmount = laborCost.add(partsCost).add(taxAmount).subtract(discountAmount);
            
            // 음수 방지
            if (totalAmount.compareTo(BigDecimal.ZERO) < 0) {
                totalAmount = BigDecimal.ZERO;
            }
            
            // 계산된 금액으로 업데이트
            quote.setLaborCost(laborCost);
            quote.setPartsCost(partsCost);
            quote.setTaxAmount(taxAmount);
            quote.setTotalAmount(totalAmount);
            
            // 견적서 재저장
            quoteRepository.updateQuote(quote);
            
            log.info("견적서 총액 재계산 완료: quoteId={}, totalAmount={}", 
                quote.getId(), quote.getTotalAmount());
                
        } catch (Exception e) {
            log.warn("견적서 총액 재계산 실패: quoteId={}, error={}", quote.getId(), e.getMessage());
        }

        log.info("견적서 수정 완료: quoteId={}", id);
        return findQuoteById(id);
    }

    /**
     * 견적서 삭제
     */
    @Transactional
    public void deleteQuote(Long id) {
        log.info("견적서 삭제 요청: quoteId={}", id);

        Quote quote = quoteRepository.findById(id)
            .orElseThrow(() -> new BusinessException("견적서를 찾을 수 없습니다."));

        // 삭제 가능 여부 검증
        if (!quote.isEditable()) {
            throw new BusinessException("임시저장 상태의 견적서만 삭제할 수 있습니다.");
        }

        // 견적 항목 삭제
        quoteItemRepository.deleteByQuoteId(id);

        // 견적서 삭제
        int result = quoteRepository.deleteQuote(id);
        if (result == 0) {
            throw new BusinessException("견적서 삭제에 실패했습니다.");
        }

        log.info("견적서 삭제 완료: quoteId={}", id);
    }

    /**
     * 견적서 발송
     */
    @Transactional
    public QuoteDto.Response sendQuote(Long id) {
        log.info("견적서 발송 요청: quoteId={}", id);

        Quote quote = quoteRepository.findById(id)
            .orElseThrow(() -> new BusinessException("견적서를 찾을 수 없습니다."));

        quote.send();

        int result = quoteRepository.updateQuote(quote);
        if (result == 0) {
            throw new BusinessException("견적서 발송에 실패했습니다.");
        }

        log.info("견적서 발송 완료: quoteId={}", id);
        return findQuoteById(id);
    }

    /**
     * 견적서 승인
     */
    @Transactional
    public QuoteDto.Response approveQuote(Long id) {
        log.info("견적서 승인 요청: quoteId={}", id);

        Quote quote = quoteRepository.findById(id)
            .orElseThrow(() -> new BusinessException("견적서를 찾을 수 없습니다."));

        quote.approve();

        int result = quoteRepository.updateQuote(quote);
        if (result == 0) {
            throw new BusinessException("견적서 승인에 실패했습니다.");
        }

        log.info("견적서 승인 완료: quoteId={}", id);
        return findQuoteById(id);
    }

    /**
     * 견적서 거절
     */
    @Transactional
    public QuoteDto.Response rejectQuote(Long id, QuoteDto.StatusChangeRequest request) {
        log.info("견적서 거절 요청: quoteId={}", id);

        Quote quote = quoteRepository.findById(id)
            .orElseThrow(() -> new BusinessException("견적서를 찾을 수 없습니다."));

        quote.reject(request.getReason());

        int result = quoteRepository.updateQuote(quote);
        if (result == 0) {
            throw new BusinessException("견적서 거절에 실패했습니다.");
        }

        log.info("견적서 거절 완료: quoteId={}", id);
        return findQuoteById(id);
    }

    /**
     * 견적서 목록 조회 (페이징)
     */
    public QuoteDto.ListResponse findQuotes(int page, int size) {
        int offset = page * size;
        List<Quote> quotes = quoteRepository.findQuotesWithPaging(offset, size);
        long totalCount = quoteRepository.countQuotes();
        int totalPages = (int) Math.ceil((double) totalCount / size);

        List<QuoteDto.Response> quoteDtos = quotes.stream()
            .map(this::convertToDto)
            .collect(Collectors.toList());

        return QuoteDto.ListResponse.builder()
            .quotes(quoteDtos)
            .totalCount(totalCount)
            .currentPage(page)
            .pageSize(size)
            .totalPages(totalPages)
            .build();
    }

    /**
     * 상태별 견적서 조회
     */
    public List<QuoteDto.Response> findQuotesByStatus(Quote.QuoteStatus status) {
        List<Quote> quotes = quoteRepository.findByStatus(status.name());
        return quotes.stream()
            .map(this::convertToDto)
            .collect(Collectors.toList());
    }

    /**
     * 만료된 견적서 처리
     */
    @Transactional
    public void processExpiredQuotes() {
        log.info("만료된 견적서 처리 시작");

        List<Quote> expiredQuotes = quoteRepository.findExpiredQuotes(LocalDateTime.now());

        for (Quote quote : expiredQuotes) {
            try {
                quote.expire();
                quoteRepository.updateQuote(quote);
                log.info("견적서 만료 처리: quoteId={}", quote.getId());
            } catch (Exception e) {
                log.error("견적서 만료 처리 실패: quoteId={}, error={}", quote.getId(), e.getMessage());
            }
        }

        log.info("만료된 견적서 처리 완료: {}건", expiredQuotes.size());
    }

    /**
     * 엔티티를 DTO로 변환
     */
    private QuoteDto.Response convertToDto(Quote quote) {
        List<QuoteItemDto.Response> itemDtos = null;
        if (quote.getQuoteItems() != null) {
            itemDtos = quote.getQuoteItems().stream()
                .map(this::convertItemToDto)
                .collect(Collectors.toList());
        }

        return QuoteDto.Response.builder()
            .id(quote.getId())
            .quoteUuid(quote.getQuoteUuid())
            .reservationId(quote.getReservationId())
            .laborCost(quote.getLaborCost())
            .partsCost(quote.getPartsCost())
            .taxAmount(quote.getTaxAmount())
            .discountAmount(quote.getDiscountAmount())
            .totalAmount(quote.getTotalAmount())
            .status(quote.getStatus())
            .validUntil(quote.getValidUntil())
            .notes(quote.getNotes())
            .approvedAt(quote.getApprovedAt())
            .rejectedAt(quote.getRejectedAt())
            .rejectionReason(quote.getRejectionReason())
            .createdAt(quote.getCreatedAt())
            .updatedAt(quote.getUpdatedAt())
            .items(itemDtos)
            .build();
    }

    /**
     * QuoteItem 엔티티를 DTO로 변환
     */
    private QuoteItemDto.Response convertItemToDto(QuoteItem item) {
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
} 