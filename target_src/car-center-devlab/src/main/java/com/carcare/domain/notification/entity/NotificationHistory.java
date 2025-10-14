package com.carcare.domain.notification.entity;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 알림 발송 이력 엔티티
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class NotificationHistory {
    
    private Long id;
    private String historyUuid;
    private Long notificationId;
    private Long userId;
    private String channel; // SMS, EMAIL, PUSH, IN_APP
    private String status; // PENDING, SENT, FAILED, CANCELLED
    private String content;
    private String recipientInfo; // 수신자 정보 (전화번호, 이메일 등)
    private String errorMessage;
    private String requestId; // 외부 서비스 요청 ID (SMS, 이메일 등)
    private Integer retryCount;
    private LocalDateTime sentAt;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    
    /**
     * 발송 상태 enum
     */
    public enum DeliveryStatus {
        PENDING("발송 대기"),
        SENT("발송 완료"),
        FAILED("발송 실패"),
        CANCELLED("발송 취소");
        
        private final String description;
        
        DeliveryStatus(String description) {
            this.description = description;
        }
        
        public String getDescription() {
            return description;
        }
    }
    
    /**
     * 발송 성공 이력 생성
     */
    public static NotificationHistory createSuccess(Long notificationId, Long userId, 
                                                   String channel, String content, 
                                                   String recipientInfo, String requestId) {
        return NotificationHistory.builder()
                .historyUuid(java.util.UUID.randomUUID().toString())
                .notificationId(notificationId)
                .userId(userId)
                .channel(channel)
                .status(DeliveryStatus.SENT.name())
                .content(content)
                .recipientInfo(recipientInfo)
                .requestId(requestId)
                .retryCount(0)
                .sentAt(LocalDateTime.now())
                .createdAt(LocalDateTime.now())
                .updatedAt(LocalDateTime.now())
                .build();
    }
    
    /**
     * 발송 실패 이력 생성
     */
    public static NotificationHistory createFailure(Long notificationId, Long userId, 
                                                   String channel, String content, 
                                                   String recipientInfo, String errorMessage) {
        return NotificationHistory.builder()
                .historyUuid(java.util.UUID.randomUUID().toString())
                .notificationId(notificationId)
                .userId(userId)
                .channel(channel)
                .status(DeliveryStatus.FAILED.name())
                .content(content)
                .recipientInfo(recipientInfo)
                .errorMessage(errorMessage)
                .retryCount(0)
                .createdAt(LocalDateTime.now())
                .updatedAt(LocalDateTime.now())
                .build();
    }
    
    /**
     * 재시도 횟수 증가
     */
    public void incrementRetryCount() {
        this.retryCount = (this.retryCount == null) ? 1 : this.retryCount + 1;
        this.updatedAt = LocalDateTime.now();
    }
    
    /**
     * 발송 성공으로 업데이트
     */
    public void markAsSent(String requestId) {
        this.status = DeliveryStatus.SENT.name();
        this.requestId = requestId;
        this.sentAt = LocalDateTime.now();
        this.updatedAt = LocalDateTime.now();
        this.errorMessage = null;
    }
    
    /**
     * 발송 실패로 업데이트
     */
    public void markAsFailed(String errorMessage) {
        this.status = DeliveryStatus.FAILED.name();
        this.errorMessage = errorMessage;
        this.updatedAt = LocalDateTime.now();
    }
} 