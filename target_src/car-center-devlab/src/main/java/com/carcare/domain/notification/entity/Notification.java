package com.carcare.domain.notification.entity;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 알림 엔티티
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Notification {
    
    private Long id;
    private String notificationUuid;
    private Long userId;
    private NotificationType type;
    private String title;
    private String message;
    private Boolean isRead;
    private String relatedEntityType;
    private Long relatedEntityId;
    private LocalDateTime createdAt;
    
    /**
     * 알림 타입 enum
     */
    public enum NotificationType {
        RESERVATION_CONFIRMED("예약 확인"),
        RESERVATION_REMINDER("예약 리마인더"),
        APPOINTMENT_REMINDER("예약 리마인더"),
        QUOTE_READY("견적서 준비 완료"),
        QUOTE_APPROVED("견적서 승인"),
        QUOTE_REJECTED("견적서 거절"),
        SERVICE_STARTED("정비 시작"),
        SERVICE_COMPLETED("정비 완료"),
        PAYMENT_COMPLETED("결제 완료"),
        PAYMENT_FAILED("결제 실패"),
        REVIEW_REQUEST("리뷰 요청"),
        SYSTEM_MAINTENANCE("시스템 점검"),
        PROMOTION("프로모션");
        
        private final String description;
        
        NotificationType(String description) {
            this.description = description;
        }
        
        public String getDescription() {
            return description;
        }
    }
} 