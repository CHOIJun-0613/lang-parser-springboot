package com.carcare.domain.review.service;

import com.carcare.domain.review.entity.ReviewReply;
import com.carcare.domain.review.dto.ReviewReplyDto;
import com.carcare.domain.review.repository.ReviewReplyRepository;
import com.carcare.domain.review.repository.ReviewRepository;
import com.carcare.common.exception.BusinessException;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

/**
 * 리뷰 답글 서비스
 */
@Service
@RequiredArgsConstructor
@Slf4j
@Transactional(readOnly = true)
public class ReviewReplyService {

    private final ReviewReplyRepository reviewReplyRepository;
    private final ReviewRepository reviewRepository;

    /**
     * 리뷰 답글 생성
     */
    @Transactional
    public ReviewReplyDto.Response createReply(ReviewReplyDto.CreateRequest request, Long authorId) {
        log.info("리뷰 답글 생성 요청: reviewId={}, authorId={}", request.getReviewId(), authorId);

        // 리뷰 존재 확인
        reviewRepository.findById(request.getReviewId())
                .orElseThrow(() -> new BusinessException("리뷰를 찾을 수 없습니다."));

        // 답글 엔티티 생성
        ReviewReply reply = ReviewReply.builder()
                .reviewId(request.getReviewId())
                .authorId(authorId)
                .content(request.getContent())
                .build();

        reviewReplyRepository.insert(reply);

        log.info("리뷰 답글 생성 완료: replyId={}", reply.getId());
        return convertToResponse(reply);
    }

    /**
     * 리뷰 답글 조회
     */
    public ReviewReplyDto.Response getReply(Long replyId) {
        ReviewReply reply = reviewReplyRepository.findById(replyId)
                .orElseThrow(() -> new BusinessException("답글을 찾을 수 없습니다."));

        return convertToResponse(reply);
    }

    /**
     * 리뷰별 답글 목록 조회
     */
    public List<ReviewReplyDto.Response> getReviewReplies(Long reviewId) {
        List<ReviewReply> replies = reviewReplyRepository.findByReviewId(reviewId);

        return replies.stream()
                .map(this::convertToResponse)
                .toList();
    }

    /**
     * 리뷰 답글 수정
     */
    @Transactional
    public ReviewReplyDto.Response updateReply(Long replyId, ReviewReplyDto.UpdateRequest request, Long authorId) {
        log.info("리뷰 답글 수정 요청: replyId={}, authorId={}", replyId, authorId);

        ReviewReply reply = reviewReplyRepository.findById(replyId)
                .orElseThrow(() -> new BusinessException("답글을 찾을 수 없습니다."));

        // 작성자 권한 검증
        if (!reply.getAuthorId().equals(authorId)) {
            throw new BusinessException("답글 수정 권한이 없습니다.");
        }

        // 답글 수정
        reply.setContent(request.getContent());
        reviewReplyRepository.update(reply);

        log.info("리뷰 답글 수정 완료: replyId={}", replyId);
        return convertToResponse(reply);
    }

    /**
     * 리뷰 답글 삭제
     */
    @Transactional
    public void deleteReply(Long replyId, Long authorId) {
        log.info("리뷰 답글 삭제 요청: replyId={}, authorId={}", replyId, authorId);

        ReviewReply reply = reviewReplyRepository.findById(replyId)
                .orElseThrow(() -> new BusinessException("답글을 찾을 수 없습니다."));

        // 작성자 권한 검증
        if (!reply.getAuthorId().equals(authorId)) {
            throw new BusinessException("답글 삭제 권한이 없습니다.");
        }

        reviewReplyRepository.delete(replyId);

        log.info("리뷰 답글 삭제 완료: replyId={}", replyId);
    }

    /**
     * 작성자별 답글 목록 조회
     */
    public List<ReviewReplyDto.Response> getAuthorReplies(Long authorId, Integer page, Integer size) {
        int offset = page * size;
        List<ReviewReply> replies = reviewReplyRepository.findByAuthorId(authorId, offset, size);

        return replies.stream()
                .map(this::convertToResponse)
                .toList();
    }

    /**
     * ReviewReply 엔티티를 Response DTO로 변환
     */
    private ReviewReplyDto.Response convertToResponse(ReviewReply reply) {
        return ReviewReplyDto.Response.builder()
                .id(reply.getId())
                .reviewId(reply.getReviewId())
                .authorId(reply.getAuthorId())
                .content(reply.getContent())
                .createdAt(reply.getCreatedAt())
                .updatedAt(reply.getUpdatedAt())
                .authorName(reply.getAuthorName())
                .authorType(reply.getAuthorType())
                .build();
    }
} 