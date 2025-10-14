package com.carcare.domain.notification.repository;

import com.carcare.domain.notification.entity.Notification;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

/**
 * 알림 Repository
 */
@Mapper
public interface NotificationRepository {
    
    /**
     * 알림 생성
     */
    void insert(Notification notification);
    
    /**
     * 알림 조회 (ID 기준)
     */
    Optional<Notification> findById(@Param("id") Long id);
    
    /**
     * 알림 조회 (UUID 기준)
     */
    Optional<Notification> findByNotificationUuid(@Param("notificationUuid") String notificationUuid);
    
    /**
     * 사용자별 알림 목록 조회
     */
    List<Notification> findByUserId(@Param("userId") Long userId,
                                   @Param("offset") int offset,
                                   @Param("limit") int limit);
    
    /**
     * 사용자별 읽지 않은 알림 개수 조회
     */
    int countUnreadByUserId(@Param("userId") Long userId);
    
    /**
     * 알림 읽음 처리
     */
    void markAsRead(@Param("id") Long id);
    
    /**
     * 사용자의 모든 알림 읽음 처리
     */
    void markAllAsReadByUserId(@Param("userId") Long userId);
    
    /**
     * 알림 삭제
     */
    void deleteById(@Param("id") Long id);
    
    /**
     * 특정 기간 이전의 알림 삭제 (정리용)
     */
    void deleteOldNotifications(@Param("beforeDate") LocalDateTime beforeDate);
    
    /**
     * 발송 대기 중인 알림 조회 (스케줄러용)
     */
    List<Notification> findPendingNotifications(@Param("limit") int limit);
    
    /**
     * 관련 엔티티별 알림 조회
     */
    List<Notification> findByRelatedEntity(@Param("entityType") String entityType,
                                          @Param("entityId") Long entityId);
} 