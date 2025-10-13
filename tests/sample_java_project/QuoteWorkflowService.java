package com.carcare.domain.quote.service;

import com.carcare.domain.quote.entity.Quote;
import com.carcare.domain.quote.entity.QuoteStatusHistory;
import com.carcare.domain.quote.repository.QuoteRepository;
import com.carcare.domain.quote.dto.QuoteDto;
import com.carcare.common.exception.BusinessException;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import lombok.Data;
import lombok.Builder;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

/**
 * 견적서 워크플로우 서비스
 * 견적서 상태 관리 및 승인 프로세스를 담당
 */
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
@Slf4j
public class QuoteWorkflowService {

    private final QuoteRepository quoteRepository;

    /**
     * 견적서 상태 변경 가능 여부 검증
     */
    public boolean canChangeStatus(Quote quote, Quote.QuoteStatus targetStatus) {
        Quote.QuoteStatus currentStatus = quote.getStatus();
        
        return switch (targetStatus) {
            case DRAFT -> currentStatus == Quote.QuoteStatus.DRAFT; // 이미 DRAFT이거나 불가능
            case PENDING -> currentStatus == Quote.QuoteStatus.DRAFT;
            case APPROVED -> currentStatus == Quote.QuoteStatus.PENDING && quote.isValid();
            case REJECTED -> currentStatus == Quote.QuoteStatus.PENDING || currentStatus == Quote.QuoteStatus.DRAFT;
            case EXPIRED -> currentStatus == Quote.QuoteStatus.PENDING || 
                           (quote.getValidUntil() != null && LocalDateTime.now().isAfter(quote.getValidUntil()));
        };
    }

    /**
     * 견적서 발송 가능 여부 검증
     */
    public void validateSendConditions(Quote quote) {
        if (quote.getStatus() != Quote.QuoteStatus.DRAFT) {
            throw new BusinessException("임시저장 상태의 견적서만 발송할 수 있습니다.");
        }
        
        if (quote.getTotalAmount() == null || quote.getTotalAmount().signum() <= 0) {
            throw new BusinessException("견적 금액이 유효하지 않습니다.");
        }
        
        if (quote.getValidUntil() == null || quote.getValidUntil().isBefore(LocalDateTime.now())) {
            throw new BusinessException("견적 유효기간이 설정되지 않았거나 이미 만료되었습니다.");
        }
    }

    /**
     * 견적서 승인 가능 여부 검증
     */
    public void validateApprovalConditions(Quote quote) {
        if (quote.getStatus() != Quote.QuoteStatus.PENDING) {
            throw new BusinessException("발송된 견적서만 승인할 수 있습니다.");
        }
        
        if (!quote.isValid()) {
            throw new BusinessException("만료되거나 유효하지 않은 견적서는 승인할 수 없습니다.");
        }
    }

    /**
     * 견적서 거절 가능 여부 검증
     */
    public void validateRejectionConditions(Quote quote) {
        if (quote.getStatus() == Quote.QuoteStatus.APPROVED) {
            throw new BusinessException("승인된 견적서는 거절할 수 없습니다.");
        }
        
        if (quote.getStatus() == Quote.QuoteStatus.EXPIRED) {
            throw new BusinessException("만료된 견적서는 거절할 수 없습니다.");
        }
    }

    /**
     * 견적서 발송 처리
     */
    @Transactional
    public QuoteDto.Response sendQuoteWithWorkflow(Long quoteId, String changedBy) {
        log.info("견적서 발송 워크플로우 시작: quoteId={}, changedBy={}", quoteId, changedBy);
        
        Quote quote = quoteRepository.findById(quoteId)
            .orElseThrow(() -> new BusinessException("견적서를 찾을 수 없습니다."));
        
        Quote.QuoteStatus oldStatus = quote.getStatus();
        
        // 발송 조건 검증
        validateSendConditions(quote);
        
        // 상태 변경
        quote.send();
        
        // 견적서 업데이트
        int result = quoteRepository.updateQuote(quote);
        if (result == 0) {
            throw new BusinessException("견적서 발송에 실패했습니다.");
        }
        
        // 상태 변경 이력 기록
        recordStatusChange(quote.getId(), oldStatus, quote.getStatus(), "견적서 발송", changedBy);
        
        log.info("견적서 발송 완료: quoteId={}", quoteId);
        
        // 발송 후 알림 처리 (추후 구현)
        // notificationService.sendQuoteNotification(quote);
        
        return convertToDto(quote);
    }

