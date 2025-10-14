package com.carcare.domain.notification.entity;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.Map;

/**
 * 알림 템플릿 엔티티
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class NotificationTemplate {
    
    private Long id;
    private String templateUuid;
    private String name;
    private String type;
    private NotificationChannel channel;
    private String language;
    private String subject;
    private String titleTemplate;
    private String contentTemplate;
    private Map<String, Object> variables;
    private Boolean isActive;
    private Integer version;
    private String description;
    private Long createdBy;
    private Long updatedBy;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    
    /**
     * 알림 채널 enum
     */
    public enum NotificationChannel {
        SMS("SMS"),
        EMAIL("이메일"),
        PUSH("푸시 알림"),
        IN_APP("인앱 알림");
        
        private final String description;
        
        NotificationChannel(String description) {
            this.description = description;
        }
        
        public String getDescription() {
            return description;
        }
    }
    
    /**
     * 기본 활성 템플릿 생성
     */
    public static NotificationTemplate createDefault(String name, String type, NotificationChannel channel, 
                                                   String titleTemplate, String contentTemplate) {
        return NotificationTemplate.builder()
                .templateUuid(java.util.UUID.randomUUID().toString())
                .name(name)
                .type(type)
                .channel(channel)
                .language("ko")
                .titleTemplate(titleTemplate)
                .contentTemplate(contentTemplate)
                .isActive(true)
                .version(1)
                .createdAt(LocalDateTime.now())
                .updatedAt(LocalDateTime.now())
                .build();
    }
    
    /**
     * 템플릿 복사 (새 버전 생성)
     */
    public NotificationTemplate createNewVersion() {
        return NotificationTemplate.builder()
                .templateUuid(java.util.UUID.randomUUID().toString())
                .name(this.name)
                .type(this.type)
                .channel(this.channel)
                .language(this.language)
                .subject(this.subject)
                .titleTemplate(this.titleTemplate)
                .contentTemplate(this.contentTemplate)
                .variables(this.variables)
                .isActive(true)
                .version(this.version + 1)
                .description(this.description)
                .createdAt(LocalDateTime.now())
                .updatedAt(LocalDateTime.now())
                .build();
    }
} 