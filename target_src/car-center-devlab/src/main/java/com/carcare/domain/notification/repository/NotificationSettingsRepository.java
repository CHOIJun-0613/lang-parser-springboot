package com.carcare.domain.notification.repository;

import com.carcare.domain.notification.entity.NotificationSettings;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.Optional;

/**
 * 알림 설정 Repository
 */
@Mapper
public interface NotificationSettingsRepository {
    
    /**
     * 알림 설정 생성
     */
    void insert(NotificationSettings settings);
    
    /**
     * 사용자별 알림 설정 조회
     */
    Optional<NotificationSettings> findByUserId(@Param("userId") Long userId);
    
    /**
     * 알림 설정 업데이트
     */
    void update(NotificationSettings settings);
    
    /**
     * 알림 설정 삭제
     */
    void deleteByUserId(@Param("userId") Long userId);
    
    /**
     * 사용자별 알림 설정 존재 여부 확인
     */
    boolean existsByUserId(@Param("userId") Long userId);
} 