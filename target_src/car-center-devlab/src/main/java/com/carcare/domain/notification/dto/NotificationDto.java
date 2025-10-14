package com.carcare.domain.notification.dto;

import com.carcare.domain.notification.entity.Notification;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.Map;

/**
 * 알림 DTO
 */
public class NotificationDto {
    
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class CreateRequest {
        private Long userId;
        private String type;
        private String title;
        private String message;
        private String relatedEntityType;
        private Long relatedEntityId;
    }
    
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Response {
        private Long id;
        private String notificationUuid;
        private Long userId;
        private String type;
        private String title;
        private String message;
        private Boolean isRead;
        private String relatedEntityType;
        private Long relatedEntityId;
        private LocalDateTime createdAt;
        
        public static Response from(Notification notification) {
            return Response.builder()
                    .id(notification.getId())
                    .notificationUuid(notification.getNotificationUuid())
                    .userId(notification.getUserId())
                    .type(notification.getType().name())
                    .title(notification.getTitle())
                    .message(notification.getMessage())
                    .isRead(notification.getIsRead())
                    .relatedEntityType(notification.getRelatedEntityType())
                    .relatedEntityId(notification.getRelatedEntityId())
                    .createdAt(notification.getCreatedAt())
                    .build();
        }
    }
    
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ListResponse {
        private int page;
        private int size;
        private int totalCount;
        private int unreadCount;
        private java.util.List<Response> notifications;
    }
    
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class SettingsRequest {
        private Boolean smsEnabled;
        private Boolean pushEnabled;
        private Boolean emailEnabled;
        private Boolean inAppEnabled;
        private Boolean nightModeEnabled;
        private Integer quietStartHour;
        private Integer quietEndHour;
        private Boolean promotionEnabled;
        private String timezone;
        private String language;
        private Map<String, Object> typeSettings;
    }
    
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class SettingsResponse {
        private Long id;
        private Long userId;
        private Boolean smsEnabled;
        private Boolean pushEnabled;
        private Boolean emailEnabled;
        private Boolean inAppEnabled;
        private Boolean nightModeEnabled;
        private Integer quietStartHour;
        private Integer quietEndHour;
        private Boolean promotionEnabled;
        private String timezone;
        private String language;
        private Map<String, Object> typeSettings;
        private LocalDateTime createdAt;
        private LocalDateTime updatedAt;
        
        public static SettingsResponse from(com.carcare.domain.notification.entity.NotificationSettings settings) {
            return SettingsResponse.builder()
                    .id(settings.getId())
                    .userId(settings.getUserId())
                    .smsEnabled(settings.getSmsEnabled())
                    .pushEnabled(settings.getPushEnabled())
                    .emailEnabled(settings.getEmailEnabled())
                    .inAppEnabled(settings.getInAppEnabled())
                    .nightModeEnabled(settings.getNightModeEnabled())
                    .quietStartHour(settings.getQuietStartHour())
                    .quietEndHour(settings.getQuietEndHour())
                    .promotionEnabled(settings.getPromotionEnabled())
                    .timezone(settings.getTimezone())
                    .language(settings.getLanguage())
                    .typeSettings(settings.getTypeSettings())
                    .createdAt(settings.getCreatedAt())
                    .updatedAt(settings.getUpdatedAt())
                    .build();
        }
    }
    
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class UnreadCountResponse {
        private int unreadCount;
    }
} 