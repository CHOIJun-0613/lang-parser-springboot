package com.carcare.domain.notification.repository;

import com.carcare.domain.notification.entity.NotificationTemplate;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;
import java.util.Optional;

/**
 * 알림 템플릿 Repository
 */
@Mapper
public interface NotificationTemplateRepository {
    
    /**
     * 템플릿 생성
     */
    void insert(NotificationTemplate template);
    
    /**
     * 템플릿 조회 (ID)
     */
    Optional<NotificationTemplate> findById(@Param("id") Long id);
    
    /**
     * 템플릿 조회 (UUID)
     */
    Optional<NotificationTemplate> findByTemplateUuid(@Param("templateUuid") String templateUuid);
    
    /**
     * 활성 템플릿 조회 (타입 + 채널 + 언어)
     */
    Optional<NotificationTemplate> findActiveTemplate(@Param("type") String type,
                                                     @Param("channel") String channel,
                                                     @Param("language") String language);
    
    /**
     * 타입별 템플릿 목록 조회
     */
    List<NotificationTemplate> findByType(@Param("type") String type);
    
    /**
     * 채널별 템플릿 목록 조회
     */
    List<NotificationTemplate> findByChannel(@Param("channel") String channel);
    
    /**
     * 전체 템플릿 목록 조회
     */
    List<NotificationTemplate> findAll(@Param("offset") int offset, @Param("limit") int limit);
    
    /**
     * 활성 템플릿만 조회
     */
    List<NotificationTemplate> findActiveTemplates(@Param("offset") int offset, @Param("limit") int limit);
    
    /**
     * 검색 조건으로 템플릿 조회
     */
    List<NotificationTemplate> searchTemplates(@Param("keyword") String keyword,
                                              @Param("type") String type,
                                              @Param("channel") String channel,
                                              @Param("language") String language,
                                              @Param("isActive") Boolean isActive,
                                              @Param("offset") int offset,
                                              @Param("limit") int limit);
    
    /**
     * 템플릿 개수 조회
     */
    int countTemplates(@Param("keyword") String keyword,
                      @Param("type") String type,
                      @Param("channel") String channel,
                      @Param("language") String language,
                      @Param("isActive") Boolean isActive);
    
    /**
     * 템플릿 업데이트
     */
    void update(NotificationTemplate template);
    
    /**
     * 템플릿 활성화/비활성화
     */
    void updateActiveStatus(@Param("id") Long id, @Param("isActive") Boolean isActive);
    
    /**
     * 같은 타입/채널의 다른 템플릿 비활성화 (새 템플릿 활성화 시 사용)
     */
    void deactivateOtherTemplates(@Param("type") String type,
                                 @Param("channel") String channel,
                                 @Param("language") String language,
                                 @Param("excludeId") Long excludeId);
    
    /**
     * 템플릿 삭제
     */
    void deleteById(@Param("id") Long id);
    
    /**
     * 템플릿 존재 여부 확인
     */
    boolean existsByTypeAndChannel(@Param("type") String type, @Param("channel") String channel);
} 