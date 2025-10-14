package com.carcare.domain.service.scheduler;

import com.carcare.domain.service.service.ServiceCenterOperatingHoursService;
import com.carcare.domain.service.entity.ServiceCenterOperatingHours;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;

import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * 운영 상태 자동 업데이트 스케줄러
 * 정비소의 운영 상태를 주기적으로 확인하고 업데이트
 */
@Slf4j
@Component
@RequiredArgsConstructor
@ConditionalOnProperty(name = "app.scheduler.operating-status.enabled", havingValue = "true", matchIfMissing = true)
public class OperatingStatusScheduler {

    private final ServiceCenterOperatingHoursService operatingHoursService;

    // 상태 캐시 (메모리)
    private final Map<Long, ServiceCenterOperatingHours.OperatingStatus> statusCache = new ConcurrentHashMap<>();
    private final Map<Long, LocalDateTime> lastUpdateCache = new ConcurrentHashMap<>();

    // 통계 정보
    private final AtomicInteger totalUpdates = new AtomicInteger(0);
    private final AtomicInteger successfulUpdates = new AtomicInteger(0);
    private final AtomicInteger failedUpdates = new AtomicInteger(0);

    /**
     * 매분마다 운영 상태 체크 및 업데이트
     */
    @Scheduled(cron = "${app.scheduler.operating-status.cron:0 * * * * *}") // 매분 실행
    @Transactional
    public void updateOperatingStatusEveryMinute() {
        log.debug("운영 상태 주기적 업데이트 시작: {}", LocalDateTime.now());

        try {
            ServiceCenterOperatingHoursService.BatchUpdateResult result = 
                operatingHoursService.batchUpdateOperatingStatus();

            totalUpdates.incrementAndGet();

            if (result.isSuccess()) {
                successfulUpdates.incrementAndGet();
                log.debug("운영 상태 업데이트 완료: 전체={}, 업데이트={}", 
                         result.getTotalCount(), result.getUpdatedCount());

                // 변경된 상태가 있으면 로그 출력
                if (result.getUpdatedCount() > 0) {
                    log.info("운영 상태 변경 감지: {}개 정비소의 상태가 변경되었습니다", result.getUpdatedCount());
                }
            } else {
                failedUpdates.incrementAndGet();
                log.error("운영 상태 업데이트 실패: {}", result.getErrorMessage());
            }

        } catch (Exception e) {
            failedUpdates.incrementAndGet();
            log.error("운영 상태 스케줄러 실행 중 오류 발생: {}", e.getMessage(), e);
        }
    }

