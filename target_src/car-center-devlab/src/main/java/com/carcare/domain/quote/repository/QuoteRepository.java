package com.carcare.domain.quote.repository;

import com.carcare.domain.quote.entity.Quote;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * 견적서 데이터 접근 인터페이스
 */
@Mapper
public interface QuoteRepository {

    /**
     * 견적서 등록
     */
    int insertQuote(Quote quote);

    /**
     * 견적서 정보 수정
     */
    int updateQuote(Quote quote);

    /**
     * 견적서 삭제 (소프트 삭제)
     */
    int deleteQuote(@Param("id") Long id);

    /**
     * 견적서 조회 (ID)
     */
    Optional<Quote> findById(Long id);

    /**
     * UUID로 견적서 조회
     */
    Optional<Quote> findByUuid(UUID uuid);

    /**
     * 예약 ID로 견적서 조회
     */
    Optional<Quote> findByReservationId(Long reservationId);

    /**
     * 견적서 조회 (항목 포함)
     */
    Optional<Quote> findByIdWithItems(Long id);

    /**
     * 상태별 견적서 목록
     */
    List<Quote> findByStatus(@Param("status") String status);

    /**
     * 만료된 견적서 목록
     */
    List<Quote> findExpiredQuotes(@Param("currentTime") LocalDateTime currentTime);

    /**
     * 견적서 목록 (페이징)
     */
    List<Quote> findQuotesWithPaging(@Param("offset") int offset, @Param("limit") int limit);

    /**
     * 견적서 총 개수
     */
    long countQuotes();

    /**
     * 사용자별 견적서 목록 (예약을 통한 간접 조회)
     */
    List<Quote> findByUserId(@Param("userId") Long userId);

    /**
     * 정비소별 견적서 목록 (예약을 통한 간접 조회)
     */
    List<Quote> findByServiceCenterId(@Param("serviceCenterId") Long serviceCenterId);

    /**
     * 기간별 견적서 조회
     */
    List<Quote> findByDateRange(@Param("startDate") LocalDateTime startDate, 
                               @Param("endDate") LocalDateTime endDate);

    /**
     * 견적서 통계 조회
     */
    QuoteStatistics getQuoteStatistics(@Param("startDate") LocalDateTime startDate, 
                                     @Param("endDate") LocalDateTime endDate);

    /**
     * 견적서 통계 내부 클래스
     */
    class QuoteStatistics {
        private long totalCount;
        private long draftCount;
        private long sentCount;
        private long approvedCount;
        private long rejectedCount;
        private long expiredCount;
        
        // getters and setters
        public long getTotalCount() { return totalCount; }
        public void setTotalCount(long totalCount) { this.totalCount = totalCount; }
        
        public long getDraftCount() { return draftCount; }
        public void setDraftCount(long draftCount) { this.draftCount = draftCount; }
        
        public long getSentCount() { return sentCount; }
        public void setSentCount(long sentCount) { this.sentCount = sentCount; }
        
        public long getApprovedCount() { return approvedCount; }
        public void setApprovedCount(long approvedCount) { this.approvedCount = approvedCount; }
        
        public long getRejectedCount() { return rejectedCount; }
        public void setRejectedCount(long rejectedCount) { this.rejectedCount = rejectedCount; }
        
        public long getExpiredCount() { return expiredCount; }
        public void setExpiredCount(long expiredCount) { this.expiredCount = expiredCount; }
    }
} 