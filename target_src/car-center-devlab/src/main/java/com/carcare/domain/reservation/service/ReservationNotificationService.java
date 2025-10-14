package com.carcare.domain.reservation.service;

import com.carcare.domain.reservation.entity.Reservation;
import com.carcare.domain.reservation.dto.ReservationDto;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

/**
 * 예약 알림 서비스
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ReservationNotificationService {

    /**
     * 예약 생성 알림
     */
    public void notifyReservationCreated(ReservationDto.Response reservation) {
        log.info("예약 생성 알림 발송: 예약ID={}, 고객={}", 
            reservation.getId(), reservation.getUserName());
        
        // TODO: 실제 알림 발송 구현
        // - 고객에게 SMS/이메일 발송
        // - 정비소에게 새 예약 알림
        
        sendCustomerNotification(
            reservation.getUserId(),
            "예약 확인",
            String.format("예약이 성공적으로 생성되었습니다. 예약번호: %s, 일시: %s",
                reservation.getReservationUuid(),
                reservation.getScheduledDate())
        );
        
        sendServiceCenterNotification(
            reservation.getServiceCenterId(),
            "새 예약 접수",
            String.format("새로운 예약이 접수되었습니다. 고객: %s, 서비스: %s",
                reservation.getUserName(),
                reservation.getServiceTypeName())
        );
    }

    /**
     * 예약 상태 변경 알림
     */
    public void notifyReservationStatusChanged(ReservationDto.Response reservation, 
                                             Reservation.ReservationStatus previousStatus) {
        log.info("예약 상태 변경 알림 발송: 예약ID={}, {} -> {}", 
            reservation.getId(), previousStatus, reservation.getStatus());
        
        String statusMessage = getStatusMessage(reservation.getStatus());
        
        sendCustomerNotification(
            reservation.getUserId(),
            "예약 상태 변경",
            String.format("예약 상태가 변경되었습니다. 현재 상태: %s (%s)",
                reservation.getStatusDescription(),
                statusMessage)
        );
        
        // 완료 시 추가 안내
        if (reservation.getStatus() == Reservation.ReservationStatus.COMPLETED) {
            sendCustomerNotification(
                reservation.getUserId(),
                "정비 완료",
                "정비가 완료되었습니다. 차량을 찾으러 오시기 바랍니다."
            );
        }
    }

    /**
     * 예약 취소 알림
     */
    public void notifyReservationCancelled(ReservationDto.Response reservation, String reason) {
        log.info("예약 취소 알림 발송: 예약ID={}, 사유={}", reservation.getId(), reason);
        
        sendCustomerNotification(
            reservation.getUserId(),
            "예약 취소 확인",
            String.format("예약이 취소되었습니다. 취소 사유: %s", 
                reason != null ? reason : "고객 요청")
        );
        
        sendServiceCenterNotification(
            reservation.getServiceCenterId(),
            "예약 취소",
            String.format("예약이 취소되었습니다. 고객: %s, 취소 사유: %s",
                reservation.getUserName(),
                reason != null ? reason : "고객 요청")
        );
    }

    /**
     * 예약 시간 임박 알림 (예약 1시간 전)
     */
    public void notifyReservationReminder(ReservationDto.Response reservation) {
        log.info("예약 알림 발송: 예약ID={}", reservation.getId());
        
        sendCustomerNotification(
            reservation.getUserId(),
            "예약 알림",
            String.format("예약 시간이 1시간 남았습니다. 정비소: %s, 시간: %s",
                reservation.getServiceCenterName(),
                reservation.getScheduledDate())
        );
    }

    /**
     * 고객 알림 발송
     */
    private void sendCustomerNotification(Long userId, String title, String message) {
        log.debug("고객 알림 발송: 사용자={}, 제목={}", userId, title);
        
        // TODO: 실제 알림 발송 구현
        // 1. SMS 발송
        // 2. 이메일 발송  
        // 3. 푸시 알림 발송
        // 4. 앱 내 알림 저장
        
        // 현재는 로그만 출력
        log.info("📱 고객 알림 - 사용자: {}, 제목: {}, 내용: {}", userId, title, message);
    }

    /**
     * 정비소 알림 발송
     */
    private void sendServiceCenterNotification(Long serviceCenterId, String title, String message) {
        log.debug("정비소 알림 발송: 정비소={}, 제목={}", serviceCenterId, title);
        
        // TODO: 실제 알림 발송 구현
        // 1. 정비소 관리자에게 이메일 발송
        // 2. 정비소 대시보드 알림
        // 3. SMS 발송 (긴급한 경우)
        
        // 현재는 로그만 출력
        log.info("🔧 정비소 알림 - 정비소: {}, 제목: {}, 내용: {}", serviceCenterId, title, message);
    }

    /**
     * 상태별 메시지 생성
     */
    private String getStatusMessage(Reservation.ReservationStatus status) {
        return switch (status) {
            case PENDING -> "예약이 접수되었습니다.";
            case CONFIRMED -> "예약이 확정되었습니다.";
            case IN_PROGRESS -> "정비가 시작되었습니다.";
            case COMPLETED -> "정비가 완료되었습니다.";
            case CANCELLED -> "예약이 취소되었습니다.";
        };
    }
} 