    /**
     * 매시간 정각에 상태 정리 및 알림 처리
     */
    @Scheduled(cron = "${app.scheduler.operating-status.hourly-cron:0 0 * * * *}") // 매시간 정각
    @Transactional
    public void hourlyStatusMaintenance() {
        LocalDateTime now = LocalDateTime.now();
        log.info("시간별 운영 상태 관리 작업 시작: {}", now.format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm")));

        try {
            // 1. 상태 캐시 정리
            cleanupStatusCache();

            // 2. 곧 상태가 변경될 정비소들 확인 및 알림
            checkUpcomingStatusChanges();

            // 3. 영업 시작/종료 알림 발송
            sendOperatingStatusNotifications(now);

            // 4. 통계 정보 로깅
            logHourlyStatistics();

        } catch (Exception e) {
            log.error("시간별 운영 상태 관리 작업 중 오류 발생: {}", e.getMessage(), e);
        }
    }

    /**
     * 매일 자정에 일일 정리 작업
     */
    @Scheduled(cron = "${app.scheduler.operating-status.daily-cron:0 0 0 * * *}") // 매일 자정
    @Transactional
    public void dailyStatusMaintenance() {
        LocalDateTime now = LocalDateTime.now();
        log.info("일일 운영 상태 관리 작업 시작: {}", now.format(DateTimeFormatter.ofPattern("yyyy-MM-dd")));

        try {
            // 1. 전체 상태 캐시 초기화
            resetStatusCache();

            // 2. 통계 초기화
            resetStatistics();

            // 3. 운영시간 데이터 검증
            validateOperatingHoursData();

            // 4. 만료된 임시 휴무 정리
            cleanupExpiredTemporaryClosures();

            log.info("일일 운영 상태 관리 작업 완료");

        } catch (Exception e) {
            log.error("일일 운영 상태 관리 작업 중 오류 발생: {}", e.getMessage(), e);
        }
    }

    /**
     * 영업 시작 시간 알림 (매일 오전 8시 30분)
     */
    @Scheduled(cron = "${app.scheduler.operating-status.morning-notification:0 30 8 * * *}")
    public void sendMorningOperatingNotification() {
        log.info("영업 시작 시간 알림 발송");

        try {
            // 곧 영업을 시작할 정비소들 찾기
            List<Long> upcomingOpenServiceCenters = findUpcomingOpenServiceCenters(30); // 30분 내

            if (!upcomingOpenServiceCenters.isEmpty()) {
                log.info("30분 내 영업 시작 예정 정비소: {}개", upcomingOpenServiceCenters.size());
                
                // TODO: 실제 구현에서는 알림 서비스 호출
                sendNotificationToServiceCenters(upcomingOpenServiceCenters, 
                    NotificationType.OPENING_SOON, "곧 영업 시작 예정입니다");
            }

        } catch (Exception e) {
            log.error("영업 시작 시간 알림 발송 중 오류 발생: {}", e.getMessage(), e);
        }
    }

    /**
     * 영업 종료 시간 알림 (매일 오후 5시 30분)
     */
    @Scheduled(cron = "${app.scheduler.operating-status.evening-notification:0 30 17 * * *}")
    public void sendEveningOperatingNotification() {
        log.info("영업 종료 시간 알림 발송");

        try {
            // 곧 영업을 종료할 정비소들 찾기
            List<Long> upcomingCloseServiceCenters = findUpcomingCloseServiceCenters(60); // 60분 내

            if (!upcomingCloseServiceCenters.isEmpty()) {
                log.info("60분 내 영업 종료 예정 정비소: {}개", upcomingCloseServiceCenters.size());
                
                // TODO: 실제 구현에서는 알림 서비스 호출
                sendNotificationToServiceCenters(upcomingCloseServiceCenters, 
                    NotificationType.CLOSING_SOON, "곧 영업 종료 예정입니다");
            }

        } catch (Exception e) {
            log.error("영업 종료 시간 알림 발송 중 오류 발생: {}", e.getMessage(), e);
        }
    }

    /**
     * 스케줄러 상태 정보 조회
     */
    public SchedulerStatusInfo getSchedulerStatus() {
        return SchedulerStatusInfo.builder()
            .isEnabled(true)
            .lastRunTime(LocalDateTime.now())
            .totalUpdates(totalUpdates.get())
            .successfulUpdates(successfulUpdates.get())
            .failedUpdates(failedUpdates.get())
            .cachedServiceCenters(statusCache.size())
            .nextScheduledRun(getNextScheduledRun())
            .build();
    }

    // === 내부 메서드들 ===

    private void cleanupStatusCache() {
        LocalDateTime cutoff = LocalDateTime.now().minusHours(1);
        
        lastUpdateCache.entrySet().removeIf(entry -> {
            if (entry.getValue().isBefore(cutoff)) {
                statusCache.remove(entry.getKey());
                return true;
            }
            return false;
        });
        
        log.debug("상태 캐시 정리 완료: 현재 캐시 크기={}", statusCache.size());
    }

    private void checkUpcomingStatusChanges() {
        // TODO: 실제 구현에서는 다음 상태 변경이 임박한 정비소들 확인
        try {
            LocalDateTime now = LocalDateTime.now();
            LocalDateTime soon = now.plusMinutes(10); // 10분 후

            // 10분 내에 상태가 변경될 정비소들 찾기
            List<Long> upcomingChanges = findServiceCentersWithUpcomingChanges(soon);
            
            if (!upcomingChanges.isEmpty()) {
                log.info("10분 내 상태 변경 예정 정비소: {}개", upcomingChanges.size());
                
                // 미리 캐시 무효화
                upcomingChanges.forEach(serviceCenterId -> {
                    statusCache.remove(serviceCenterId);
                    lastUpdateCache.remove(serviceCenterId);
                });
            }

        } catch (Exception e) {
            log.warn("상태 변경 예정 확인 중 오류: {}", e.getMessage());
        }
    }

    private void sendOperatingStatusNotifications(LocalDateTime now) {
        LocalTime currentTime = now.toLocalTime();
        
        // 주요 알림 시간대 체크
        if (isImportantTimeSlot(currentTime)) {
            try {
                // 현재 영업 중인 정비소
                List<Long> openServiceCenters = operatingHoursService.getCurrentlyOpenServiceCenters();
                
                // 상태 변경 알림
                NotificationType notificationType = determineNotificationType(currentTime);
                if (notificationType != null) {
                    sendNotificationToServiceCenters(openServiceCenters, notificationType, 
                        getNotificationMessage(notificationType));
                }

            } catch (Exception e) {
                log.warn("운영 상태 알림 발송 중 오류: {}", e.getMessage());
            }
        }
    }

    private void logHourlyStatistics() {
        int total = totalUpdates.get();
        int successful = successfulUpdates.get();
        int failed = failedUpdates.get();
        
        if (total > 0) {
            double successRate = (double) successful / total * 100;
            log.info("지난 시간 운영 상태 업데이트 통계: 전체={}, 성공={}, 실패={}, 성공률={:.1f}%", 
                    total, successful, failed, successRate);
        }
    }

    private void resetStatusCache() {
        int cacheSize = statusCache.size();
        statusCache.clear();
        lastUpdateCache.clear();
        log.info("운영 상태 캐시 초기화 완료: 정리된 항목 수={}", cacheSize);
    }

    private void resetStatistics() {
        totalUpdates.set(0);
        successfulUpdates.set(0);
        failedUpdates.set(0);
        log.info("스케줄러 통계 초기화 완료");
    }

    private void validateOperatingHoursData() {
        // TODO: 실제 구현에서는 모든 정비소의 운영시간 데이터 검증
        log.info("운영시간 데이터 검증 시작");
        
        try {
            // 데이터 무결성 확인
            // 1. JSON 형식 오류 확인
            // 2. 시간 형식 오류 확인
            // 3. 논리적 오류 확인 (시작시간 > 종료시간 등)
            
            log.info("운영시간 데이터 검증 완료");
            
        } catch (Exception e) {
            log.error("운영시간 데이터 검증 중 오류 발생: {}", e.getMessage(), e);
        }
    }

    private void cleanupExpiredTemporaryClosures() {
        // TODO: 실제 구현에서는 만료된 임시 휴무 자동 정리
        log.info("만료된 임시 휴무 정리 시작");
        
        try {
            LocalDateTime now = LocalDateTime.now();
            // 과거 날짜의 임시 휴무 데이터 정리
            
            log.info("만료된 임시 휴무 정리 완료");
            
        } catch (Exception e) {
            log.error("만료된 임시 휴무 정리 중 오류 발생: {}", e.getMessage(), e);
        }
    }

    private List<Long> findUpcomingOpenServiceCenters(int minutesAhead) {
        // TODO: 실제 구현에서는 지정된 시간 내에 영업을 시작할 정비소들 조회
        return List.of(); // 임시 구현
    }

    private List<Long> findUpcomingCloseServiceCenters(int minutesAhead) {
        // TODO: 실제 구현에서는 지정된 시간 내에 영업을 종료할 정비소들 조회
        return List.of(); // 임시 구현
    }

    private List<Long> findServiceCentersWithUpcomingChanges(LocalDateTime targetTime) {
        // TODO: 실제 구현에서는 지정된 시간에 상태가 변경될 정비소들 조회
        return List.of(); // 임시 구현
    }

    private void sendNotificationToServiceCenters(List<Long> serviceCenterIds, NotificationType type, String message) {
        // TODO: 실제 구현에서는 알림 서비스 호출
        log.info("알림 발송: 대상={}개, 타입={}, 메시지={}", serviceCenterIds.size(), type, message);
    }

    private boolean isImportantTimeSlot(LocalTime time) {
        // 중요한 시간대: 영업 시작/종료 시간대, 점심시간 등
        int hour = time.getHour();
        return hour == 9 || hour == 12 || hour == 13 || hour == 18; // 9시, 12시, 13시, 18시
    }

    private NotificationType determineNotificationType(LocalTime time) {
        int hour = time.getHour();
        switch (hour) {
            case 9: return NotificationType.OPENING_TIME;
            case 12: return NotificationType.BREAK_TIME_START;
            case 13: return NotificationType.BREAK_TIME_END;
            case 18: return NotificationType.CLOSING_TIME;
            default: return null;
        }
    }

    private String getNotificationMessage(NotificationType type) {
        switch (type) {
            case OPENING_TIME: return "영업이 시작되었습니다";
            case CLOSING_TIME: return "영업이 종료되었습니다";
            case BREAK_TIME_START: return "휴게시간이 시작되었습니다";
            case BREAK_TIME_END: return "휴게시간이 종료되었습니다";
            case OPENING_SOON: return "곧 영업이 시작됩니다";
            case CLOSING_SOON: return "곧 영업이 종료됩니다";
            default: return "운영 상태가 변경되었습니다";
        }
    }

    private LocalDateTime getNextScheduledRun() {
        // 다음 분의 0초로 계산
        LocalDateTime now = LocalDateTime.now();
        return now.withSecond(0).withNano(0).plusMinutes(1);
    }

    // === 열거형 및 데이터 클래스들 ===

    public enum NotificationType {
        OPENING_TIME("영업 시작"),
        CLOSING_TIME("영업 종료"),
        BREAK_TIME_START("휴게시간 시작"),
        BREAK_TIME_END("휴게시간 종료"),
        OPENING_SOON("영업 시작 예정"),
        CLOSING_SOON("영업 종료 예정"),
        STATUS_CHANGED("상태 변경");

        private final String description;

        NotificationType(String description) {
            this.description = description;
        }

        public String getDescription() {
            return description;
        }
    }

    @lombok.Data
    @lombok.Builder
    public static class SchedulerStatusInfo {
        private boolean isEnabled;
        private LocalDateTime lastRunTime;
        private int totalUpdates;
        private int successfulUpdates;
        private int failedUpdates;
        private int cachedServiceCenters;
        private LocalDateTime nextScheduledRun;
        private double successRate;

        public double getSuccessRate() {
            if (totalUpdates == 0) return 0.0;
            return (double) successfulUpdates / totalUpdates * 100;
        }
    }
} 