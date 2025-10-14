package com.carcare.domain.review.repository;

import com.carcare.domain.review.entity.ReviewReply;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import java.util.List;
import java.util.Optional;

/**
 * 리뷰 답글 Repository
 */
@Mapper
public interface ReviewReplyRepository {

    /**
     * 리뷰 답글 생성
     */
    void insert(ReviewReply reviewReply);

    /**
     * 리뷰 답글 조회 (ID)
     */
    Optional<ReviewReply> findById(@Param("id") Long id);

    /**
     * 리뷰 ID로 답글 목록 조회
     */
    List<ReviewReply> findByReviewId(@Param("reviewId") Long reviewId);

    /**
     * 리뷰 답글 수정
     */
    void update(ReviewReply reviewReply);

    /**
     * 리뷰 답글 삭제
     */
    void delete(@Param("id") Long id);

    /**
     * 리뷰별 답글 개수 조회
     */
    long countByReviewId(@Param("reviewId") Long reviewId);

    /**
     * 작성자별 답글 목록 조회
     */
    List<ReviewReply> findByAuthorId(@Param("authorId") Long authorId, 
                                    @Param("offset") Integer offset, 
                                    @Param("size") Integer size);

    /**
     * 작성자별 답글 개수 조회
     */
    long countByAuthorId(@Param("authorId") Long authorId);
} 