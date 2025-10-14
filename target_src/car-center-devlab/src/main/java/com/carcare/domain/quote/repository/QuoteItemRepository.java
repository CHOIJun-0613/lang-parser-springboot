package com.carcare.domain.quote.repository;

import com.carcare.domain.quote.entity.QuoteItem;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;
import java.util.Optional;

/**
 * 견적 항목 데이터 접근 인터페이스
 */
@Mapper
public interface QuoteItemRepository {

    /**
     * 견적 항목 등록
     */
    int insertQuoteItem(QuoteItem quoteItem);

    /**
     * 견적 항목 정보 수정
     */
    int updateQuoteItem(QuoteItem quoteItem);

    /**
     * 견적 항목 삭제
     */
    int deleteQuoteItem(@Param("id") Long id);

    /**
     * 견적 항목 조회 (ID)
     */
    Optional<QuoteItem> findById(Long id);

    /**
     * 견적서별 항목 목록
     */
    List<QuoteItem> findByQuoteId(@Param("quoteId") Long quoteId);

    /**
     * 항목 타입별 견적 항목 목록
     */
    List<QuoteItem> findByQuoteIdAndType(@Param("quoteId") Long quoteId, 
                                        @Param("itemType") String itemType);

    /**
     * 견적서의 모든 항목 삭제
     */
    int deleteByQuoteId(@Param("quoteId") Long quoteId);

    /**
     * 견적 항목 일괄 등록
     */
    int insertQuoteItems(@Param("items") List<QuoteItem> items);

    /**
     * 견적 항목 총 개수
     */
    long countByQuoteId(@Param("quoteId") Long quoteId);
} 