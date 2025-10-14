package com.carcare.domain.review.repository;

import com.carcare.domain.review.entity.Review;
import com.carcare.domain.review.dto.ReviewDto;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import java.util.List;
import java.util.Optional;

/**
 * 리뷰 Repository
 */
@Mapper
public interface ReviewRepository {

    /**
     * 리뷰 생성
     */
    void insert(Review review);

    /**
     * 리뷰 조회 (ID)
     */
    Optional<Review> findById(@Param("id") Long id);

    /**
     * 리뷰 조회 (UUID)
     */
    Optional<Review> findByUuid(@Param("reviewUuid") String reviewUuid);

    /**
     * 예약 ID로 리뷰 조회
     */
    Optional<Review> findByReservationId(@Param("reservationId") Long reservationId);

    /**
     * 리뷰 수정
     */
    void update(Review review);

    /**
     * 리뷰 삭제
     */
    void delete(@Param("id") Long id);

    /**
     * 리뷰 목록 조회 (검색 조건)
     */
    List<Review> findBySearchCondition(@Param("condition") ReviewDto.SearchRequest condition);

    /**
     * 리뷰 총 개수 조회 (검색 조건)
     */
    long countBySearchCondition(@Param("condition") ReviewDto.SearchRequest condition);

    /**
     * 정비소별 리뷰 목록 조회
     */
    List<Review> findByServiceCenterId(@Param("serviceCenterId") Long serviceCenterId, 
                                      @Param("visibleOnly") Boolean visibleOnly,
                                      @Param("offset") Integer offset, 
                                      @Param("size") Integer size);

    /**
     * 정비소별 리뷰 개수 조회
     */
    long countByServiceCenterId(@Param("serviceCenterId") Long serviceCenterId, 
                               @Param("visibleOnly") Boolean visibleOnly);

    /**
     * 정비소별 리뷰 통계 조회
     */
    ReviewDto.Statistics getStatisticsByServiceCenterId(@Param("serviceCenterId") Long serviceCenterId);

    /**
     * 사용자별 리뷰 목록 조회
     */
    List<Review> findByUserId(@Param("userId") Long userId, 
                             @Param("offset") Integer offset, 
                             @Param("size") Integer size);

    /**
     * 사용자별 리뷰 개수 조회
     */
    long countByUserId(@Param("userId") Long userId);

    /**
     * 리뷰 가시성 변경
     */
    void updateVisibility(@Param("id") Long id, @Param("isVisible") Boolean isVisible);
} 