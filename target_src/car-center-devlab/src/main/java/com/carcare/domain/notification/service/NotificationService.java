package com.carcare.domain.notification.service;

import com.carcare.domain.notification.entity.Notification;
import com.carcare.domain.notification.entity.NotificationSettings;
import com.carcare.domain.notification.repository.NotificationRepository;
import com.carcare.domain.notification.repository.NotificationSettingsRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * 알림 서비스
 */
@Slf4j
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class NotificationService {
    
    private final NotificationRepository notificationRepository;
    private final NotificationSettingsRepository notificationSettingsRepository;
    
    /**
     * 알림 생성
     */
    @Transactional
    public Notification createNotification(Long userId, Notification.NotificationType type,
                                         String title, String message, 
                                         String relatedEntityType, Long relatedEntityId) {
        
        log.info("알림 생성 요청 - userId: {}, type: {}, title: {}", userId, type, title);
        
        Notification notification = Notification.builder()
                .notificationUuid(UUID.randomUUID().toString())
                .userId(userId)
                .type(type)
                .title(title)
                .message(message)
                .isRead(false)
                .relatedEntityType(relatedEntityType)
                .relatedEntityId(relatedEntityId)
                .createdAt(LocalDateTime.now())
                .build();
        
        notificationRepository.insert(notification);
        
        log.info("알림 생성 완료 - id: {}, uuid: {}", notification.getId(), notification.getNotificationUuid());
        return notification;
    }
    
    /**
     * 사용자별 알림 목록 조회
     */
    public List<Notification> getNotificationsByUserId(Long userId, int page, int size) {
        int offset = page * size;
        return notificationRepository.findByUserId(userId, offset, size);
    }
    
    /**
     * 읽지 않은 알림 개수 조회
     */
    public int getUnreadCount(Long userId) {
        return notificationRepository.countUnreadByUserId(userId);
    }
    
    /**
     * 알림 읽음 처리
     */
    @Transactional
    public void markAsRead(Long notificationId) {
        notificationRepository.markAsRead(notificationId);
        log.info("알림 읽음 처리 완료 - id: {}", notificationId);
    }
    
    /**
     * 모든 알림 읽음 처리
     */
    @Transactional
    public void markAllAsRead(Long userId) {
        notificationRepository.markAllAsReadByUserId(userId);
        log.info("모든 알림 읽음 처리 완료 - userId: {}", userId);
    }
    
    /**
     * 알림 삭제
     */
    @Transactional
    public void deleteNotification(Long notificationId) {
        notificationRepository.deleteById(notificationId);
        log.info("알림 삭제 완료 - id: {}", notificationId);
    }
    
    /**
     * 알림 조회 (ID)
     */
    public Optional<Notification> getNotificationById(Long id) {
        return notificationRepository.findById(id);
    }
    
    /**
     * 알림 조회 (UUID)
     */
    public Optional<Notification> getNotificationByUuid(String uuid) {
        return notificationRepository.findByNotificationUuid(uuid);
    }
    
    /**
     * 관련 엔티티별 알림 조회
     */
    public List<Notification> getNotificationsByRelatedEntity(String entityType, Long entityId) {
        return notificationRepository.findByRelatedEntity(entityType, entityId);
    }
    
    /**
     * 오래된 알림 정리 (배치 작업용)
     */
    @Transactional
    public void cleanupOldNotifications(int daysToKeep) {
        LocalDateTime cutoffDate = LocalDateTime.now().minusDays(daysToKeep);
        notificationRepository.deleteOldNotifications(cutoffDate);
        log.info("오래된 알림 정리 완료 - 기준일: {}", cutoffDate);
    }
    
    /**
     * 사용자별 알림 설정 조회
     */
    @Transactional
    public NotificationSettings getNotificationSettings(Long userId) {
        return notificationSettingsRepository.findByUserId(userId)
                .orElseGet(() -> {
                    // 설정이 없으면 기본 설정으로 생성
                    NotificationSettings defaultSettings = NotificationSettings.createDefault(userId);
                    createNotificationSettings(defaultSettings);
                    return defaultSettings;
                });
    }
    
    /**
     * 알림 설정 생성
     */
    @Transactional
    public NotificationSettings createNotificationSettings(NotificationSettings settings) {
        notificationSettingsRepository.insert(settings);
        log.info("알림 설정 생성 완료 - userId: {}", settings.getUserId());
        return settings;
    }
    
    /**
     * 알림 설정 업데이트
     */
    @Transactional
    public NotificationSettings updateNotificationSettings(NotificationSettings settings) {
        settings.setUpdatedAt(LocalDateTime.now());
        notificationSettingsRepository.update(settings);
        log.info("알림 설정 업데이트 완료 - userId: {}", settings.getUserId());
        return settings;
    }
    
    /**
     * 사용자가 특정 타입의 알림을 수신할지 확인
     */
    @Transactional
    public boolean shouldReceiveNotification(Long userId, Notification.NotificationType type, String channel) {
        NotificationSettings settings = getNotificationSettings(userId);
        
        // 기본 채널별 설정 확인
        switch (channel.toUpperCase()) {
            case "SMS":
                if (!settings.getSmsEnabled()) return false;
                break;
            case "EMAIL":
                if (!settings.getEmailEnabled()) return false;
                break;
            case "PUSH":
                if (!settings.getPushEnabled()) return false;
                break;
            case "IN_APP":
                if (!settings.getInAppEnabled()) return false;
                break;
        }
        
        // 프로모션 알림 타입 체크
        if (type == Notification.NotificationType.PROMOTION && !settings.getPromotionEnabled()) {
            return false;
        }
        
        // 야간 시간대 체크
        int currentHour = LocalDateTime.now().getHour();
        if (settings.isQuietTime(currentHour)) {
            return false;
        }
        
        return true;
    }
} 