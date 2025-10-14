package com.carcare.domain.notification.scheduler;

import com.carcare.domain.notification.entity.Notification;
import com.carcare.domain.notification.service.EmailService;
import com.carcare.domain.notification.service.NotificationService;
import com.carcare.domain.notification.service.NotificationTemplateService;
import com.carcare.domain.notification.service.SmsService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.scheduling.annotation.Async;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * 알림 발송 스케줄러
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class NotificationScheduler {
    
    private final NotificationService notificationService;
    private final NotificationTemplateService templateService;
    @Qualifier("notificationSmsService")
    private final SmsService smsService;
    private final EmailService emailService;
    
    /**
     * 대기 중인 알림 처리 (매 1분마다 실행)
     */
    @Scheduled(fixedRate = 60000) // 1분마다
    @Async
    public void processPendingNotifications() {
        log.debug("대기 중인 알림 처리 스케줄러 시작");
        
        try {
            // 발송 대기 중인 알림들을 조회 (최대 100개)
            // 실제로는 NotificationRepository에서 발송 대기 상태의 알림을 조회해야 함
            // 현재는 간단한 예시로 구현
            
            log.debug("대기 중인 알림 처리 완료");
            
        } catch (Exception e) {
            log.error("대기 중인 알림 처리 중 오류 발생", e);
        }
    }
    
    /**
     * 예약 리마인더 발송 (매 시간마다 실행)
     */
    @Scheduled(cron = "0 0 * * * *") // 매 시간 정각
    @Async
    public void sendReservationReminders() {
        log.info("예약 리마인더 발송 스케줄러 시작");
        
        try {
            LocalDateTime now = LocalDateTime.now();
            LocalDateTime reminderTime = now.plusHours(2); // 2시간 후 예약에 대한 리마인더
            
            // TODO: 2시간 후 예약이 있는 사용자들을 조회하여 리마인더 발송
            // ReservationService를 통해 해당 시간대 예약들을 조회하고
            // 각 예약에 대해 리마인더 알림 생성
            
            log.info("예약 리마인더 발송 완료");
            
        } catch (Exception e) {
            log.error("예약 리마인더 발송 중 오류 발생", e);
        }
    }
    
    /**
     * 오래된 알림 정리 (매일 새벽 3시 실행)
     */
    @Scheduled(cron = "0 0 3 * * *") // 매일 새벽 3시
    @Async
    public void cleanupOldNotifications() {
        log.info("오래된 알림 정리 스케줄러 시작");
        
        try {
            // 90일 이전의 알림들을 삭제
            notificationService.cleanupOldNotifications(90);
            
            log.info("오래된 알림 정리 완료");
            
        } catch (Exception e) {
            log.error("오래된 알림 정리 중 오류 발생", e);
        }
    }
    
    /**
     * 템플릿 기반 알림 발송
     */
    @Async
    public void sendTemplatedNotification(Long userId, Notification.NotificationType type, 
                                        String channel, Map<String, Object> variables) {
        
        log.info("템플릿 기반 알림 발송 시작 - userId: {}, type: {}, channel: {}", userId, type, channel);
        
        try {
            // 사용자 알림 설정 확인
            if (!notificationService.shouldReceiveNotification(userId, type, channel)) {
                log.info("사용자 알림 설정으로 인해 발송 제외 - userId: {}, type: {}, channel: {}", userId, type, channel);
                return;
            }
            
            // 템플릿 렌더링
            NotificationTemplateService.TemplateRenderResult renderResult = 
                    templateService.renderTemplate(type.name(), channel, "ko", variables);
            
            if (!renderResult.isSuccess()) {
                log.error("템플릿 렌더링 실패 - userId: {}, type: {}, channel: {}, error: {}", 
                         userId, type, channel, renderResult.getErrorMessage());
                return;
            }
            
            // 채널별 발송
            boolean sendSuccess = false;
            String errorMessage = null;
            
            switch (channel.toUpperCase()) {
                case "SMS":
                    SmsService.SmsResult smsResult = smsService.sendSmsToUser(
                            userId, renderResult.getRenderedContent(), null, null);
                    sendSuccess = smsResult.isSuccess();
                    errorMessage = smsResult.getErrorMessage();
                    break;
                    
                case "EMAIL":
                    EmailService.EmailResult emailResult = emailService.sendEmailToUser(
                            userId, renderResult.getRenderedSubject(), renderResult.getRenderedContent(), true);
                    sendSuccess = emailResult.isSuccess();
                    errorMessage = emailResult.getErrorMessage();
                    break;
                    
                case "IN_APP":
                    // 인앱 알림 생성
                    notificationService.createNotification(
                            userId, type, 
                            renderResult.getRenderedTitle(), 
                            renderResult.getRenderedContent(),
                            null, null);
                    sendSuccess = true;
                    break;
                    
                default:
                    log.warn("지원하지 않는 알림 채널: {}", channel);
                    return;
            }
            
            if (sendSuccess) {
                log.info("템플릿 기반 알림 발송 성공 - userId: {}, type: {}, channel: {}", userId, type, channel);
            } else {
                log.error("템플릿 기반 알림 발송 실패 - userId: {}, type: {}, channel: {}, error: {}", 
                         userId, type, channel, errorMessage);
            }
            
        } catch (Exception e) {
            log.error("템플릿 기반 알림 발송 중 예외 발생 - userId: {}, type: {}, channel: {}", 
                     userId, type, channel, e);
        }
    }
    
    /**
     * 예약 확인 알림 발송
     */
    @Async
    public void sendReservationConfirmation(Long userId, Long reservationId, Map<String, Object> reservationData) {
        
        log.info("예약 확인 알림 발송 - userId: {}, reservationId: {}", userId, reservationId);
        
        Map<String, Object> variables = new HashMap<>();
        variables.put("appName", "Car Center");
        variables.putAll(reservationData);
        
        // SMS 발송
        sendTemplatedNotification(userId, Notification.NotificationType.RESERVATION_CONFIRMED, "SMS", variables);
        
        // 이메일 발송
        sendTemplatedNotification(userId, Notification.NotificationType.RESERVATION_CONFIRMED, "EMAIL", variables);
        
        // 인앱 알림 생성
        sendTemplatedNotification(userId, Notification.NotificationType.RESERVATION_CONFIRMED, "IN_APP", variables);
    }
    
    /**
     * 견적서 준비 완료 알림 발송
     */
    @Async
    public void sendQuoteReady(Long userId, Long quoteId, Map<String, Object> quoteData) {
        
        log.info("견적서 준비 완료 알림 발송 - userId: {}, quoteId: {}", userId, quoteId);
        
        Map<String, Object> variables = new HashMap<>();
        variables.put("appName", "Car Center");
        variables.putAll(quoteData);
        
        // SMS 발송
        sendTemplatedNotification(userId, Notification.NotificationType.QUOTE_READY, "SMS", variables);
        
        // 이메일 발송
        sendTemplatedNotification(userId, Notification.NotificationType.QUOTE_READY, "EMAIL", variables);
        
        // 인앱 알림 생성
        sendTemplatedNotification(userId, Notification.NotificationType.QUOTE_READY, "IN_APP", variables);
    }
    
    /**
     * 서비스 완료 알림 발송
     */
    @Async
    public void sendServiceCompleted(Long userId, Long reservationId, Map<String, Object> serviceData) {
        
        log.info("서비스 완료 알림 발송 - userId: {}, reservationId: {}", userId, reservationId);
        
        Map<String, Object> variables = new HashMap<>();
        variables.put("appName", "Car Center");
        variables.putAll(serviceData);
        
        // SMS 발송
        sendTemplatedNotification(userId, Notification.NotificationType.SERVICE_COMPLETED, "SMS", variables);
        
        // 이메일 발송
        sendTemplatedNotification(userId, Notification.NotificationType.SERVICE_COMPLETED, "EMAIL", variables);
        
        // 인앱 알림 생성
        sendTemplatedNotification(userId, Notification.NotificationType.SERVICE_COMPLETED, "IN_APP", variables);
    }
    
    /**
     * 결제 완료 알림 발송
     */
    @Async
    public void sendPaymentCompleted(Long userId, Long paymentId, Map<String, Object> paymentData) {
        
        log.info("결제 완료 알림 발송 - userId: {}, paymentId: {}", userId, paymentId);
        
        Map<String, Object> variables = new HashMap<>();
        variables.put("appName", "Car Center");
        variables.putAll(paymentData);
        
        // SMS 발송
        sendTemplatedNotification(userId, Notification.NotificationType.PAYMENT_COMPLETED, "SMS", variables);
        
        // 이메일 발송
        sendTemplatedNotification(userId, Notification.NotificationType.PAYMENT_COMPLETED, "EMAIL", variables);
        
        // 인앱 알림 생성
        sendTemplatedNotification(userId, Notification.NotificationType.PAYMENT_COMPLETED, "IN_APP", variables);
    }
} 