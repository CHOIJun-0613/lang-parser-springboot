package com.carcare.domain.notification.controller;

import com.carcare.common.dto.ApiResponse;
import com.carcare.common.util.ResponseUtils;
import com.carcare.domain.notification.dto.NotificationDto;
import com.carcare.domain.notification.entity.Notification;
import com.carcare.domain.notification.entity.NotificationSettings;
import com.carcare.domain.notification.service.NotificationService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.stream.Collectors;

/**
 * 알림 관리 컨트롤러
 */
@RestController
@RequestMapping("/api/v1/notifications")
@Tag(name = "Notification", description = "알림 관리 API")
@RequiredArgsConstructor
public class NotificationController {
    
    private final NotificationService notificationService;
    
    /**
     * 전체 알림 목록 조회 (관리자용)
     */
    @GetMapping
    @Operation(summary = "전체 알림 목록 조회", description = "모든 알림을 페이징하여 조회합니다 (관리자용)")
    public ResponseEntity<ApiResponse<NotificationDto.ListResponse>> getAllNotifications(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        
        // 임시로 빈 목록 반환 (실제 구현 시 관리자 권한 확인 필요)
        NotificationDto.ListResponse response = NotificationDto.ListResponse.builder()
                .page(page)
                .size(size)
                .totalCount(0)
                .unreadCount(0)
                .notifications(List.of())
                .build();
        
        return ResponseEntity.ok(ResponseUtils.success("전체 알림 목록 조회 성공", response));
    }
    
    /**
     * 사용자별 알림 목록 조회
     */
    @GetMapping("/users/{userId}")
    @Operation(summary = "사용자별 알림 목록 조회", description = "특정 사용자의 알림 목록을 페이징하여 조회합니다")
    public ResponseEntity<ApiResponse<NotificationDto.ListResponse>> getUserNotifications(
            @PathVariable Long userId,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        
        List<Notification> notifications = notificationService.getNotificationsByUserId(userId, page, size);
        int unreadCount = notificationService.getUnreadCount(userId);
        
        List<NotificationDto.Response> notificationResponses = notifications.stream()
                .map(NotificationDto.Response::from)
                .collect(Collectors.toList());
        
        NotificationDto.ListResponse response = NotificationDto.ListResponse.builder()
                .page(page)
                .size(size)
                .totalCount(notifications.size())
                .unreadCount(unreadCount)
                .notifications(notificationResponses)
                .build();
        
        return ResponseEntity.ok(ResponseUtils.success("알림 목록 조회 성공", response));
    }
    
    /**
     * 읽지 않은 알림 개수 조회
     */
    @GetMapping("/users/{userId}/unread-count")
    @Operation(summary = "읽지 않은 알림 개수 조회", description = "특정 사용자의 읽지 않은 알림 개수를 조회합니다")
    public ResponseEntity<ApiResponse<NotificationDto.UnreadCountResponse>> getUnreadCount(@PathVariable Long userId) {
        
        int unreadCount = notificationService.getUnreadCount(userId);
        
        NotificationDto.UnreadCountResponse response = NotificationDto.UnreadCountResponse.builder()
                .unreadCount(unreadCount)
                .build();
        
        return ResponseEntity.ok(ResponseUtils.success("읽지 않은 알림 개수 조회 성공", response));
    }
    
    /**
     * 알림 생성
     */
    @PostMapping
    @Operation(summary = "알림 생성", description = "새로운 알림을 생성합니다")
    public ResponseEntity<ApiResponse<NotificationDto.Response>> createNotification(
            @RequestBody NotificationDto.CreateRequest request) {
        
        Notification.NotificationType type = Notification.NotificationType.valueOf(request.getType());
        
        Notification notification = notificationService.createNotification(
                request.getUserId(),
                type,
                request.getTitle(),
                request.getMessage(),
                request.getRelatedEntityType(),
                request.getRelatedEntityId()
        );
        
        NotificationDto.Response response = NotificationDto.Response.from(notification);
        return ResponseEntity.ok(ResponseUtils.success("알림 생성 성공", response));
    }
    