    /**
     * 견적서 승인 처리
     */
    @Transactional
    public QuoteDto.Response approveQuoteWithWorkflow(Long quoteId, String changedBy, String approvalNotes) {
        log.info("견적서 승인 워크플로우 시작: quoteId={}, changedBy={}", quoteId, changedBy);
        
        Quote quote = quoteRepository.findById(quoteId)
            .orElseThrow(() -> new BusinessException("견적서를 찾을 수 없습니다."));
        
        Quote.QuoteStatus oldStatus = quote.getStatus();
        
        // 승인 조건 검증
        validateApprovalConditions(quote);
        
        // 상태 변경
        quote.approve();
        
        // 견적서 업데이트
        int result = quoteRepository.updateQuote(quote);
        if (result == 0) {
            throw new BusinessException("견적서 승인에 실패했습니다.");
        }
        
        // 상태 변경 이력 기록
        recordStatusChange(quote.getId(), oldStatus, quote.getStatus(), "견적서 승인", changedBy, approvalNotes);
        
        log.info("견적서 승인 완료: quoteId={}", quoteId);
        
        // 승인 후 알림 처리 (추후 구현)
        // notificationService.sendApprovalNotification(quote);
        
        return convertToDto(quote);
    }

    /**
     * 견적서 거절 처리
     */
    @Transactional
    public QuoteDto.Response rejectQuoteWithWorkflow(Long quoteId, String reason, String changedBy) {
        log.info("견적서 거절 워크플로우 시작: quoteId={}, changedBy={}", quoteId, changedBy);
        
        Quote quote = quoteRepository.findById(quoteId)
            .orElseThrow(() -> new BusinessException("견적서를 찾을 수 없습니다."));
        
        Quote.QuoteStatus oldStatus = quote.getStatus();
        
        // 거절 조건 검증
        validateRejectionConditions(quote);
        
        // 상태 변경
        quote.reject(reason);
        
        // 견적서 업데이트
        int result = quoteRepository.updateQuote(quote);
        if (result == 0) {
            throw new BusinessException("견적서 거절에 실패했습니다.");
        }
        
        // 상태 변경 이력 기록
        recordStatusChange(quote.getId(), oldStatus, quote.getStatus(), reason, changedBy);
        
        log.info("견적서 거절 완료: quoteId={}", quoteId);
        
        // 거절 후 알림 처리 (추후 구현)
        // notificationService.sendRejectionNotification(quote);
        
        return convertToDto(quote);
    }

    /**
     * 만료된 견적서 자동 처리
     */
    @Transactional
    public int processExpiredQuotes() {
        log.info("만료된 견적서 자동 처리 시작");
        
        List<Quote> expiredQuotes = quoteRepository.findExpiredQuotes(LocalDateTime.now());
        int processedCount = 0;
        
        for (Quote quote : expiredQuotes) {
            try {
                if (canChangeStatus(quote, Quote.QuoteStatus.EXPIRED)) {
                    Quote.QuoteStatus oldStatus = quote.getStatus();
                    quote.expire();
                    
                    int result = quoteRepository.updateQuote(quote);
                    if (result > 0) {
                        recordStatusChange(quote.getId(), oldStatus, quote.getStatus(), 
                                         "자동 만료 처리", "SYSTEM");
                        processedCount++;
                        log.info("견적서 만료 처리: quoteId={}", quote.getId());
                    }
                }
            } catch (Exception e) {
                log.error("견적서 만료 처리 실패: quoteId={}, error={}", quote.getId(), e.getMessage());
            }
        }
        
        log.info("만료된 견적서 자동 처리 완료: 처리된 건수={}", processedCount);
        return processedCount;
    }

    /**
     * 견적서 상태별 통계 조회
     */
    public QuoteStatusStatistics getQuoteStatusStatistics() {
        // 실제 구현에서는 Repository에서 통계 쿼리 실행
        return QuoteStatusStatistics.builder()
            .totalCount(0L)
            .draftCount(0L)
            .sentCount(0L)
            .approvedCount(0L)
            .rejectedCount(0L)
            .expiredCount(0L)
            .build();
    }

    /**
     * 상태 변경 이력 기록
     */
    private void recordStatusChange(Long quoteId, Quote.QuoteStatus fromStatus, Quote.QuoteStatus toStatus, 
                                  String reason, String changedBy) {
        recordStatusChange(quoteId, fromStatus, toStatus, reason, changedBy, null);
    }

    /**
     * 상태 변경 이력 기록 (메모 포함)
     */
    private void recordStatusChange(Long quoteId, Quote.QuoteStatus fromStatus, Quote.QuoteStatus toStatus, 
                                  String reason, String changedBy, String notes) {
        QuoteStatusHistory history = QuoteStatusHistory.builder()
            .quoteId(quoteId)
            .fromStatus(fromStatus)
            .toStatus(toStatus)
            .reason(reason)
            .changedBy(changedBy)
            .changedAt(LocalDateTime.now())
            .notes(notes)
            .build();
        
        // 실제 구현에서는 QuoteStatusHistoryRepository.insert(history) 호출
        log.info("견적서 상태 변경 이력 기록: quoteId={}, {}→{}, changedBy={}", 
                quoteId, fromStatus, toStatus, changedBy);
    }

    /**
     * Quote 엔티티를 DTO로 변환 (간단한 변환)
     */
    private QuoteDto.Response convertToDto(Quote quote) {
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
            .build();
    }

    /**
     * 견적서 상태 통계 내부 클래스
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class QuoteStatusStatistics {
        private Long totalCount;
        private Long draftCount;
        private Long sentCount;
        private Long approvedCount;
        private Long rejectedCount;
        private Long expiredCount;
    }
} 