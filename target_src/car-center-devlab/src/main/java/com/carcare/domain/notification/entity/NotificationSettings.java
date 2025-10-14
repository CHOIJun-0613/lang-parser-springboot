package com.carcare.domain.notification.entity;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.Map;

/**
 * 알림 설정 엔티티
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class NotificationSettings {
    
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
    
    /**
     * 기본 설정값으로 NotificationSettings 생성
     */
    public static NotificationSettings createDefault(Long userId) {
        return NotificationSettings.builder()
                .userId(userId)
                .smsEnabled(true)
                .pushEnabled(true)
                .emailEnabled(true)
                .inAppEnabled(true)
                .nightModeEnabled(true)
                .quietStartHour(22)
                .quietEndHour(8)
                .promotionEnabled(false)
                .timezone("Asia/Seoul")
                .language("ko")
                .createdAt(LocalDateTime.now())
                .updatedAt(LocalDateTime.now())
                .build();
    }
    
    /**
     * 야간 시간대 확인
     */
    public boolean isQuietTime(int currentHour) {
        if (!nightModeEnabled) {
            return false;
        }
        
        if (quietStartHour <= quietEndHour) {
            // 같은 날 내의 시간대 (예: 22시 ~ 8시가 다음날)
            return currentHour >= quietStartHour || currentHour < quietEndHour;
        } else {
            // 날짜를 넘나드는 시간대 (예: 8시 ~ 22시)
            return currentHour >= quietStartHour && currentHour < quietEndHour;
        }
    }
} 