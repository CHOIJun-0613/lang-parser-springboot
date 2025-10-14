package com.carcare.domain.payment.repository;

import com.carcare.domain.payment.entity.Payment;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;
import java.util.Optional;

/**
 * 결제 리포지토리
 */
@Mapper
public interface PaymentRepository {
    
    /**
     * 결제 정보 저장
     */
    void save(Payment payment);
    
    /**
     * 결제 정보 업데이트
     */
    void update(Payment payment);
    
    /**
     * ID로 결제 정보 조회
     */
    Optional<Payment> findById(@Param("id") Long id);
    
    /**
     * UUID로 결제 정보 조회
     */
    Optional<Payment> findByPaymentUuid(@Param("paymentUuid") String paymentUuid);
    
    /**
     * 트랜잭션 ID로 결제 정보 조회
     */
    Optional<Payment> findByTransactionId(@Param("transactionId") String transactionId);
    
    /**
     * 예약 ID로 결제 정보 조회
     */
    List<Payment> findByReservationId(@Param("reservationId") Long reservationId);
    
    /**
     * 견적 ID로 결제 정보 조회
     */
    List<Payment> findByQuoteId(@Param("quoteId") Long quoteId);
    
    /**
     * 사용자별 결제 목록 조회
     */
    List<Payment> findByUserId(@Param("userId") Long userId);
    
    /**
     * 결제 상태별 조회
     */
    List<Payment> findByStatus(@Param("status") Payment.PaymentStatus status);
    
    /**
     * 결제 정보 삭제
     */
    void deleteById(@Param("id") Long id);
    
    /**
     * 전체 결제 건수 조회
     */
    int count();
    
    /**
     * 검색 조건에 따른 결제 목록 조회
     */
    List<Payment> findBySearchCriteria(SearchCriteria criteria);
    
    /**
     * 검색 조건에 따른 결제 건수 조회
     */
    int countBySearchCriteria(SearchCriteria criteria);
    
    /**
     * 검색 조건 DTO
     */
    public static class SearchCriteria {
        private Long userId;
        private Payment.PaymentStatus status;
        private Payment.PaymentMethod paymentMethod;
        private String startDate;
        private String endDate;
        private int offset;
        private int limit;
        
        // Getters and Setters
        public Long getUserId() { return userId; }
        public void setUserId(Long userId) { this.userId = userId; }
        
        public Payment.PaymentStatus getStatus() { return status; }
        public void setStatus(Payment.PaymentStatus status) { this.status = status; }
        
        public Payment.PaymentMethod getPaymentMethod() { return paymentMethod; }
        public void setPaymentMethod(Payment.PaymentMethod paymentMethod) { this.paymentMethod = paymentMethod; }
        
        public String getStartDate() { return startDate; }
        public void setStartDate(String startDate) { this.startDate = startDate; }
        
        public String getEndDate() { return endDate; }
        public void setEndDate(String endDate) { this.endDate = endDate; }
        
        public int getOffset() { return offset; }
        public void setOffset(int offset) { this.offset = offset; }
        
        public int getLimit() { return limit; }
        public void setLimit(int limit) { this.limit = limit; }
    }
} 