    /**
     * 알림 읽음 처리
     */
    @PutMapping("/{notificationId}/read")
    @Operation(summary = "알림 읽음 처리", description = "특정 알림을 읽음 상태로 변경합니다")
    public ResponseEntity<ApiResponse<Void>> markAsRead(@PathVariable Long notificationId) {
        
        notificationService.markAsRead(notificationId);
        return ResponseEntity.ok(ResponseUtils.success("알림 읽음 처리 성공", null));
    }
    
    /**
     * 모든 알림 읽음 처리
     */
    @PutMapping("/users/{userId}/read-all")
    @Operation(summary = "모든 알림 읽음 처리", description = "특정 사용자의 모든 알림을 읽음 상태로 변경합니다")
    public ResponseEntity<ApiResponse<Void>> markAllAsRead(@PathVariable Long userId) {
        
        notificationService.markAllAsRead(userId);
        return ResponseEntity.ok(ResponseUtils.success("모든 알림 읽음 처리 성공", null));
    }
    
    /**
     * 알림 삭제
     */
    @DeleteMapping("/{notificationId}")
    @Operation(summary = "알림 삭제", description = "특정 알림을 삭제합니다")
    public ResponseEntity<ApiResponse<Void>> deleteNotification(@PathVariable Long notificationId) {
        
        notificationService.deleteNotification(notificationId);
        return ResponseEntity.ok(ResponseUtils.success("알림 삭제 성공", null));
    }
    
    /**
     * 알림 설정 조회
     */
    @GetMapping("/users/{userId}/settings")
    @Operation(summary = "알림 설정 조회", description = "특정 사용자의 알림 설정을 조회합니다")
    public ResponseEntity<ApiResponse<NotificationDto.SettingsResponse>> getNotificationSettings(@PathVariable Long userId) {
        
        NotificationSettings settings = notificationService.getNotificationSettings(userId);
        NotificationDto.SettingsResponse response = NotificationDto.SettingsResponse.from(settings);
        
        return ResponseEntity.ok(ResponseUtils.success("알림 설정 조회 성공", response));
    }
    
    /**
     * 알림 설정 업데이트
     */
    @PutMapping("/users/{userId}/settings")
    @Operation(summary = "알림 설정 업데이트", description = "특정 사용자의 알림 설정을 업데이트합니다")
    public ResponseEntity<ApiResponse<NotificationDto.SettingsResponse>> updateNotificationSettings(
            @PathVariable Long userId,
            @RequestBody NotificationDto.SettingsRequest request) {
        
        // 기존 설정 조회
        NotificationSettings existingSettings = notificationService.getNotificationSettings(userId);
        
        // 요청된 값으로 업데이트 (null이 아닌 값만)
        if (request.getSmsEnabled() != null) {
            existingSettings.setSmsEnabled(request.getSmsEnabled());
        }
        if (request.getPushEnabled() != null) {
            existingSettings.setPushEnabled(request.getPushEnabled());
        }
        if (request.getEmailEnabled() != null) {
            existingSettings.setEmailEnabled(request.getEmailEnabled());
        }
        if (request.getInAppEnabled() != null) {
            existingSettings.setInAppEnabled(request.getInAppEnabled());
        }
        if (request.getNightModeEnabled() != null) {
            existingSettings.setNightModeEnabled(request.getNightModeEnabled());
        }
        if (request.getQuietStartHour() != null) {
            existingSettings.setQuietStartHour(request.getQuietStartHour());
        }
        if (request.getQuietEndHour() != null) {
            existingSettings.setQuietEndHour(request.getQuietEndHour());
        }
        if (request.getPromotionEnabled() != null) {
            existingSettings.setPromotionEnabled(request.getPromotionEnabled());
        }
        if (request.getTimezone() != null) {
            existingSettings.setTimezone(request.getTimezone());
        }
        if (request.getLanguage() != null) {
            existingSettings.setLanguage(request.getLanguage());
        }
        if (request.getTypeSettings() != null) {
            existingSettings.setTypeSettings(request.getTypeSettings());
        }
        
        NotificationSettings updatedSettings = notificationService.updateNotificationSettings(existingSettings);
        NotificationDto.SettingsResponse response = NotificationDto.SettingsResponse.from(updatedSettings);
        
        return ResponseEntity.ok(ResponseUtils.success("알림 설정 업데이트 성공", response));
    }
} 