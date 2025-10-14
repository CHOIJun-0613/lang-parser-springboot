package com.carcare.domain.reservation.entity;

import lombok.Data;
import lombok.Builder;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import java.time.LocalDateTime;
import java.util.UUID;

/**
 * 예약 엔티티
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Reservation {
    
    /**
     * 예약 고유 ID
     */
    private Long id;
    
    /**
     * 예약 UUID (외부 참조용)
     */
    private UUID reservationUuid;
    
    /**
     * 고객 ID
     */
    private Long userId;
    
    /**
     * 차량 ID
     */
    private Long vehicleId;
    
    /**
     * 정비소 ID
     */
    private Long serviceCenterId;
    
    /**
     * 서비스 유형 ID
     */
    private Long serviceTypeId;
    
    /**
     * 예약 상태
     */
    private ReservationStatus status;
    
    /**
     * 예약 일시
     */
    private LocalDateTime scheduledDate;
    
    /**
     * 예상 소요시간 (분)
     */
    private Integer estimatedDuration;
    
    /**
     * 고객 요청사항
     */
    private String customerNotes;
    
    /**
     * 정비사 메모
     */
    private String mechanicNotes;
    
    /**
     * 확정 시간
     */
    private LocalDateTime confirmedAt;
    
    /**
     * 시작 시간
     */
    private LocalDateTime startedAt;
    
    /**
     * 완료 시간
     */
    private LocalDateTime completedAt;
    
    /**
     * 취소 시간
     */
    private LocalDateTime cancelledAt;
    
    /**
     * 취소 사유
     */
    private String cancellationReason;
    
    /**
     * 생성 일시
     */
    private LocalDateTime createdAt;
    
    /**
     * 수정 일시
     */
    private LocalDateTime updatedAt;
    
    /**
     * 예약 상태 ENUM
     */
    public enum ReservationStatus {
        PENDING("대기중"),
        CONFIRMED("확정"),
        IN_PROGRESS("진행중"),
        COMPLETED("완료"),
        CANCELLED("취소");
        
        private final String description;
        
        ReservationStatus(String description) {
            this.description = description;
        }
        
        public String getDescription() {
            return description;
        }
    }
    
    /**
     * 예약 확정 여부 확인
     */
    public boolean isConfirmed() {
        return status == ReservationStatus.CONFIRMED || 
               status == ReservationStatus.IN_PROGRESS || 
               status == ReservationStatus.COMPLETED;
    }
    
    /**
     * 취소 가능 여부 확인
     */
    public boolean isCancellable() {
        return status == ReservationStatus.PENDING || 
               status == ReservationStatus.CONFIRMED;
    }
    
    /**
     * 진행 중인 예약 여부 확인
     */
    public boolean isInProgress() {
        return status == ReservationStatus.IN_PROGRESS;
    }
    
    /**
     * 완료된 예약 여부 확인
     */
    public boolean isCompleted() {
        return status == ReservationStatus.COMPLETED;
    }
    
    /**
     * 예약 상태 변경 메서드
     */
    public void confirm() {
        if (status != ReservationStatus.PENDING) {
            throw new IllegalStateException("대기 중인 예약만 확정할 수 있습니다.");
        }
        this.status = ReservationStatus.CONFIRMED;
        this.confirmedAt = LocalDateTime.now();
    }
    
    public void start() {
        if (status != ReservationStatus.CONFIRMED) {
            throw new IllegalStateException("확정된 예약만 시작할 수 있습니다.");
        }
        this.status = ReservationStatus.IN_PROGRESS;
        this.startedAt = LocalDateTime.now();
    }
    
    public void complete() {
        if (status != ReservationStatus.IN_PROGRESS) {
            throw new IllegalStateException("진행 중인 예약만 완료할 수 있습니다.");
        }
        this.status = ReservationStatus.COMPLETED;
        this.completedAt = LocalDateTime.now();
    }
    
    public void cancel(String reason) {
        if (!isCancellable()) {
            throw new IllegalStateException("취소할 수 없는 예약 상태입니다.");
        }
        this.status = ReservationStatus.CANCELLED;
        this.cancellationReason = reason;
        this.cancelledAt = LocalDateTime.now();
    }
} 